# =============================================================================
# ADAM Audio Service
# Location: adam/audio/service.py
# =============================================================================

"""
AUDIO SERVICE

Unified service for audio generation and optimization.
"""

import logging
import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

from adam.audio.models import (
    VoiceProfile,
    VoiceGender,
    VoiceStyle,
    AudioFormat,
    SSMLDocument,
    AudioVariant,
    ProsodyModulation,
)
from adam.audio.ssml import SSMLGenerator
from adam.infrastructure.redis import ADAMRedisCache

logger = logging.getLogger(__name__)


class VoiceSynthesizer:
    """
    Voice synthesis with multiple TTS backend support.
    
    Supports:
    - Google Cloud Text-to-Speech (production)
    - AWS Polly (alternative)
    - Placeholder URLs (testing)
    """
    
    def __init__(
        self,
        google_credentials_path: Optional[str] = None,
        aws_region: Optional[str] = None,
    ):
        self._google_credentials = google_credentials_path or os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS"
        )
        self._aws_region = aws_region or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        self._backend = self._detect_backend()
        self._google_client = None
        self._polly_client = None
    
    def _detect_backend(self) -> str:
        """Detect which TTS backend to use."""
        # Check for Google Cloud TTS
        if self._google_credentials:
            try:
                from google.cloud import texttospeech
                return "google"
            except ImportError:
                logger.info("Google Cloud TTS library not installed")
        
        # Check for AWS Polly
        try:
            import boto3
            # Verify credentials exist
            session = boto3.Session()
            if session.get_credentials():
                return "aws"
        except ImportError:
            logger.info("boto3 not installed")
        except Exception:
            pass
        
        logger.info("No TTS backend available; using placeholder")
        return "placeholder"
    
    async def synthesize(
        self,
        ssml: str,
        output_format: AudioFormat,
        voice_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Synthesize audio from SSML.
        
        Returns:
            URL or path to generated audio file
        """
        if self._backend == "google":
            return await self._synthesize_google(ssml, output_format, voice_id)
        elif self._backend == "aws":
            return await self._synthesize_polly(ssml, output_format, voice_id)
        else:
            return await self._synthesize_placeholder(ssml, output_format)
    
    async def _synthesize_google(
        self,
        ssml: str,
        output_format: AudioFormat,
        voice_id: Optional[str],
    ) -> Optional[str]:
        """Synthesize using Google Cloud Text-to-Speech."""
        try:
            from google.cloud import texttospeech
            import asyncio
            
            if self._google_client is None:
                self._google_client = texttospeech.TextToSpeechClient()
            
            # Build request
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml)
            
            voice = texttospeech.VoiceSelectionParams(
                name=voice_id or "en-US-Neural2-C",
                language_code="en-US",
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=self._get_google_encoding(output_format),
            )
            
            # Run in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._google_client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config,
                )
            )
            
            # Save to file
            audio_id = uuid4().hex[:12]
            filename = f"/tmp/adam_audio_{audio_id}.{output_format.value}"
            
            with open(filename, "wb") as f:
                f.write(response.audio_content)
            
            return filename
            
        except Exception as e:
            logger.error(f"Google TTS error: {e}")
            return await self._synthesize_placeholder(ssml, output_format)
    
    async def _synthesize_polly(
        self,
        ssml: str,
        output_format: AudioFormat,
        voice_id: Optional[str],
    ) -> Optional[str]:
        """Synthesize using AWS Polly."""
        try:
            import boto3
            import asyncio
            
            if self._polly_client is None:
                self._polly_client = boto3.client(
                    "polly", region_name=self._aws_region
                )
            
            # Run in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._polly_client.synthesize_speech(
                    TextType="ssml",
                    Text=ssml,
                    OutputFormat=self._get_polly_format(output_format),
                    VoiceId=voice_id or "Joanna",
                    Engine="neural",
                )
            )
            
            # Save to file
            audio_id = uuid4().hex[:12]
            filename = f"/tmp/adam_audio_{audio_id}.{output_format.value}"
            
            with open(filename, "wb") as f:
                f.write(response["AudioStream"].read())
            
            return filename
            
        except Exception as e:
            logger.error(f"AWS Polly error: {e}")
            return await self._synthesize_placeholder(ssml, output_format)
    
    async def _synthesize_placeholder(
        self,
        ssml: str,
        output_format: AudioFormat,
    ) -> str:
        """
        Return placeholder URL for testing.
        
        In production, this should not be used.
        """
        audio_id = uuid4().hex[:12]
        return f"/audio/placeholder_{audio_id}.{output_format.value}"
    
    def _get_google_encoding(self, format: AudioFormat):
        """Map AudioFormat to Google encoding."""
        from google.cloud import texttospeech
        
        mapping = {
            AudioFormat.MP3: texttospeech.AudioEncoding.MP3,
            AudioFormat.WAV: texttospeech.AudioEncoding.LINEAR16,
            AudioFormat.OGG: texttospeech.AudioEncoding.OGG_OPUS,
        }
        return mapping.get(format, texttospeech.AudioEncoding.MP3)
    
    def _get_polly_format(self, format: AudioFormat) -> str:
        """Map AudioFormat to Polly format."""
        mapping = {
            AudioFormat.MP3: "mp3",
            AudioFormat.WAV: "pcm",
            AudioFormat.OGG: "ogg_vorbis",
        }
        return mapping.get(format, "mp3")
    
    @property
    def backend_info(self) -> Dict[str, str]:
        """Get information about active backend."""
        return {
            "backend": self._backend,
            "google_configured": bool(self._google_credentials),
            "aws_region": self._aws_region,
        }


class AudioService:
    """
    Unified audio service for ADAM.
    """
    
    # Default voice profiles
    DEFAULT_PROFILES = {
        "professional_male": VoiceProfile(
            profile_id="professional_male",
            name="Professional Male",
            gender=VoiceGender.MALE,
            style=VoiceStyle.PROFESSIONAL,
            voice_id="en-US-Neural2-D",
        ),
        "professional_female": VoiceProfile(
            profile_id="professional_female",
            name="Professional Female",
            gender=VoiceGender.FEMALE,
            style=VoiceStyle.PROFESSIONAL,
            voice_id="en-US-Neural2-C",
        ),
        "friendly_male": VoiceProfile(
            profile_id="friendly_male",
            name="Friendly Male",
            gender=VoiceGender.MALE,
            style=VoiceStyle.FRIENDLY,
            voice_id="en-US-Neural2-A",
        ),
        "friendly_female": VoiceProfile(
            profile_id="friendly_female",
            name="Friendly Female",
            gender=VoiceGender.FEMALE,
            style=VoiceStyle.FRIENDLY,
            voice_id="en-US-Neural2-F",
        ),
    }
    
    def __init__(
        self,
        cache: Optional[ADAMRedisCache] = None,
    ):
        self.cache = cache
        self.ssml_generator = SSMLGenerator()
        self.synthesizer = VoiceSynthesizer()
    
    async def generate_audio_variant(
        self,
        text: str,
        voice_profile_id: str,
        target_personality: Optional[Dict[str, float]] = None,
        framing: Optional[List[str]] = None,
        output_format: AudioFormat = AudioFormat.MP3,
    ) -> AudioVariant:
        """Generate an audio variant for given text."""
        
        # Get voice profile
        profile = self.DEFAULT_PROFILES.get(voice_profile_id)
        if not profile:
            profile = self.DEFAULT_PROFILES["professional_female"]
        
        # Calculate modulation from personality
        modulation = self._personality_to_modulation(target_personality)
        
        # Generate SSML
        ssml_doc = self.ssml_generator.generate(
            text=text,
            voice_profile=profile,
            target_personality=target_personality,
            modulation=modulation,
        )
        
        # Synthesize audio
        audio_url = await self.synthesizer.synthesize(
            ssml_doc.ssml, output_format
        )
        
        return AudioVariant(
            variant_id=f"audio_{uuid4().hex[:12]}",
            text=text,
            ssml=ssml_doc.ssml,
            audio_url=audio_url,
            audio_format=output_format,
            duration_seconds=ssml_doc.duration_estimate_seconds,
            voice_profile=profile,
            target_personality=target_personality or {},
            framing_applied=framing or [],
        )
    
    async def generate_ad_audio(
        self,
        headline: str,
        body: str,
        call_to_action: str,
        voice_profile_id: str,
        target_personality: Optional[Dict[str, float]] = None,
        output_format: AudioFormat = AudioFormat.MP3,
    ) -> AudioVariant:
        """Generate audio for an advertisement."""
        
        profile = self.DEFAULT_PROFILES.get(
            voice_profile_id,
            self.DEFAULT_PROFILES["professional_female"]
        )
        
        # Generate ad-optimized SSML
        ssml_doc = self.ssml_generator.generate_ad_ssml(
            headline=headline,
            body=body,
            call_to_action=call_to_action,
            voice_profile=profile,
            target_personality=target_personality,
        )
        
        # Synthesize
        audio_url = await self.synthesizer.synthesize(
            ssml_doc.ssml, output_format
        )
        
        full_text = f"{headline} {body} {call_to_action}"
        
        return AudioVariant(
            variant_id=f"ad_audio_{uuid4().hex[:12]}",
            text=full_text,
            ssml=ssml_doc.ssml,
            audio_url=audio_url,
            audio_format=output_format,
            duration_seconds=ssml_doc.duration_estimate_seconds,
            voice_profile=profile,
            target_personality=target_personality or {},
        )
    
    def _personality_to_modulation(
        self,
        personality: Optional[Dict[str, float]],
    ) -> ProsodyModulation:
        """Convert personality profile to prosody modulation."""
        
        if not personality:
            return ProsodyModulation()
        
        rate = 1.0
        pause = 500
        
        # High extraversion -> faster, shorter pauses
        if personality.get("extraversion", 0.5) > 0.7:
            rate *= 1.05
            pause = 400
        elif personality.get("extraversion", 0.5) < 0.3:
            rate *= 0.95
            pause = 600
        
        # High neuroticism -> slower, more calming
        if personality.get("neuroticism", 0.5) > 0.7:
            rate *= 0.95
            pause = 600
        
        return ProsodyModulation(
            rate_multiplier=rate,
            sentence_pause_ms=pause,
            based_on={"personality": personality},
        )
    
    async def select_voice_for_user(
        self,
        user_profile: Dict[str, Any],
    ) -> VoiceProfile:
        """Select optimal voice profile for user."""
        
        # Simple selection based on preferences
        preferred_gender = user_profile.get("preferred_voice_gender")
        
        if preferred_gender == "male":
            base = "male"
        elif preferred_gender == "female":
            base = "female"
        else:
            base = "female"  # Default
        
        # Select style based on personality
        extraversion = user_profile.get("big_five", {}).get("extraversion", 0.5)
        
        if extraversion > 0.6:
            style = "friendly"
        else:
            style = "professional"
        
        profile_id = f"{style}_{base}"
        return self.DEFAULT_PROFILES.get(
            profile_id,
            self.DEFAULT_PROFILES["professional_female"]
        )

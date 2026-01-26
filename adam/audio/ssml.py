# =============================================================================
# ADAM SSML Generator
# Location: adam/audio/ssml.py
# =============================================================================

"""
SSML GENERATOR

Generate psychologically-optimized SSML for voice synthesis.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from adam.audio.models import (
    VoiceProfile,
    VoiceStyle,
    SSMLDocument,
    ProsodyModulation,
)

logger = logging.getLogger(__name__)


class SSMLGenerator:
    """
    Generate SSML with psychological optimization.
    
    Applies prosody modulation based on:
    - Target personality traits
    - Regulatory focus
    - Message framing
    - Context (urgency, emotional state)
    """
    
    # Style to prosody mapping
    STYLE_PROSODY = {
        VoiceStyle.CONVERSATIONAL: {"rate": 1.0, "pitch": "0%"},
        VoiceStyle.PROFESSIONAL: {"rate": 0.95, "pitch": "-5%"},
        VoiceStyle.ENTHUSIASTIC: {"rate": 1.1, "pitch": "+10%"},
        VoiceStyle.CALM: {"rate": 0.9, "pitch": "-10%"},
        VoiceStyle.URGENT: {"rate": 1.15, "pitch": "+5%"},
        VoiceStyle.FRIENDLY: {"rate": 1.05, "pitch": "+5%"},
    }
    
    # Personality-based adjustments
    PERSONALITY_ADJUSTMENTS = {
        "extraversion_high": {"rate": "+5%", "pitch": "+3%"},
        "extraversion_low": {"rate": "-5%", "pitch": "-3%"},
        "neuroticism_high": {"rate": "-3%", "pitch": "-2%"},
        "openness_high": {"rate": "+2%", "pitch": "+5%"},
        "conscientiousness_high": {"rate": "-2%", "pitch": "-2%"},
    }
    
    def __init__(self):
        self.default_voice = "en-US-Standard-A"
    
    def generate(
        self,
        text: str,
        voice_profile: VoiceProfile,
        target_personality: Optional[Dict[str, float]] = None,
        modulation: Optional[ProsodyModulation] = None,
    ) -> SSMLDocument:
        """Generate SSML from text with psychological optimization."""
        
        # Start SSML document
        ssml_parts = ['<speak>']
        
        # Apply voice
        ssml_parts.append(
            f'<voice name="{voice_profile.voice_id}">'
        )
        
        # Calculate prosody
        prosody = self._calculate_prosody(
            voice_profile, target_personality, modulation
        )
        
        # Apply prosody wrapper
        ssml_parts.append(
            f'<prosody rate="{prosody["rate"]}" pitch="{prosody["pitch"]}">'
        )
        
        # Process text with emphasis
        processed_text = self._add_emphasis(text, modulation)
        
        # Add sentence breaks
        processed_text = self._add_breaks(processed_text, modulation)
        
        ssml_parts.append(processed_text)
        
        # Close tags
        ssml_parts.append('</prosody>')
        ssml_parts.append('</voice>')
        ssml_parts.append('</speak>')
        
        ssml = ''.join(ssml_parts)
        
        return SSMLDocument(
            ssml=ssml,
            word_count=len(text.split()),
            voice_profile=voice_profile.profile_id,
            duration_estimate_seconds=self._estimate_duration(text, prosody),
        )
    
    def _calculate_prosody(
        self,
        voice_profile: VoiceProfile,
        target_personality: Optional[Dict[str, float]],
        modulation: Optional[ProsodyModulation],
    ) -> Dict[str, str]:
        """Calculate final prosody settings."""
        
        # Start with style defaults
        style_prosody = self.STYLE_PROSODY.get(
            voice_profile.style,
            {"rate": 1.0, "pitch": "0%"}
        )
        
        rate = float(style_prosody.get("rate", 1.0))
        pitch = style_prosody.get("pitch", "0%")
        
        # Apply personality adjustments
        if target_personality:
            for trait, value in target_personality.items():
                if value > 0.7:
                    adj = self.PERSONALITY_ADJUSTMENTS.get(f"{trait}_high", {})
                elif value < 0.3:
                    adj = self.PERSONALITY_ADJUSTMENTS.get(f"{trait}_low", {})
                else:
                    adj = {}
                
                if "rate" in adj:
                    rate *= 1 + float(adj["rate"].strip("%")) / 100
        
        # Apply modulation override
        if modulation:
            rate *= modulation.rate_multiplier
        
        # Clamp rate
        rate = max(0.5, min(2.0, rate))
        
        return {
            "rate": f"{rate:.0%}",
            "pitch": pitch,
        }
    
    def _add_emphasis(
        self,
        text: str,
        modulation: Optional[ProsodyModulation],
    ) -> str:
        """Add emphasis to key words."""
        
        if not modulation or not modulation.emphasis_words:
            return text
        
        for word in modulation.emphasis_words:
            # Case-insensitive replacement with emphasis
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            text = pattern.sub(
                f'<emphasis level="strong">{word}</emphasis>',
                text
            )
        
        return text
    
    def _add_breaks(
        self,
        text: str,
        modulation: Optional[ProsodyModulation],
    ) -> str:
        """Add sentence breaks."""
        
        pause_ms = 500
        if modulation:
            pause_ms = modulation.sentence_pause_ms
        
        # Add break after sentences
        text = re.sub(
            r'([.!?])\s+',
            f'\\1<break time="{pause_ms}ms"/> ',
            text
        )
        
        return text
    
    def _estimate_duration(
        self,
        text: str,
        prosody: Dict[str, str],
    ) -> float:
        """Estimate audio duration in seconds."""
        
        words = len(text.split())
        
        # Base rate: 150 words per minute
        wpm = 150
        
        # Adjust for prosody rate
        rate_str = prosody.get("rate", "100%")
        rate = float(rate_str.strip("%")) / 100
        wpm *= rate
        
        return (words / wpm) * 60
    
    def generate_ad_ssml(
        self,
        headline: str,
        body: str,
        call_to_action: str,
        voice_profile: VoiceProfile,
        target_personality: Optional[Dict[str, float]] = None,
    ) -> SSMLDocument:
        """Generate SSML for an ad with proper structure."""
        
        # Build structured text
        text_parts = []
        
        # Headline with emphasis
        text_parts.append(f'<p><s>{headline}</s></p>')
        
        # Short pause
        text_parts.append('<break time="300ms"/>')
        
        # Body
        text_parts.append(f'<p>{body}</p>')
        
        # Pause before CTA
        text_parts.append('<break time="500ms"/>')
        
        # CTA with emphasis
        text_parts.append(
            f'<p><emphasis level="strong">{call_to_action}</emphasis></p>'
        )
        
        full_text = ''.join(text_parts)
        
        # Generate with prosody
        prosody = self._calculate_prosody(voice_profile, target_personality, None)
        
        ssml = f'''<speak>
<voice name="{voice_profile.voice_id}">
<prosody rate="{prosody["rate"]}" pitch="{prosody["pitch"]}">
{full_text}
</prosody>
</voice>
</speak>'''
        
        return SSMLDocument(
            ssml=ssml,
            word_count=len(f"{headline} {body} {call_to_action}".split()),
            voice_profile=voice_profile.profile_id,
        )

# =============================================================================
# Processing Depth Classifier — Signal 4
# Location: adam/retargeting/engines/processing_depth.py
# Enhancement #34: Nonconscious Signal Intelligence Layer, Session 2
# =============================================================================

"""
Classifies how deeply a person processed an ad impression.

This is the HIGHEST-LEVERAGE signal in the system. Currently, every non-click
impression equally penalizes the deployed mechanism's posterior. But 30-50%
of display impressions are never meaningfully seen (Lumen Research: only 30%
of viewable display ads are actually looked at). The system is learning from
noise — penalizing mechanisms for failures that never happened. This creates
systematic pessimism in Thompson Sampling.

Fixing this is not an optimization — it's a CORRECTION of a systematic error
contaminating the entire learning pipeline.

Processing depth is classified from viewability seconds (how long the ad was
in the viewport) and click/video engagement signals. The classification drives
a power-posterior weight that scales the posterior update:

  UNPROCESSED (< 1.0s):        weight = 0.05  (near-zero update)
  PERIPHERAL  (1.0 - 2.5s):    weight = 0.30  (shallow processing)
  EVALUATED   (2.5 - 5.0s):    weight = 0.80  (active consideration)
  DELIBERATE_REJECTION (> 5s):  weight = 1.00  (full negative signal)

Research validation:
  - < 1.0s: Bruns et al. 2025 (J. Advertising): 94% correctly identifies
    fixated ads at >= 1s threshold. MRC standard agrees.
  - 1.0-2.5s: Lumen Research avg display dwell; Amplified Intelligence
    (May 2025): 1.5s sufficient for memory encoding with brand assets.
  - 2.5-5.0s: Nelson-Field (Amplified Intelligence): 2.5s memory formation
    threshold. LinkedIn/MediaScience: peak cardiac deceleration at 4s.
  - > 5.0s: Goldstein et al. 2011 (ACM EC): diminishing returns ~10s.
    Non-click after 5s+ = deliberate rejection.
"""

import logging
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# PROCESSING DEPTH ENUM
# =============================================================================

class ProcessingDepth(str, Enum):
    """How deeply the person processed the ad."""
    UNPROCESSED = "unprocessed"           # < 1.0s viewport time
    PERIPHERAL = "peripheral"             # 1.0 - 2.5s
    EVALUATED = "evaluated"               # 2.5 - 5.0s
    REJECTED = "deliberate_rejection"     # > 5.0s, non-click


# =============================================================================
# POSTERIOR UPDATE WEIGHTS (Power Posterior Framework)
# =============================================================================

# L(x|θ)^w where w is the weight. Lower w = less posterior shift.
#
# w = 0.05 for UNPROCESSED:
#   Not zero — subliminal/mere exposure effects exist (Bornstein 1989
#   meta-analysis: r=0.26) but negligible for advertising specifically
#   (Trappey 1996: r=0.059). Fisher information ≈ 0.004-0.01.
#   Risk asymmetry: if true weight is 0 and we use 0.05, minimal noise.
#
# w = 0.30 for PERIPHERAL:
#   Heath's "Low Attention Processing" (2006, J. Advertising Research)
#   shows implicit learning at low attention. Moderate update.
#
# w = 0.80 for EVALUATED:
#   Strong evidence. Some evaluation failures are contextual (phone
#   interrupted, lost connection) rather than mechanism failures.
#
# w = 1.00 for REJECTED:
#   Full-weight negative update. Processed fully, deliberately declined.

PROCESSING_DEPTH_WEIGHTS: Dict[ProcessingDepth, float] = {
    ProcessingDepth.UNPROCESSED: 0.05,
    ProcessingDepth.PERIPHERAL:  0.30,
    ProcessingDepth.EVALUATED:   0.80,
    ProcessingDepth.REJECTED:    1.00,
}


# =============================================================================
# DIAGNOSTIC HYPOTHESIS MODIFIERS (H1-H5)
# =============================================================================

# These modify the DiagnosticReasoner's H1-H5 base probabilities.
# Applied BEFORE hypothesis evaluation in reason_sync().

PROCESSING_DEPTH_H_MODIFIERS: Dict[ProcessingDepth, Dict[str, float]] = {
    ProcessingDepth.UNPROCESSED: {
        "H1": 0.0,   # Can't blame page mindstate — they didn't see it
        "H2": 0.0,   # Can't blame mechanism — they didn't see it
        "H3": 0.0,   # Can't blame stage — they didn't see it
        "H4": 0.0,   # Can't blame reactance — they didn't see it
        "H5": 0.40,  # Strong evidence for fatigue/blindness
    },
    ProcessingDepth.PERIPHERAL: {
        "H1": 0.15,  # Page environment may not support attention capture
        "H2": 0.0,   # Didn't process deeply enough to evaluate mechanism
        "H3": 0.0,   # Didn't process deeply enough to evaluate stage fit
        "H4": 0.0,   # Peripheral processing doesn't trigger reactance
        "H5": 0.20,  # Some fatigue/blindness evidence
    },
    ProcessingDepth.EVALUATED: {
        "H1": -0.05,  # They saw it — page was somewhat effective
        "H2": 0.20,   # They evaluated and decided against — mechanism issue
        "H3": 0.10,   # Possible stage mismatch
        "H4": 0.05,   # Mild reactance possible
        "H5": -0.10,  # They engaged — not fatigue
    },
    ProcessingDepth.REJECTED: {
        "H1": -0.10,  # They processed fully — page worked
        "H2": 0.30,   # Strong mechanism/argument failure
        "H3": 0.15,   # Stage mismatch more likely with full processing
        "H4": 0.20,   # Full processing + rejection = reactance signal
        "H5": -0.20,  # Definitely not fatigue — they were attending
    },
}


# =============================================================================
# CLASSIFIER
# =============================================================================

def classify_processing_depth(
    viewability_seconds: float,
    clicked: bool,
    video_seconds_watched: Optional[float] = None,
    video_total_seconds: Optional[float] = None,
) -> ProcessingDepth:
    """Classify how deeply the person processed the ad.

    Args:
        viewability_seconds: Time the ad was in the viewport (from StackAdapt
            viewability metrics or our telemetry).
        clicked: Whether the person clicked the ad.
        video_seconds_watched: For video ads, absolute seconds watched.
        video_total_seconds: For video ads, total video duration.

    Returns:
        ProcessingDepth classification.

    For video: uses absolute seconds watched, not just quartile completion.
    A 30s video at 25% (7.5s) is more processed than a 6s bumper at 50% (3s).
    """
    if clicked:
        return ProcessingDepth.EVALUATED  # Clicking implies processing

    # For video, prefer absolute watch time over viewport time
    effective_seconds = viewability_seconds
    if video_seconds_watched is not None:
        effective_seconds = max(viewability_seconds, video_seconds_watched)

    if effective_seconds < 1.0:
        return ProcessingDepth.UNPROCESSED
    elif effective_seconds < 2.5:
        return ProcessingDepth.PERIPHERAL
    elif effective_seconds < 5.0:
        return ProcessingDepth.EVALUATED
    else:
        return ProcessingDepth.REJECTED


def get_processing_weight(depth: ProcessingDepth) -> float:
    """Get the posterior update weight for a processing depth level."""
    return PROCESSING_DEPTH_WEIGHTS[depth]


def get_processing_h_modifiers(depth: ProcessingDepth) -> Dict[str, float]:
    """Get the H1-H5 diagnostic hypothesis modifiers for a processing depth."""
    return PROCESSING_DEPTH_H_MODIFIERS[depth].copy()

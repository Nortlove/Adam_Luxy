# =============================================================================
# ADAM ML Module — Custom AI Model + Online Learning
# =============================================================================

"""
ADAM's custom AI model ecosystem — NOT a wrapper around a generic LLM.

Purpose-built multi-task neural networks trained on 1B+ psycholinguistic
extractions that capture patterns no rule-based system can express.

Architecture:
    Text → Rule-Based Extraction (fast, interpretable)
         → Foundation Model (multi-task: NDF + archetype + mechanism)
         → Ensemble Combiner (confidence-weighted fusion)
         → Online Learning (contextual bandit + NDF refinement)

Core Components:
    - weak_supervisor: Exports rule-based labels as ML training data
    - ndf_predictor: Neural NDF dimension predictor + trainer
    - hybrid_extractor: Confidence-weighted fusion of rule + ML outputs
    - training_pipeline: Full curriculum learning pipeline

Custom AI Model (Breakthrough):
    - foundation_model: PsychoFormer — multi-task transformer with
      cross-task attention (NDF → Archetype → Mechanism refinement)
    - online_learner: Three online learning mechanisms:
      1. LinUCB contextual bandit for mechanism selection
      2. Gradient-free NDF refinement from outcomes
      3. Reward-weighted regression for periodic fine-tuning

Three Learning Loops:
    1. Offline: Batch training on 1B+ rule-extracted labels
    2. Online: Real-time learning from ad outcome feedback
    3. Self-supervised: Contrastive learning on psycholinguistic similarity
"""

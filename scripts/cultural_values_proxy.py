#!/usr/bin/env python3
"""
Cultural Values Proxy System

Maps political lean data to estimated cultural/psychological values based on
well-established research correlations:

1. Moral Foundations Theory (Jonathan Haidt)
   - Individualizing: Care/Harm, Fairness/Cheating
   - Binding: Loyalty/Betrayal, Authority/Subversion, Sanctity/Degradation
   
2. World Values Survey Dimensions (Inglehart-Welzel)
   - Traditional vs Secular-Rational values
   - Survival vs Self-Expression values

3. Decision-Making Style Predictors
   - System 1 vs System 2 processing preference
   - Need for Cognitive Closure
   - Uncertainty Tolerance

Research sources:
- Haidt, J. (2012). The Righteous Mind
- Graham, J. et al. (2013). Moral Foundations Theory
- Inglehart, R. & Welzel, C. (2005). Modernization, Cultural Change and Democracy
- Jost, J. T. et al. (2003). Political Conservatism as Motivated Social Cognition
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import math


@dataclass
class MoralFoundations:
    """Moral Foundations Theory scores (0-1 scale)"""
    care: float  # Sensitivity to suffering, compassion
    fairness: float  # Justice, rights, equality
    loyalty: float  # Group allegiance, patriotism
    authority: float  # Respect for hierarchy, tradition
    sanctity: float  # Purity, disgust sensitivity, sacredness
    
    @property
    def individualizing(self) -> float:
        """Average of care + fairness (liberal foundations)"""
        return (self.care + self.fairness) / 2
    
    @property
    def binding(self) -> float:
        """Average of loyalty + authority + sanctity (conservative foundations)"""
        return (self.loyalty + self.authority + self.sanctity) / 3
    
    @property
    def moral_balance(self) -> float:
        """Binding - Individualizing (positive = more binding/conservative)"""
        return self.binding - self.individualizing


@dataclass
class WorldValues:
    """World Values Survey dimensions (0-1 scale)"""
    traditional_vs_secular: float  # 0=traditional, 1=secular-rational
    survival_vs_expression: float  # 0=survival, 1=self-expression


@dataclass
class DecisionStyle:
    """Decision-making style predictors (0-1 scale)"""
    need_for_closure: float  # Preference for certainty, quick decisions
    uncertainty_tolerance: float  # Comfort with ambiguity
    analytical_thinking: float  # System 2 processing preference
    intuitive_thinking: float  # System 1/gut feeling preference
    openness_to_experience: float  # Big Five personality trait
    conscientiousness: float  # Big Five personality trait


@dataclass
class ReligiosityProfile:
    """Religiosity estimates (0-1 scale)"""
    religious_attendance: float  # Estimated church attendance
    religious_importance: float  # Importance of religion in life
    biblical_literalism: float  # Literal Bible interpretation tendency
    evangelical_identity: float  # Evangelical Christian identification


@dataclass
class CulturalProfile:
    """Complete cultural values profile"""
    moral_foundations: MoralFoundations
    world_values: WorldValues
    decision_style: DecisionStyle
    religiosity: ReligiosityProfile
    
    # Summary scores
    traditionalism_score: float  # 0-1 (higher = more traditional)
    individualism_score: float  # 0-1 (higher = more individualist)
    cognitive_style: str  # "analytical", "intuitive", "balanced"
    

def estimate_moral_foundations(lean_score: float) -> MoralFoundations:
    """
    Estimate moral foundations from political lean score.
    
    Research shows:
    - Conservatives weight all 5 foundations ~equally
    - Liberals weight care/fairness much higher than binding foundations
    
    Args:
        lean_score: -1 (strong D) to +1 (strong R)
    
    Returns:
        MoralFoundations with estimated scores
    """
    # Normalize lean_score to 0-1 range (0=most D, 1=most R)
    conservatism = (lean_score + 1) / 2
    liberalism = 1 - conservatism
    
    # Care: Liberals higher, but conservatives also value
    care = 0.65 + (liberalism * 0.25) - (conservatism * 0.10)
    
    # Fairness: Liberals higher (equality focus) vs conservatives (proportionality)
    fairness = 0.60 + (liberalism * 0.30) - (conservatism * 0.15)
    
    # Loyalty: Conservatives much higher
    loyalty = 0.40 + (conservatism * 0.45) - (liberalism * 0.15)
    
    # Authority: Conservatives much higher
    authority = 0.35 + (conservatism * 0.50) - (liberalism * 0.15)
    
    # Sanctity: Conservatives much higher
    sanctity = 0.30 + (conservatism * 0.55) - (liberalism * 0.10)
    
    # Clamp all values to 0-1
    return MoralFoundations(
        care=max(0, min(1, care)),
        fairness=max(0, min(1, fairness)),
        loyalty=max(0, min(1, loyalty)),
        authority=max(0, min(1, authority)),
        sanctity=max(0, min(1, sanctity)),
    )


def estimate_world_values(lean_score: float) -> WorldValues:
    """
    Estimate World Values Survey dimensions from political lean.
    
    Research correlations:
    - Traditional values correlate with conservatism
    - Self-expression correlates with liberalism and economic development
    
    Args:
        lean_score: -1 (strong D) to +1 (strong R)
    """
    conservatism = (lean_score + 1) / 2
    
    # Traditional vs Secular-Rational
    # Higher conservatism = more traditional
    traditional_vs_secular = 0.50 - (conservatism * 0.40) + ((1 - conservatism) * 0.30)
    
    # Survival vs Self-Expression
    # More complex - both economic and cultural factors
    # Urban liberal areas tend toward self-expression
    survival_vs_expression = 0.55 - (conservatism * 0.25) + ((1 - conservatism) * 0.20)
    
    return WorldValues(
        traditional_vs_secular=max(0, min(1, traditional_vs_secular)),
        survival_vs_expression=max(0, min(1, survival_vs_expression)),
    )


def estimate_decision_style(lean_score: float) -> DecisionStyle:
    """
    Estimate decision-making style from political lean.
    
    Research shows:
    - Conservatives: Higher need for closure, lower uncertainty tolerance
    - Liberals: Higher openness, more analytical processing
    - Both use intuition, but for different moral foundations
    
    Args:
        lean_score: -1 (strong D) to +1 (strong R)
    """
    conservatism = (lean_score + 1) / 2
    liberalism = 1 - conservatism
    
    # Need for Cognitive Closure: Conservatives higher
    need_for_closure = 0.45 + (conservatism * 0.30)
    
    # Uncertainty Tolerance: Liberals higher
    uncertainty_tolerance = 0.45 + (liberalism * 0.30)
    
    # Analytical Thinking: Slightly higher in liberals (but varies)
    analytical_thinking = 0.50 + (liberalism * 0.15)
    
    # Intuitive Thinking: Both use, conservatives for binding morals
    intuitive_thinking = 0.55 + (conservatism * 0.10)
    
    # Openness to Experience: Strong liberal correlation
    openness_to_experience = 0.40 + (liberalism * 0.35)
    
    # Conscientiousness: Moderate conservative correlation
    conscientiousness = 0.50 + (conservatism * 0.20)
    
    return DecisionStyle(
        need_for_closure=max(0, min(1, need_for_closure)),
        uncertainty_tolerance=max(0, min(1, uncertainty_tolerance)),
        analytical_thinking=max(0, min(1, analytical_thinking)),
        intuitive_thinking=max(0, min(1, intuitive_thinking)),
        openness_to_experience=max(0, min(1, openness_to_experience)),
        conscientiousness=max(0, min(1, conscientiousness)),
    )


def estimate_religiosity(lean_score: float, state: str = None) -> ReligiosityProfile:
    """
    Estimate religiosity from political lean.
    
    Research shows strong correlation between conservatism and:
    - Church attendance
    - Religious importance
    - Evangelical identification
    - Biblical literalism
    
    Note: This is a rough estimate. Actual religiosity varies significantly
    by region (Bible Belt vs Pacific Northwest) and demographics.
    
    Args:
        lean_score: -1 (strong D) to +1 (strong R)
        state: Optional state for regional adjustment
    """
    conservatism = (lean_score + 1) / 2
    
    # Regional adjustment factor (Bible Belt states have higher baseline)
    regional_boost = 0.0
    if state:
        bible_belt = ["alabama", "arkansas", "georgia", "kentucky", "louisiana",
                     "mississippi", "north_carolina", "oklahoma", "south_carolina",
                     "tennessee", "texas", "west_virginia"]
        secular_regions = ["california", "colorado", "connecticut", "maine",
                         "massachusetts", "new_hampshire", "oregon", "vermont",
                         "washington", "district_of_columbia"]
        
        state_lower = state.lower().replace(" ", "_")
        if state_lower in bible_belt:
            regional_boost = 0.15
        elif state_lower in secular_regions:
            regional_boost = -0.10
    
    # Religious attendance: Strong conservative correlation
    religious_attendance = 0.30 + (conservatism * 0.45) + regional_boost
    
    # Religious importance: Strong conservative correlation
    religious_importance = 0.35 + (conservatism * 0.45) + regional_boost
    
    # Biblical literalism: Very strong conservative correlation
    biblical_literalism = 0.20 + (conservatism * 0.55) + regional_boost
    
    # Evangelical identity: Very strong conservative correlation
    evangelical_identity = 0.15 + (conservatism * 0.60) + regional_boost
    
    return ReligiosityProfile(
        religious_attendance=max(0, min(1, religious_attendance)),
        religious_importance=max(0, min(1, religious_importance)),
        biblical_literalism=max(0, min(1, biblical_literalism)),
        evangelical_identity=max(0, min(1, evangelical_identity)),
    )


def compute_cultural_profile(lean_score: float, state: str = None) -> CulturalProfile:
    """
    Compute complete cultural profile from political lean score.
    
    Args:
        lean_score: -1 (strong D) to +1 (strong R)
        state: Optional state name for regional adjustments
    
    Returns:
        Complete CulturalProfile with all estimated values
    """
    moral = estimate_moral_foundations(lean_score)
    world = estimate_world_values(lean_score)
    decision = estimate_decision_style(lean_score)
    religiosity = estimate_religiosity(lean_score, state)
    
    # Compute summary scores
    conservatism = (lean_score + 1) / 2
    
    # Traditionalism: Blend of moral binding, traditional values, religiosity
    traditionalism_score = (
        moral.binding * 0.30 +
        (1 - world.traditional_vs_secular) * 0.30 +
        religiosity.religious_importance * 0.40
    )
    
    # Individualism: Blend of care/fairness focus, self-expression, openness
    individualism_score = (
        moral.individualizing * 0.30 +
        world.survival_vs_expression * 0.30 +
        decision.openness_to_experience * 0.40
    )
    
    # Cognitive style classification
    if decision.analytical_thinking > decision.intuitive_thinking + 0.1:
        cognitive_style = "analytical"
    elif decision.intuitive_thinking > decision.analytical_thinking + 0.1:
        cognitive_style = "intuitive"
    else:
        cognitive_style = "balanced"
    
    return CulturalProfile(
        moral_foundations=moral,
        world_values=world,
        decision_style=decision,
        religiosity=religiosity,
        traditionalism_score=traditionalism_score,
        individualism_score=individualism_score,
        cognitive_style=cognitive_style,
    )


def profile_to_dict(profile: CulturalProfile) -> Dict[str, Any]:
    """Convert CulturalProfile to dictionary for JSON serialization."""
    return {
        "moral_foundations": {
            "care": round(profile.moral_foundations.care, 3),
            "fairness": round(profile.moral_foundations.fairness, 3),
            "loyalty": round(profile.moral_foundations.loyalty, 3),
            "authority": round(profile.moral_foundations.authority, 3),
            "sanctity": round(profile.moral_foundations.sanctity, 3),
            "individualizing_avg": round(profile.moral_foundations.individualizing, 3),
            "binding_avg": round(profile.moral_foundations.binding, 3),
            "moral_balance": round(profile.moral_foundations.moral_balance, 3),
        },
        "world_values": {
            "traditional_vs_secular": round(profile.world_values.traditional_vs_secular, 3),
            "survival_vs_expression": round(profile.world_values.survival_vs_expression, 3),
        },
        "decision_style": {
            "need_for_closure": round(profile.decision_style.need_for_closure, 3),
            "uncertainty_tolerance": round(profile.decision_style.uncertainty_tolerance, 3),
            "analytical_thinking": round(profile.decision_style.analytical_thinking, 3),
            "intuitive_thinking": round(profile.decision_style.intuitive_thinking, 3),
            "openness_to_experience": round(profile.decision_style.openness_to_experience, 3),
            "conscientiousness": round(profile.decision_style.conscientiousness, 3),
        },
        "religiosity": {
            "religious_attendance": round(profile.religiosity.religious_attendance, 3),
            "religious_importance": round(profile.religiosity.religious_importance, 3),
            "biblical_literalism": round(profile.religiosity.biblical_literalism, 3),
            "evangelical_identity": round(profile.religiosity.evangelical_identity, 3),
        },
        "summary": {
            "traditionalism_score": round(profile.traditionalism_score, 3),
            "individualism_score": round(profile.individualism_score, 3),
            "cognitive_style": profile.cognitive_style,
        }
    }


# =============================================================================
# AD TARGETING IMPLICATIONS
# =============================================================================

def get_advertising_implications(profile: CulturalProfile) -> Dict[str, Any]:
    """
    Generate advertising/messaging implications from cultural profile.
    
    Returns targeting recommendations based on psychological research.
    """
    implications = {
        "messaging_approach": [],
        "value_appeals": [],
        "avoid": [],
        "decision_triggers": [],
        "trust_builders": [],
    }
    
    mf = profile.moral_foundations
    ds = profile.decision_style
    rel = profile.religiosity
    
    # Moral foundations-based messaging
    if mf.care > 0.7:
        implications["value_appeals"].append("compassion")
        implications["value_appeals"].append("helping_others")
        implications["messaging_approach"].append("emotional_storytelling")
    
    if mf.fairness > 0.7:
        implications["value_appeals"].append("justice")
        implications["value_appeals"].append("equality")
        implications["messaging_approach"].append("rights_based_appeals")
    
    if mf.loyalty > 0.7:
        implications["value_appeals"].append("patriotism")
        implications["value_appeals"].append("community")
        implications["value_appeals"].append("tradition")
        implications["messaging_approach"].append("in_group_identification")
    
    if mf.authority > 0.7:
        implications["value_appeals"].append("expertise")
        implications["value_appeals"].append("heritage")
        implications["trust_builders"].append("authority_endorsements")
        implications["trust_builders"].append("established_brands")
    
    if mf.sanctity > 0.7:
        implications["value_appeals"].append("purity")
        implications["value_appeals"].append("natural")
        implications["value_appeals"].append("wholesome")
        implications["avoid"].append("controversial_imagery")
    
    # Decision style implications
    if ds.need_for_closure > 0.65:
        implications["decision_triggers"].append("limited_time_offers")
        implications["decision_triggers"].append("clear_choices")
        implications["messaging_approach"].append("simple_direct_messaging")
    else:
        implications["messaging_approach"].append("nuanced_messaging")
        implications["decision_triggers"].append("detailed_comparisons")
    
    if ds.uncertainty_tolerance < 0.4:
        implications["trust_builders"].append("guarantees")
        implications["trust_builders"].append("testimonials")
        implications["trust_builders"].append("money_back_promises")
    
    if ds.analytical_thinking > 0.6:
        implications["messaging_approach"].append("data_driven_claims")
        implications["messaging_approach"].append("feature_specifications")
    
    if ds.intuitive_thinking > 0.6:
        implications["messaging_approach"].append("emotional_appeals")
        implications["messaging_approach"].append("visual_storytelling")
    
    # Religiosity implications
    if rel.religious_importance > 0.6:
        implications["value_appeals"].append("family_values")
        implications["value_appeals"].append("tradition")
        implications["avoid"].append("irreverent_humor")
    
    if rel.evangelical_identity > 0.5:
        implications["trust_builders"].append("faith_based_endorsements")
        implications["value_appeals"].append("purpose_driven")
    
    return implications


# =============================================================================
# CLI TESTING
# =============================================================================

def main():
    """Test the cultural values proxy system."""
    print("\n" + "=" * 70)
    print("CULTURAL VALUES PROXY SYSTEM")
    print("=" * 70)
    
    # Test different political leans
    test_cases = [
        ("Strong Democratic (-0.8)", -0.8, "California"),
        ("Lean Democratic (-0.3)", -0.3, "Colorado"),
        ("Swing (0.0)", 0.0, "Pennsylvania"),
        ("Lean Republican (+0.3)", 0.3, "Texas"),
        ("Strong Republican (+0.8)", 0.8, "Alabama"),
    ]
    
    for name, lean_score, state in test_cases:
        print(f"\n{'='*70}")
        print(f"{name} - {state}")
        print("=" * 70)
        
        profile = compute_cultural_profile(lean_score, state)
        profile_dict = profile_to_dict(profile)
        
        print("\nMoral Foundations:")
        mf = profile_dict["moral_foundations"]
        print(f"  Care:       {mf['care']:.2f}  |  Fairness:  {mf['fairness']:.2f}")
        print(f"  Loyalty:    {mf['loyalty']:.2f}  |  Authority: {mf['authority']:.2f}")
        print(f"  Sanctity:   {mf['sanctity']:.2f}")
        print(f"  Individualizing avg: {mf['individualizing_avg']:.2f}")
        print(f"  Binding avg:         {mf['binding_avg']:.2f}")
        
        print("\nWorld Values:")
        wv = profile_dict["world_values"]
        print(f"  Traditional←→Secular: {wv['traditional_vs_secular']:.2f}")
        print(f"  Survival←→Expression: {wv['survival_vs_expression']:.2f}")
        
        print("\nDecision Style:")
        ds = profile_dict["decision_style"]
        print(f"  Need for Closure:    {ds['need_for_closure']:.2f}")
        print(f"  Uncertainty Tol:     {ds['uncertainty_tolerance']:.2f}")
        print(f"  Analytical:          {ds['analytical_thinking']:.2f}")
        print(f"  Intuitive:           {ds['intuitive_thinking']:.2f}")
        print(f"  Openness:            {ds['openness_to_experience']:.2f}")
        
        print("\nReligiosity:")
        rel = profile_dict["religiosity"]
        print(f"  Attendance:          {rel['religious_attendance']:.2f}")
        print(f"  Importance:          {rel['religious_importance']:.2f}")
        print(f"  Biblical Literal:    {rel['biblical_literalism']:.2f}")
        print(f"  Evangelical ID:      {rel['evangelical_identity']:.2f}")
        
        print("\nSummary:")
        summ = profile_dict["summary"]
        print(f"  Traditionalism:      {summ['traditionalism_score']:.2f}")
        print(f"  Individualism:       {summ['individualism_score']:.2f}")
        print(f"  Cognitive Style:     {summ['cognitive_style']}")
        
        # Advertising implications
        implications = get_advertising_implications(profile)
        print("\nAdvertising Implications:")
        print(f"  Value Appeals:       {', '.join(implications['value_appeals'][:4])}")
        print(f"  Messaging:           {', '.join(implications['messaging_approach'][:3])}")
        if implications['avoid']:
            print(f"  Avoid:               {', '.join(implications['avoid'])}")


if __name__ == "__main__":
    main()

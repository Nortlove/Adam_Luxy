/**
 * Calibration training scenarios — advertising-domain binary forecasts
 * with canonical historical/textbook answers.
 *
 * Based on the Tetlock/Mellers protocol (Good Judgment Project 2014,
 * ~40-minute training): give users probability-prediction reps with
 * immediate feedback and Brier-score aggregation so they learn to
 * produce calibrated estimates rather than round numbers like "70%"
 * that mean nothing.
 *
 * For v1 the scenarios are teaching cases with predetermined
 * outcomes drawn from well-documented advertising / marketing /
 * behavioral-economics findings. The training value isn't knowing
 * the specific answer — it's learning to calibrate *how* confident
 * you are when you don't know for sure.
 */

export type CalibrationScenario = {
  id: string;
  category: string; // for per-domain calibration tracking
  prompt: string; // the question
  context: string; // enough context to reason about it
  actual_outcome: "true" | "false";
  explanation: string; // shown after the user commits
  source: string; // where the canonical answer comes from
};

export const CALIBRATION_SCENARIOS: CalibrationScenario[] = [
  {
    id: "cal.display_ctr_median",
    category: "channel_benchmarks",
    prompt:
      "True or false: the median CTR for a standard display campaign is above 0.1%.",
    context:
      "You're estimating a typical CTR benchmark for programmatic display (desktop + mobile web, non-retargeted).",
    actual_outcome: "false",
    explanation:
      "Median display CTR sits around 0.05-0.08%. 0.1% is a useful *floor* for 'not broken,' but median performance is below it — which is why display optimizers chase scale rather than click efficiency.",
    source: "WordStream Display Benchmarks, multi-year median",
  },
  {
    id: "cal.viral_decay_90d",
    category: "customer_lifecycle",
    prompt:
      "True or false: a DTC brand that gets a viral social moment typically maintains its week-1 CPA efficiency through day 90.",
    context:
      "Consider a startup that has a TikTok or Twitter moment that drives a sudden acquisition spike.",
    actual_outcome: "false",
    explanation:
      "Viral moments compress the highest-intent audience into a short window. Once that cohort is consumed, CPA typically rises 2-5× as the campaign reaches less-intent populations. Day 90 CPA rarely resembles day 7.",
    source: "Segment-depletion dynamics (repeated-measures work)",
  },
  {
    id: "cal.recency_bias_creative",
    category: "human_decisions",
    prompt:
      "True or false: when an agency has to pick which creative to continue with after a short test, they will usually pick the one with the best 3-day performance even if a 14-day window would tell a different story.",
    context:
      "A common pattern in agency-led optimization: short-window creative-reallocation decisions.",
    actual_outcome: "true",
    explanation:
      "Recency bias is extensively documented in marketing decisions. Short-window CTR/CPA variance is often mistaken for signal. The platform's WhyLibrary is designed to surface this pattern as a pre-emptive warning.",
    source: "Kahneman & Tversky availability heuristic, applied to ad decisions",
  },
  {
    id: "cal.age_demo_prediction",
    category: "targeting",
    prompt:
      "True or false: for most DTC brands, psychographic / archetype targeting outperforms demographic (age + gender) targeting by ≥10% on CPA.",
    context:
      "Assume both targeting strategies have been given equivalent media budget and similar creative.",
    actual_outcome: "true",
    explanation:
      "The bilateral-cascade research shows construct-alignment targeting consistently outperforms demographic targeting — often by 15-30% on CPA for considered purchases. Demographics are weak correlates of the underlying psychological traits that drive conversion.",
    source: "INFORMATIV bilateral cascade evidence + broader psychographic-targeting literature",
  },
  {
    id: "cal.frequency_cap_effect",
    category: "channel_benchmarks",
    prompt:
      "True or false: dropping a display campaign from '5 impressions/user/day' to '2 impressions/user/day' typically reduces conversions by less than 30%.",
    context:
      "You're evaluating the conversion impact of tightening frequency caps on an ongoing retargeting campaign.",
    actual_outcome: "true",
    explanation:
      "Most conversions in high-frequency retargeting come from the first 1-2 exposures per session. Aggressive frequency capping usually loses less conversion than expected and can even help by reducing reactance / ad-blindness.",
    source: "Frequency decay research (Enhancement #34 Signal 6)",
  },
  {
    id: "cal.cpa_across_dsps",
    category: "platform_benchmarks",
    prompt:
      "True or false: if a brand runs the same creative + audience on two DSPs (say TTD and StackAdapt), CPA will typically vary by less than 20% between them.",
    context:
      "Assume both DSPs have similar inventory access.",
    actual_outcome: "false",
    explanation:
      "Per-DSP CPA variance of 30-80% is common even with 'identical' setups. Bid-clearing dynamics, inventory ordering, pixel-fire timing, and attribution window differences all contribute. DSPs are not interchangeable.",
    source: "Multi-DSP case studies (Digiday, AdExchanger)",
  },
  {
    id: "cal.lookalike_performance",
    category: "targeting",
    prompt:
      "True or false: a 1% lookalike audience built from a CRM export of high-LTV customers typically has CPA within 2× of the source seed cohort.",
    context:
      "You're evaluating whether to trust a Meta / platform-built lookalike for retargeting-alternative prospecting.",
    actual_outcome: "false",
    explanation:
      "1% lookalikes typically hit CPA 3-8× the source seed. The lookalike algorithm prioritizes reach, not conversion signal, and the platform's notion of similarity is correlational (behavioral features) rather than inferential (the psychological traits that drove the original conversions).",
    source: "INFORMATIV correlational-vs-inferential research; also independent lookalike benchmarks",
  },
  {
    id: "cal.attribution_window_effect",
    category: "measurement",
    prompt:
      "True or false: switching from a 7-day click / 1-day view window to 30-day click / 7-day view typically attributes 40% more conversions to ad spend.",
    context:
      "You're evaluating how attribution window choice affects reported performance.",
    actual_outcome: "true",
    explanation:
      "Longer attribution windows catch more of the long-tail conversions that happen after initial exposure. Reported ROAS can shift 30-70% just by changing the window — which is why stating the window is mandatory in any ROAS comparison.",
    source: "IAB DBPC and multi-platform attribution studies",
  },
  {
    id: "cal.ab_test_duration",
    category: "measurement",
    prompt:
      "True or false: a typical creative A/B test needs at least 2 weeks of data before conclusions can be drawn with reasonable confidence.",
    context:
      "Assume a mid-sized budget and standard display/social setup.",
    actual_outcome: "true",
    explanation:
      "With typical impression volumes, statistical significance on conversion differences rarely stabilizes before the 10-14 day mark. Day-of-week patterns alone require at least 7 days to average out. Earlier calls are almost always overfitting to recency.",
    source: "Standard frequentist power-analysis; also Bayesian stopping-rule work",
  },
  {
    id: "cal.backfire_from_overtargeting",
    category: "customer_lifecycle",
    prompt:
      "True or false: users who see the same ad 8+ times within 48 hours are less likely to convert on exposure 9 than they were on exposure 3.",
    context:
      "You're reasoning about reactance / ad fatigue in high-frequency retargeting.",
    actual_outcome: "true",
    explanation:
      "Reactance and ad-blindness kick in after modest repeated exposure. The frequency-decay curve is reliably observed: conversion rate per exposure declines after ~3-5 impressions, often reaches zero or negative by 8+. This is why the platform's Signal 6 detector looks for onset-of-reactance.",
    source: "INFORMATIV Enhancement #34 frequency-decay; broader ad-fatigue literature",
  },
];

export const BRIER_BINS = [
  { id: "bin_0", label: "0%", value: 0.0 },
  { id: "bin_10", label: "10%", value: 0.1 },
  { id: "bin_20", label: "20%", value: 0.2 },
  { id: "bin_30", label: "30%", value: 0.3 },
  { id: "bin_40", label: "40%", value: 0.4 },
  { id: "bin_50", label: "50%", value: 0.5 },
  { id: "bin_60", label: "60%", value: 0.6 },
  { id: "bin_70", label: "70%", value: 0.7 },
  { id: "bin_80", label: "80%", value: 0.8 },
  { id: "bin_90", label: "90%", value: 0.9 },
  { id: "bin_100", label: "100%", value: 1.0 },
];

export function brierScore(estimate: number, outcome: "true" | "false"): number {
  const outcomeValue = outcome === "true" ? 1 : 0;
  return Math.pow(estimate - outcomeValue, 2);
}

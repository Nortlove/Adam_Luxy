"""E3a — Customer Lifetime Value via BTYD models, segmented by archetype.

Closes the long-horizon CLV piece of E3. Three components:

    1. BG/NBD (Fader-Hardie-Lee 2005, Marketing Science 24(2)):
       Beta-Geometric / Negative-Binomial-Distribution model. Predicts
       expected number of future transactions given recency-frequency-
       observation history (x, t_x, T). Closed-form analytical formulas
       once parameters (r, alpha, a, b) are fit.

    2. Gamma-Gamma (Fader-Hardie 2013):
       Predicts expected monetary value per transaction given observed
       average. Conditional on BG/NBD's "buyer is alive" probability,
       gives expected revenue per future transaction.

    3. Per-archetype segmentation:
       Fit each model per archetype separately, OR fit pooled with
       archetype as a covariate. The substrate here supports the
       pooled-by-archetype path: returns per-archetype CLV estimates
       with uncertainty so the investor narrative can show
       'Status Seekers convert at $X CLV vs Disillusioned at $Y' —
       differentiation that's real, not invented.

Discipline anchors:
    - The fits depend on the `lifetimes` library (Cameron-Davidson-
      Pilon implementation of Fader-Hardie). Raises CLVLibsMissingError
      when absent (NOT silent None — a 'CLV estimate' that's actually
      None would silently misroute investor-facing reports).
    - Substrate ships the WRAPPER + per-archetype aggregator + data
      loader from Neo4j AdDecision/AdOutcome rows (M4 schema). The
      lifetimes-library fits happen at runtime when the lib is
      installed.
    - NO INVENTED MAGNITUDES. The substrate computes per-archetype
      CLV from real data; it does NOT bake in 'Status Seekers have
      Nx CLV vs Disillusioned' magnitudes. Those land when the fits
      run on actual outcome rows.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TransactionRow:
    """One buyer's recency-frequency-observation summary.

    Per BG/NBD convention:
        frequency: number of repeat transactions (x in F-H notation)
        recency: time of last transaction (t_x)
        T: observation period length
        monetary_value: average transaction value
        archetype: segment label for grouping
    """
    buyer_id: str
    frequency: int
    recency: float
    T: float
    monetary_value: float = 0.0
    archetype: str = ""


@dataclass
class CLVPrediction:
    """Per-buyer CLV prediction."""
    buyer_id: str
    archetype: str
    predicted_purchases: float          # E[Y(horizon) | x, t_x, T]
    expected_monetary_value: float      # E[M | x, m_x]
    predicted_clv: float                # purchases × monetary
    p_alive: float = 0.0                # P(alive | history)


@dataclass
class ArchetypeCLVAggregate:
    """Per-archetype CLV aggregate with uncertainty."""
    archetype: str
    n_buyers: int
    mean_clv: float
    median_clv: float
    p25_clv: float
    p75_clv: float
    mean_p_alive: float


@dataclass
class CLVFitDiagnostics:
    """Per-fit diagnostics for ops visibility."""
    archetypes_fit: int = 0
    archetypes_skipped_low_n: int = 0
    archetypes_failed: int = 0
    fitted_at_ts: float = 0.0
    library_versions: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class CLVLibsMissingError(RuntimeError):
    """Raised when CLV fit is requested but `lifetimes` isn't installed.

    Returning None on missing libs would let downstream investor-facing
    reports consume meaningless CLV silently — drift trap we exist to
    prevent.
    """
    pass


# -----------------------------------------------------------------------------
# Soft-import gate
# -----------------------------------------------------------------------------


def _try_import_lifetimes() -> Optional[Any]:
    try:
        import lifetimes  # noqa: F401
        return lifetimes
    except ImportError:
        return None


# -----------------------------------------------------------------------------
# Data loader from Neo4j (uses M4 schema's :DecisionContext rows)
# -----------------------------------------------------------------------------


def load_transactions_from_neo4j(
    driver: Optional[Any] = None,
    days_lookback: int = 365,
) -> List[TransactionRow]:
    """Pull buyer transaction summaries from Neo4j.

    Aggregates :DecisionContext rows + :AdOutcome rows per buyer:
        frequency = count of conversions in the window minus 1
                    (BG/NBD convention: x is REPEAT count)
        recency = days from first to last transaction
        T = days from first transaction to observation period end
        monetary_value = mean outcome_value across conversions

    Returns [] when Neo4j is unavailable or no data exists. Caller
    must handle empty list gracefully.
    """
    if driver is None:
        try:
            from adam.core.dependencies import get_neo4j_driver
            driver = get_neo4j_driver()
        except Exception:
            return []
    if driver is None:
        return []

    cypher = """
    MATCH (dc:DecisionContext)-[:HAD_OUTCOME]->(o:AdOutcome)
    WHERE dc.created_at * 1000 >= $cutoff_ts
      AND o.outcome_value > 0
    WITH dc.buyer_id AS buyer_id,
         dc.archetype AS archetype,
         collect({ts: dc.created_at, value: o.outcome_value}) AS txns
    WHERE buyer_id IS NOT NULL AND buyer_id <> ''
    RETURN buyer_id, archetype, txns
    LIMIT 50000
    """

    cutoff_ts = _epoch_ms_n_days_ago(days_lookback)
    rows: List[TransactionRow] = []
    try:
        with driver.session() as session:
            result = session.run(cypher, cutoff_ts=cutoff_ts)
            for record in result:
                buyer_id = record.get("buyer_id") or ""
                archetype = record.get("archetype") or "unknown"
                txns = record.get("txns") or []
                if not txns or not buyer_id:
                    continue
                row = _summarize_buyer_transactions(buyer_id, archetype, txns)
                if row is not None:
                    rows.append(row)
    except Exception as exc:
        logger.warning("CLV data loader failed: %s", exc)
        return []

    return rows


def _summarize_buyer_transactions(
    buyer_id: str, archetype: str, txns: List[Dict[str, Any]],
) -> Optional[TransactionRow]:
    """Convert raw transaction list to BG/NBD-ready (x, t_x, T, m)."""
    if not txns:
        return None
    timestamps = sorted(t["ts"] for t in txns if t.get("ts") is not None)
    values = [float(t.get("value", 0.0)) for t in txns if t.get("value", 0) > 0]
    if not timestamps or not values:
        return None

    first_ts = timestamps[0]
    last_ts = timestamps[-1]
    import time
    now_ts = time.time()

    days_first_to_last = (last_ts - first_ts) / 86400.0
    days_first_to_now = (now_ts - first_ts) / 86400.0

    # BG/NBD frequency = number of REPEAT transactions = total - 1
    frequency = max(0, len(timestamps) - 1)
    recency = days_first_to_last
    T = days_first_to_now
    if T <= 0:
        return None
    monetary_value = sum(values) / len(values) if values else 0.0

    return TransactionRow(
        buyer_id=buyer_id,
        frequency=frequency,
        recency=recency,
        T=T,
        monetary_value=monetary_value,
        archetype=archetype,
    )


def _epoch_ms_n_days_ago(days: int) -> int:
    import time
    return int((time.time() - days * 86400) * 1000)


# -----------------------------------------------------------------------------
# Fit + predict via `lifetimes` library
# -----------------------------------------------------------------------------


def fit_clv_for_archetype(
    rows: List[TransactionRow],
    horizon_days: float = 90.0,
    discount_rate_monthly: float = 0.01,
    min_buyers: int = 30,
) -> Tuple[List[CLVPrediction], Optional[ArchetypeCLVAggregate]]:
    """Fit BG/NBD + Gamma-Gamma for one archetype and predict CLV.

    Args:
        rows: TransactionRows for ONE archetype
        horizon_days: prediction horizon (default 90 = quarter)
        discount_rate_monthly: per-month discount for present-value CLV
        min_buyers: minimum buyer count to attempt fit (BG/NBD needs
            >= 30 buyers with frequency >= 1 to converge reliably)

    Returns (predictions, aggregate). Aggregate is None when buyer
    count is below min_buyers.

    Raises CLVLibsMissingError when `lifetimes` isn't installed.
    """
    if not rows:
        return [], None

    archetype = rows[0].archetype

    # Filter to repeat buyers (BG/NBD requires frequency observations)
    repeat_buyers = [r for r in rows if r.frequency > 0]
    if len(repeat_buyers) < min_buyers:
        return [], None

    lifetimes = _try_import_lifetimes()
    if lifetimes is None:
        raise CLVLibsMissingError(
            f"lifetimes library not installed; cannot fit CLV for "
            f"archetype {archetype!r}. Install with `pip install lifetimes`."
        )

    try:
        from lifetimes import BetaGeoFitter, GammaGammaFitter
        import numpy as np
    except ImportError as exc:
        raise CLVLibsMissingError(f"CLV deps missing: {exc}")

    frequencies = np.array([r.frequency for r in repeat_buyers])
    recencies = np.array([r.recency for r in repeat_buyers])
    Ts = np.array([r.T for r in repeat_buyers])
    monetary = np.array([r.monetary_value for r in repeat_buyers])

    # Fit BG/NBD (recency-frequency model)
    bgf = BetaGeoFitter(penalizer_coef=0.001)
    try:
        bgf.fit(frequencies, recencies, Ts)
    except Exception as exc:
        logger.warning("BG/NBD fit failed for %s: %s", archetype, exc)
        return [], None

    # Predict expected purchases over horizon
    expected_purchases = bgf.conditional_expected_number_of_purchases_up_to_time(
        horizon_days, frequencies, recencies, Ts,
    )
    p_alive = bgf.conditional_probability_alive(frequencies, recencies, Ts)

    # Fit Gamma-Gamma for monetary value (requires positive monetary values)
    valid_monetary = monetary > 0
    if not valid_monetary.any():
        # No monetary data — return predictions with monetary=0
        predictions = [
            CLVPrediction(
                buyer_id=r.buyer_id, archetype=archetype,
                predicted_purchases=float(expected_purchases[i]),
                expected_monetary_value=0.0,
                predicted_clv=0.0,
                p_alive=float(p_alive[i]),
            )
            for i, r in enumerate(repeat_buyers)
        ]
        return predictions, _aggregate_clv(predictions)

    try:
        ggf = GammaGammaFitter(penalizer_coef=0.0001)
        ggf.fit(frequencies[valid_monetary], monetary[valid_monetary])
        expected_monetary = ggf.conditional_expected_average_profit(
            frequencies, monetary,
        )
    except Exception as exc:
        logger.warning("Gamma-Gamma fit failed for %s: %s", archetype, exc)
        expected_monetary = monetary  # fallback to observed

    predictions = []
    for i, r in enumerate(repeat_buyers):
        p = float(expected_purchases[i])
        m = float(expected_monetary[i])
        clv = p * m
        predictions.append(CLVPrediction(
            buyer_id=r.buyer_id, archetype=archetype,
            predicted_purchases=p,
            expected_monetary_value=m,
            predicted_clv=clv,
            p_alive=float(p_alive[i]),
        ))

    return predictions, _aggregate_clv(predictions)


def _aggregate_clv(predictions: List[CLVPrediction]) -> Optional[ArchetypeCLVAggregate]:
    """Compute mean / quantile CLV aggregate over predictions."""
    if not predictions:
        return None
    archetype = predictions[0].archetype
    clvs = sorted(p.predicted_clv for p in predictions)
    n = len(clvs)
    mean_clv = sum(clvs) / n
    median_clv = clvs[n // 2]
    p25_clv = clvs[n // 4]
    p75_clv = clvs[(3 * n) // 4]
    mean_p_alive = sum(p.p_alive for p in predictions) / n

    return ArchetypeCLVAggregate(
        archetype=archetype,
        n_buyers=n,
        mean_clv=round(mean_clv, 4),
        median_clv=round(median_clv, 4),
        p25_clv=round(p25_clv, 4),
        p75_clv=round(p75_clv, 4),
        mean_p_alive=round(mean_p_alive, 4),
    )


# -----------------------------------------------------------------------------
# Per-archetype orchestrator
# -----------------------------------------------------------------------------


def fit_clv_per_archetype(
    rows: List[TransactionRow],
    horizon_days: float = 90.0,
    min_buyers_per_archetype: int = 30,
) -> Tuple[Dict[str, List[CLVPrediction]], Dict[str, ArchetypeCLVAggregate], CLVFitDiagnostics]:
    """Fit CLV separately for each archetype, return per-archetype results.

    This is the investor-narrative shape: 'Status Seekers have CLV
    distribution X; Disillusioned have CLV distribution Y' — fit per
    segment, aggregate per segment, compare per segment.

    Raises CLVLibsMissingError if `lifetimes` is unavailable AND any
    archetype has enough data to attempt a fit.
    """
    import time

    diag = CLVFitDiagnostics(fitted_at_ts=time.time())

    lifetimes = _try_import_lifetimes()
    if lifetimes is not None:
        diag.library_versions["lifetimes"] = getattr(
            lifetimes, "__version__", "unknown",
        )

    # Bucket rows by archetype
    by_archetype: Dict[str, List[TransactionRow]] = {}
    for r in rows:
        by_archetype.setdefault(r.archetype or "unknown", []).append(r)

    predictions_by_archetype: Dict[str, List[CLVPrediction]] = {}
    aggregates: Dict[str, ArchetypeCLVAggregate] = {}

    for archetype, archetype_rows in by_archetype.items():
        try:
            preds, agg = fit_clv_for_archetype(
                archetype_rows,
                horizon_days=horizon_days,
                min_buyers=min_buyers_per_archetype,
            )
            if agg is None:
                diag.archetypes_skipped_low_n += 1
                continue
            predictions_by_archetype[archetype] = preds
            aggregates[archetype] = agg
            diag.archetypes_fit += 1
        except CLVLibsMissingError:
            raise
        except Exception as exc:
            diag.archetypes_failed += 1
            diag.errors.append(f"{archetype}: {exc}")

    return predictions_by_archetype, aggregates, diag

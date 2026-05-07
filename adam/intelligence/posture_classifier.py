# =============================================================================
# 5-class posture classifier — v0.1 URL-token TF-IDF + multinomial logreg
# Location: adam/intelligence/posture_classifier.py
# =============================================================================
"""Round-1 posture classifier trained on the 20-URL bootstrap labels.

Per the 2026-05-03 directive: train on the 20 labels persisted to
date, evaluate via leave-one-out cross-validation, compute one-vs-
rest macro-averaged AUC + per-class AUC + bootstrap 95% CI on the
macro estimate. Gate criterion: macro-AUC point estimate ≥ 0.30
(chance for 5-class = 0.20).

V0.1 FEATURE REPRESENTATION

URL-token TF-IDF + multinomial logistic regression. Honest
tag — the directive's production target (Phase 2 line 173) is a
frozen sentence-transformer (all-mpnet-base-v2) over rendered page
TEXT, not the URL string. For n=20 + a 0.30-vs-0.20 gate, URL-token
TF-IDF is the defensible interim that:

  * clears the gate threshold defensibly without hand-tuning,
  * doesn't require fetching 20 pages over the network,
  * is interpretable + auditable.

The sentence-transformer + page-fetch path is sibling slice (Phase 2
post-pilot work + v3 Phase 1 corpus-fetch infrastructure).

THE PRIMITIVE

  * ``URLPostureClassifier`` — frozen-after-fit class with
    ``fit(urls, labels)`` + ``predict(urls)`` + ``predict_proba(urls)``.
  * ``loo_cv_evaluate(urls, labels)`` returns LooCVResult with
    per-class AUC, macro AUC, bootstrap 95% CI, and per-sample
    held-out predictions.
  * ``persist_classifier_artifact(classifier, path)`` writes a
    JSON-lines artifact (weights + vocab + version stamp).
  * ``load_classifier_artifact(path)`` round-trips the persisted
    classifier for inference.

DISCIPLINE (B3-LUXY a/b/c/d)

(a) Citations: 2026-05-03 train-and-evaluate directive + Phase 2
    line 173 (sentence-transformer is production target — honest-
    tagged here as v0.1 substrate). LOOCV pattern from sklearn's
    LeaveOneOut + roc_auc_score(multi_class="ovr"). Bootstrap CI
    from 1000-iteration resample of held-out predictions.

(b) Tests pin: deterministic from seed; fit + predict round-trips;
    predict_proba sums to 1; LOOCV held-out predictions = n_samples;
    macro-AUC bootstrap CI bounds inclusive; persist + load lossless.

(c) calibration_pending=True. v0.1 TF-IDF substrate; sentence-
    transformer + page-fetch is Phase 2 production target.
    A14 flag: PHASE_2_POSTURE_CLASSIFIER_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):
    * Sentence-transformer embeddings over rendered page text.
    * Active-learning loop integration (Slice 26 substrate is
      ready; the integration path goes via predict_proba + entropy).
    * Per-class threshold calibration (Platt scaling / isotonic).
    * Out-of-distribution detection on production traffic URLs.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# A14 PHASE_2_POSTURE_CLASSIFIER_PILOT_PENDING

CLASSIFIER_VERSION: str = "v0.1-url-tfidf-logreg"
DEFAULT_RANDOM_STATE: int = 2026


# =============================================================================
# URL tokenization
# =============================================================================


def _tokenize_url(url: str) -> List[str]:
    """Extract semantically meaningful tokens from a URL.

    Splits on ``/`` ``-`` ``_`` ``.`` ``?`` ``=`` ``&``; drops
    common protocol / TLD noise; lower-cases. Returns a list of
    word-like tokens that TF-IDF can vectorize.
    """
    if not url:
        return []
    cleaned = re.sub(r"^https?://", "", url.lower())
    raw = re.split(r"[/\-_.?=&#]+", cleaned)
    # Drop empties, pure-numeric, very short, and TLD noise.
    noise = {"www", "com", "org", "net", "io", "co", "us", "edu"}
    tokens: List[str] = []
    for t in raw:
        t = t.strip()
        if not t:
            continue
        if t in noise:
            continue
        if len(t) < 2:
            continue
        if t.isdigit():
            continue
        tokens.append(t)
    return tokens


# =============================================================================
# Classifier
# =============================================================================


@dataclass
class URLPostureClassifier:
    """v0.1 URL-token TF-IDF + multinomial logreg classifier.

    Fit-once-then-frozen contract: vectorizer + logreg both trained
    in fit(); predict() / predict_proba() use the frozen artifacts."""

    classes_: Optional[List[str]] = None
    vectorizer: Any = None  # sklearn TfidfVectorizer
    model: Any = None       # sklearn LogisticRegression
    random_state: int = DEFAULT_RANDOM_STATE
    version: str = CLASSIFIER_VERSION
    n_train: int = 0
    # Class-weight setting last used in fit(); persisted for
    # reproducibility + for round-trip-load to record the training
    # regime that produced the artifact. None = uniform; "balanced"
    # = sklearn's inverse-frequency weighting.
    class_weight: Any = "balanced"

    def fit(
        self, urls: List[str], labels: List[str],
        class_weight: Any = "balanced",
    ) -> "URLPostureClassifier":
        """Fit on (urls, labels). Validates aligned shapes; raises
        on mismatch. Sets self.classes_ to the sorted unique labels.

        Class-weight handling (G1.path4 amendment 2026-05-06):
            class_weight="balanced" (default) — sklearn's standard
                cost-sensitive-learning correction:
                n_samples / (n_classes * np.bincount(y)). Each class
                contributes inverse-frequency-weighted gradient mass
                during fit; the optimizer no longer collapses toward
                the modal class under imbalance + few-shot.
            class_weight=None — uniform weights (the prior behavior).
                Provided for backwards-compat + as the regression
                control in tests that pin the class-collapse signal.
            class_weight=dict — caller-supplied per-class weights;
                passed through to LogisticRegression unchanged.

        Default change rationale: the v0.1 round-3 checkpoint
        evaluation against the held-out fixture (session #002 EVE
        block, 2026-05-02) showed top-1=0.22 with 49/50 predictions
        collapsed to INFORMATION_FORAGING — a class-collapse signal
        attributable to imbalance + few-shot under-fitting under
        uniform weights. "balanced" mode is sklearn's documented
        cost-sensitive correction; no novel methodology.
        """
        if len(urls) != len(labels):
            raise ValueError(
                f"len(urls)={len(urls)} != len(labels)={len(labels)}"
            )
        if not urls:
            raise ValueError("Cannot fit on empty data")

        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression

        token_lists = [_tokenize_url(u) for u in urls]
        # Join tokens back into a space-separated string for the
        # TfidfVectorizer's default analyzer.
        joined = [" ".join(t) for t in token_lists]

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            max_df=1.0,
            lowercase=False,  # already lowered in tokenizer
            token_pattern=r"\b\w+\b",
        )
        X = self.vectorizer.fit_transform(joined)

        self.classes_ = sorted(set(labels))
        if len(self.classes_) < 2:
            raise ValueError(
                f"Need at least 2 distinct classes; got "
                f"{self.classes_}"
            )

        self.model = LogisticRegression(
            multi_class="multinomial",
            solver="lbfgs",
            max_iter=2000,
            random_state=self.random_state,
            C=1.0,
            class_weight=class_weight,
        )
        self.model.fit(X, labels)
        self.n_train = len(urls)
        self.class_weight = class_weight
        return self

    def predict_proba(self, urls: List[str]) -> np.ndarray:
        """Per-class probability matrix; shape (n_urls, n_classes).
        Column order matches self.classes_."""
        if self.vectorizer is None or self.model is None:
            raise RuntimeError("Call fit() first")
        joined = [" ".join(_tokenize_url(u)) for u in urls]
        X = self.vectorizer.transform(joined)
        # Reorder columns to match self.classes_ deterministic ordering.
        proba = self.model.predict_proba(X)
        order = [list(self.model.classes_).index(c) for c in self.classes_]
        return proba[:, order]

    def predict(self, urls: List[str]) -> List[str]:
        """Argmax label per URL."""
        proba = self.predict_proba(urls)
        return [
            self.classes_[int(np.argmax(row))] for row in proba
        ]


# =============================================================================
# Leave-one-out cross-validation
# =============================================================================


@dataclass(frozen=True)
class LooCVResult:
    """Outcome of LOOCV: held-out predictions + AUC metrics."""

    n_samples: int
    classes: List[str]
    held_out_predicted_proba: np.ndarray  # (n_samples, n_classes)
    held_out_true_labels: List[str]
    per_class_auc: Dict[str, float]
    macro_auc: float
    macro_auc_bootstrap_ci_low: float
    macro_auc_bootstrap_ci_high: float
    bootstrap_n: int = 1000
    seed: int = DEFAULT_RANDOM_STATE


def _per_class_one_vs_rest_auc(
    y_true: List[str],
    y_proba: np.ndarray,
    classes: List[str],
) -> Dict[str, float]:
    """One-vs-rest AUC per class. Returns 0.5 (chance) when a class
    has only one true outcome (no signal to score), so the metric
    is well-defined even on tiny n."""
    from sklearn.metrics import roc_auc_score

    out: Dict[str, float] = {}
    for ix, cls in enumerate(classes):
        binary = np.array([1 if y == cls else 0 for y in y_true])
        if binary.sum() == 0 or binary.sum() == len(binary):
            out[cls] = 0.5
            continue
        try:
            auc = float(
                roc_auc_score(binary, y_proba[:, ix])
            )
            out[cls] = auc
        except Exception:
            out[cls] = 0.5
    return out


def _bootstrap_macro_auc_ci(
    y_true: List[str],
    y_proba: np.ndarray,
    classes: List[str],
    *,
    n_bootstrap: int = 1000,
    seed: int = DEFAULT_RANDOM_STATE,
) -> Tuple[float, float]:
    """Bootstrap 95% CI on macro-AUC by resampling held-out
    predictions with replacement."""
    rng = np.random.default_rng(seed)
    n = len(y_true)
    samples: List[float] = []
    for _ in range(n_bootstrap):
        idx = rng.integers(low=0, high=n, size=n)
        boot_y = [y_true[i] for i in idx]
        boot_proba = y_proba[idx, :]
        per_class = _per_class_one_vs_rest_auc(
            boot_y, boot_proba, classes,
        )
        macro = float(np.mean(list(per_class.values())))
        samples.append(macro)
    samples_arr = np.array(samples)
    return (
        float(np.percentile(samples_arr, 2.5)),
        float(np.percentile(samples_arr, 97.5)),
    )


def loo_cv_evaluate(
    urls: List[str],
    labels: List[str],
    *,
    bootstrap_n: int = 1000,
    seed: int = DEFAULT_RANDOM_STATE,
) -> LooCVResult:
    """Leave-one-out CV: hold out each (url, label) once; train on
    the remaining n-1; record held-out predict_proba.

    Then compute per-class one-vs-rest AUC + macro AUC + bootstrap
    95% CI.
    """
    from sklearn.model_selection import LeaveOneOut

    n = len(urls)
    if n < 2:
        raise ValueError(
            f"LOOCV requires n >= 2; got n={n}"
        )

    classes = sorted(set(labels))
    n_classes = len(classes)
    held_out_proba = np.zeros((n, n_classes), dtype=float)
    held_out_true: List[str] = [""] * n

    loo = LeaveOneOut()
    urls_arr = np.array(urls)
    labels_arr = np.array(labels)

    for train_idx, test_idx in loo.split(urls_arr):
        train_urls = urls_arr[train_idx].tolist()
        train_labels = labels_arr[train_idx].tolist()
        test_url = urls_arr[test_idx][0]
        test_label = labels_arr[test_idx][0]

        # Train on the n-1 fold.
        clf = URLPostureClassifier(random_state=seed)
        # Skip if held-out class is absent from training fold —
        # still emit a chance-row so n_samples stays consistent.
        if test_label not in set(train_labels):
            held_out_proba[test_idx[0], :] = 1.0 / n_classes
            held_out_true[test_idx[0]] = test_label
            continue

        clf.fit(train_urls, train_labels)
        # If clf.classes_ ⊆ classes, align columns.
        proba = clf.predict_proba([test_url])[0]
        col_map = {c: i for i, c in enumerate(clf.classes_)}
        for j, c in enumerate(classes):
            if c in col_map:
                held_out_proba[test_idx[0], j] = proba[col_map[c]]
            else:
                held_out_proba[test_idx[0], j] = 0.0
        # Renormalize in case of missing-class column zeros.
        row_sum = held_out_proba[test_idx[0], :].sum()
        if row_sum > 0:
            held_out_proba[test_idx[0], :] /= row_sum
        held_out_true[test_idx[0]] = test_label

    per_class = _per_class_one_vs_rest_auc(
        held_out_true, held_out_proba, classes,
    )
    macro = float(np.mean(list(per_class.values())))

    ci_low, ci_high = _bootstrap_macro_auc_ci(
        held_out_true, held_out_proba, classes,
        n_bootstrap=bootstrap_n, seed=seed,
    )

    return LooCVResult(
        n_samples=n,
        classes=classes,
        held_out_predicted_proba=held_out_proba,
        held_out_true_labels=held_out_true,
        per_class_auc=per_class,
        macro_auc=macro,
        macro_auc_bootstrap_ci_low=ci_low,
        macro_auc_bootstrap_ci_high=ci_high,
        bootstrap_n=bootstrap_n,
        seed=seed,
    )


# =============================================================================
# Persistence — JSON-lines artifact (weights + vocab + version stamp)
# =============================================================================


def persist_classifier_artifact(
    classifier: URLPostureClassifier, path: str,
    *,
    eval_summary: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist classifier as a self-contained JSON-lines artifact:
    line 0 header (version + classes + n_train + eval summary);
    line 1 vectorizer vocab + idf; line 2 logreg coefficients +
    intercept."""
    if classifier.vectorizer is None or classifier.model is None:
        raise RuntimeError("Cannot persist unfitted classifier")

    vocab = {
        str(k): int(v)
        for k, v in classifier.vectorizer.vocabulary_.items()
    }
    idf = list(map(float, classifier.vectorizer.idf_))
    coef = classifier.model.coef_.tolist()
    intercept = list(map(float, classifier.model.intercept_))
    model_classes = list(map(str, classifier.model.classes_))

    header = {
        "_record_type": "classifier_header",
        "version": classifier.version,
        "classes": list(classifier.classes_) if classifier.classes_ else [],
        "n_train": classifier.n_train,
        "random_state": classifier.random_state,
        # G1.path4: persist the class_weight regime for reproducibility.
        # "balanced" / None / dict — JSON-serialized as-is.
        "class_weight": classifier.class_weight,
    }
    if eval_summary is not None:
        header["eval_summary"] = eval_summary

    vec_record = {
        "_record_type": "vectorizer",
        "vocab": vocab,
        "idf": idf,
        "ngram_range": list(classifier.vectorizer.ngram_range),
    }
    model_record = {
        "_record_type": "logreg",
        "coef": coef,
        "intercept": intercept,
        "model_classes": model_classes,
    }

    with open(path, "w") as f:
        f.write(json.dumps(header) + "\n")
        f.write(json.dumps(vec_record) + "\n")
        f.write(json.dumps(model_record) + "\n")


def load_classifier_artifact(path: str) -> URLPostureClassifier:
    """Load + reconstruct a persisted classifier."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression

    header: Dict[str, Any] = {}
    vec_data: Dict[str, Any] = {}
    model_data: Dict[str, Any] = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            t = payload.pop("_record_type", None)
            if t == "classifier_header":
                header = payload
            elif t == "vectorizer":
                vec_data = payload
            elif t == "logreg":
                model_data = payload

    vec = TfidfVectorizer(
        ngram_range=tuple(vec_data["ngram_range"]),
        lowercase=False,
        token_pattern=r"\b\w+\b",
    )
    vec.vocabulary_ = vec_data["vocab"]
    # Build idf_ aligned to vocab indices.
    idf_arr = np.array(vec_data["idf"], dtype=float)
    vec.idf_ = idf_arr

    model = LogisticRegression(multi_class="multinomial")
    model.classes_ = np.array(model_data["model_classes"])
    model.coef_ = np.array(model_data["coef"], dtype=float)
    model.intercept_ = np.array(
        model_data["intercept"], dtype=float,
    )
    # Need n_features_in_ for predict path consistency.
    model.n_features_in_ = model.coef_.shape[1]

    # G1.path4: round-trip the class_weight regime when present.
    # Older artifacts (pre-path4) lack this key → default to None
    # (uniform), which is the regime they were trained under.
    class_weight = header.get("class_weight", None)
    if class_weight == "balanced":
        cw = "balanced"
    elif class_weight is None:
        cw = None
    else:
        cw = class_weight  # dict pass-through

    clf = URLPostureClassifier(
        classes_=list(header.get("classes") or []),
        vectorizer=vec,
        model=model,
        random_state=int(header.get("random_state") or DEFAULT_RANDOM_STATE),
        version=str(header.get("version") or CLASSIFIER_VERSION),
        n_train=int(header.get("n_train") or 0),
        class_weight=cw,
    )
    return clf


# =============================================================================
# Entropy-based uncertainty sampling (round 2+)
# =============================================================================


def predict_proba_with_entropy(
    classifier: URLPostureClassifier,
    urls: List[str],
) -> List[Tuple[str, str, np.ndarray, float]]:
    """Score candidate URLs; return list of
    (url, predicted_class, proba_vector, entropy) per URL.

    Higher entropy = more uncertain → top candidates for active-
    learning round 2."""
    proba = classifier.predict_proba(urls)
    out: List[Tuple[str, str, np.ndarray, float]] = []
    for url, row in zip(urls, proba):
        predicted_class = classifier.classes_[int(np.argmax(row))]
        # Shannon entropy in nats; clip to avoid log(0).
        clipped = np.clip(row, 1e-12, 1.0)
        entropy = float(-np.sum(clipped * np.log(clipped)))
        out.append((url, predicted_class, row, entropy))
    return out

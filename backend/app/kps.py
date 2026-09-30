"""
KPS (Key Policy Understanding / Policy Simplification) Rating.

Calculates a 0-100 score measuring how effectively PolicyLens converted a
real, uploaded insurance policy into understandable, actionable information.

Every component is derived deterministically from the actual analysis JSON
produced by analysis_graph.run_policy_analysis() and the readability scores
already computed for that specific document. No LLM self-grading, no random
or hardcoded values — if the analysis is empty or weak, the score reflects
that.

Weights (must sum to 1.0):
  Coverage Understanding        20%
  Exclusion Understanding       20%
  Condition/Waiting Period      15%
  Source Traceability           15%
  Plain-Language Simplification 15%
  Attention Point Detection     15%
"""

WEIGHTS = {
    "coverageUnderstanding": 0.20,
    "exclusionUnderstanding": 0.20,
    "conditionUnderstanding": 0.15,
    "sourceTraceability": 0.15,
    "plainLanguage": 0.15,
    "attentionDetection": 0.15,
}

TARGET_KPS = 80

ALL_LIST_FIELDS = [
    "coverage", "exclusions", "waitingPeriods", "claimConditions",
    "limits", "deductibles", "importantDates", "attentionPoints", "importantClauses",
]

MIN_EXPLANATION_CHARS = 25       # below this, explanation is too thin to be "explained"
IDEAL_EXPLANATION_CHARS = 220    # a full, informative-but-concise explanation
MAX_USEFUL_EXPLANATION_CHARS = 500  # beyond this, likely a copy-pasted clause, not a simplification

PLACEHOLDER_VALUES = {"", "n/a", "na", "none", "unknown", "-", "null"}


def _is_meaningful_text(value) -> bool:
    if not isinstance(value, str):
        return False
    return value.strip().lower() not in PLACEHOLDER_VALUES and len(value.strip()) > 0


def _has_valid_source(item: dict) -> bool:
    page = item.get("page")
    section = item.get("section")
    return _is_meaningful_text(str(page) if page is not None else "") and _is_meaningful_text(section)


def _has_real_explanation(item: dict) -> bool:
    explanation = item.get("explanation", "")
    return _is_meaningful_text(explanation) and len(explanation.strip()) >= MIN_EXPLANATION_CHARS


def _explanation_quality(item: dict) -> float:
    """
    Score 0-1: rewards explanations that are substantial enough to be useful
    but not so long they're just a copy-pasted raw clause. Peaks at
    IDEAL_EXPLANATION_CHARS, decays outside that range.
    """
    explanation = item.get("explanation", "")
    if not _is_meaningful_text(explanation):
        return 0.0
    length = len(explanation.strip())
    if length < MIN_EXPLANATION_CHARS:
        return length / MIN_EXPLANATION_CHARS * 0.4  # partial credit for very short stubs
    if length <= IDEAL_EXPLANATION_CHARS:
        return 0.4 + 0.6 * ((length - MIN_EXPLANATION_CHARS) / (IDEAL_EXPLANATION_CHARS - MIN_EXPLANATION_CHARS))
    if length <= MAX_USEFUL_EXPLANATION_CHARS:
        # linear decay from 1.0 down to 0.5 as it grows toward the "too long" boundary
        span = MAX_USEFUL_EXPLANATION_CHARS - IDEAL_EXPLANATION_CHARS
        return 1.0 - 0.5 * ((length - IDEAL_EXPLANATION_CHARS) / span)
    return 0.5  # very long — likely an unsimplified copy of the clause, still some value


def _category_score(items: list, expected_min_items: int = 1) -> float:
    """
    Score 0-100 for a category of extracted items: rewards items that were
    both found AND properly explained with a valid source reference.
    If no items were extracted at all, score is 0 (nothing to understand).
    """
    if not items:
        return 0.0

    explained_and_sourced = 0
    quality_sum = 0.0
    for item in items:
        quality = _explanation_quality(item)
        quality_sum += quality
        if _has_real_explanation(item) and _has_valid_source(item):
            explained_and_sourced += 1

    coverage_ratio = explained_and_sourced / len(items)
    avg_quality = quality_sum / len(items)

    # Volume factor: a policy that yields very few items relative to a
    # reasonable minimum is penalized lightly (extraction may be incomplete),
    # but we never reward volume alone — quality dominates.
    volume_factor = min(1.0, len(items) / max(1, expected_min_items))

    score = (0.6 * coverage_ratio + 0.4 * avg_quality) * (0.85 + 0.15 * volume_factor)
    return round(max(0.0, min(1.0, score)) * 100, 1)


def _source_traceability(analysis: dict) -> float:
    """
    Across every extracted insight in the whole analysis, what fraction have
    a valid page AND section reference back to the source document.
    """
    all_items = []
    for field in ALL_LIST_FIELDS:
        all_items.extend(analysis.get(field, []) or [])

    if not all_items:
        return 0.0

    sourced = sum(1 for item in all_items if _has_valid_source(item))
    return round((sourced / len(all_items)) * 100, 1)


def _plain_language_score(analysis: dict, readability_before: float, readability_after: float) -> float:
    """
    Measures whether complex policy clauses were converted into concise,
    understandable explanations. Two independent, real signals combined:

    1. Readability lift: how much clearer the AI summary reads vs the raw
       policy text (Flesch Reading Ease, already computed per-document).
    2. Explanation concision: average explanation-quality score across every
       extracted item (rewards concise, informative explanations; penalizes
       explanations that are just long copy-pasted clauses or too thin).
    """
    all_items = []
    for field in ALL_LIST_FIELDS:
        all_items.extend(analysis.get(field, []) or [])

    if all_items:
        concision_score = sum(_explanation_quality(i) for i in all_items) / len(all_items)
    else:
        concision_score = 0.0

    # Readability lift, normalized: if summary reads at least as clear as
    # the raw text, that's a full readability contribution; if it reads
    # worse (rare, e.g. very short raw text), contribution shrinks.
    if readability_before <= 0 and readability_after <= 0:
        readability_lift = 0.5  # no usable signal either way — neutral midpoint
    else:
        delta = readability_after - readability_before
        # +30 point Flesch improvement or more is treated as a strong full-credit lift
        readability_lift = max(0.0, min(1.0, 0.5 + (delta / 60)))

    score = (0.55 * concision_score) + (0.45 * readability_lift)
    return round(max(0.0, min(1.0, score)) * 100, 1)


def _attention_detection_score(analysis: dict) -> float:
    """
    Rewards actually surfacing risk: attention points found and explained,
    plus how many exclusions/waiting-period/condition items were flagged
    with meaningful (medium/high) severity rather than left as neutral facts.
    """
    attention_points = analysis.get("attentionPoints", []) or []
    attention_base = _category_score(attention_points, expected_min_items=2)

    risk_bearing_fields = ["exclusions", "waitingPeriods", "claimConditions", "limits", "deductibles"]
    risk_items = []
    for field in risk_bearing_fields:
        risk_items.extend(analysis.get(field, []) or [])

    if risk_items:
        flagged = sum(1 for i in risk_items if i.get("severity") in ("high", "medium"))
        flag_ratio = flagged / len(risk_items)
    else:
        flag_ratio = 0.0

    score = 0.65 * (attention_base / 100) + 0.35 * flag_ratio
    return round(max(0.0, min(1.0, score)) * 100, 1)


def _label_for_score(score: float) -> str:
    if score >= 90:
        return "Excellent understanding"
    if score >= 80:
        return "Strong understanding"
    if score >= 70:
        return "Moderate understanding"
    return "Needs improvement"


def calculateKPS(policy_analysis: dict, readability_before: float = 0.0, readability_after: float = 0.0) -> dict:
    """
    Compute the KPS (Key Policy Understanding / Policy Simplification) rating
    for a single analyzed policy.

    Args:
        policy_analysis: the structured analysis JSON returned by
            analysis_graph.run_policy_analysis() (the "result" dict —
            summary/coverage/exclusions/waitingPeriods/etc).
        readability_before: Flesch Reading Ease of the raw extracted policy text.
        readability_after: Flesch Reading Ease of the AI-generated summary.

    Returns:
        {
          "overallScore": int (0-100),
          "target": 80,
          "components": {
            "coverageUnderstanding": float,
            "exclusionUnderstanding": float,
            "conditionUnderstanding": float,
            "sourceTraceability": float,
            "plainLanguage": float,
            "attentionDetection": float,
          },
          "label": str,
        }
    """
    analysis = policy_analysis or {}

    coverage_understanding = _category_score(analysis.get("coverage", []) or [], expected_min_items=3)
    exclusion_understanding = _category_score(analysis.get("exclusions", []) or [], expected_min_items=3)

    condition_items = []
    for field in ("waitingPeriods", "claimConditions", "limits", "deductibles"):
        condition_items.extend(analysis.get(field, []) or [])
    condition_understanding = _category_score(condition_items, expected_min_items=3)

    source_traceability = _source_traceability(analysis)
    plain_language = _plain_language_score(analysis, readability_before, readability_after)
    attention_detection = _attention_detection_score(analysis)

    components = {
        "coverageUnderstanding": coverage_understanding,
        "exclusionUnderstanding": exclusion_understanding,
        "conditionUnderstanding": condition_understanding,
        "sourceTraceability": source_traceability,
        "plainLanguage": plain_language,
        "attentionDetection": attention_detection,
    }

    overall = (
        components["coverageUnderstanding"] * WEIGHTS["coverageUnderstanding"]
        + components["exclusionUnderstanding"] * WEIGHTS["exclusionUnderstanding"]
        + components["conditionUnderstanding"] * WEIGHTS["conditionUnderstanding"]
        + components["sourceTraceability"] * WEIGHTS["sourceTraceability"]
        + components["plainLanguage"] * WEIGHTS["plainLanguage"]
        + components["attentionDetection"] * WEIGHTS["attentionDetection"]
    )
    overall = round(max(0.0, min(100.0, overall)))

    return {
        "overallScore": overall,
        "target": TARGET_KPS,
        "components": {k: round(v) for k, v in components.items()},
        "label": _label_for_score(overall),
    }

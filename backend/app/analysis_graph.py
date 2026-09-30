"""
LangGraph policy analysis: simple linear graph.

START -> validate_policy -> analyze (summary, coverage, exclusions,
attention points, important clauses) -> structured_output -> END

Kept intentionally simple per MVP constraints — no agent swarm.
"""
import json
from typing import TypedDict
from langgraph.graph import StateGraph, END

from app import llm

ANALYSIS_PROMPT_TEMPLATE = """You are an insurance policy analysis assistant. You will be given SANITIZED
(PII-redacted) insurance policy text extracted from a real policy document, tagged with page numbers.

Analyze ONLY the content provided. Do NOT fabricate information that is not present in the text.
If a category has no supporting content in the text, return an empty list for it.

Return STRICT JSON matching this exact schema (no markdown, no commentary):

{{
  "summary": "2-4 sentence plain-language summary of the policy",
  "coverage": [{{"title": "", "explanation": "", "severity": "low", "page": "", "section": ""}}],
  "exclusions": [{{"title": "", "explanation": "", "severity": "high", "page": "", "section": ""}}],
  "waitingPeriods": [{{"title": "", "explanation": "", "severity": "medium", "page": "", "section": ""}}],
  "claimConditions": [{{"title": "", "explanation": "", "severity": "medium", "page": "", "section": ""}}],
  "limits": [{{"title": "", "explanation": "", "severity": "medium", "page": "", "section": ""}}],
  "deductibles": [{{"title": "", "explanation": "", "severity": "medium", "page": "", "section": ""}}],
  "importantDates": [{{"title": "", "explanation": "", "severity": "low", "page": "", "section": ""}}],
  "attentionPoints": [{{"title": "", "explanation": "", "severity": "high", "page": "", "section": ""}}],
  "importantClauses": [{{"title": "", "explanation": "", "severity": "medium", "page": "", "section": ""}}]
}}

severity must be one of: "high", "medium", "low".

POLICY TEXT:
{policy_text}
"""

REQUIRED_LIST_FIELDS = [
    "coverage", "exclusions", "waitingPeriods", "claimConditions",
    "limits", "deductibles", "importantDates", "attentionPoints", "importantClauses",
]


class AnalysisState(TypedDict):
    sanitized_text: str
    valid: bool
    error: str | None
    raw_llm_output: str | None
    provider_used: str | None
    fallback_used: bool
    result: dict | None


def _validate_policy(state: AnalysisState) -> AnalysisState:
    text = state["sanitized_text"]
    if not text or len(text.strip()) < 50:
        state["valid"] = False
        state["error"] = "Document text is too short to analyze."
    else:
        state["valid"] = True
    return state


def _analyze(state: AnalysisState) -> AnalysisState:
    if not state["valid"]:
        return state

    # Truncate very large documents to keep prompt manageable for MVP
    text = state["sanitized_text"]
    max_chars = 18000
    if len(text) > max_chars:
        text = text[:max_chars]

    prompt = ANALYSIS_PROMPT_TEMPLATE.format(policy_text=text)

    try:
        llm_result = llm.generate(prompt)
        state["raw_llm_output"] = llm_result.text
        state["provider_used"] = llm_result.provider_used
        state["fallback_used"] = llm_result.fallback_used
    except llm.LLMUnavailableError as e:
        state["valid"] = False
        state["error"] = f"LLM analysis unavailable: {e}"
        return state

    try:
        parsed = llm.extract_json(llm_result.text)
    except ValueError as e:
        state["valid"] = False
        state["error"] = f"Model returned malformed JSON: {e}"
        return state

    # Defensive normalization: ensure all expected fields exist
    parsed.setdefault("summary", "")
    for field in REQUIRED_LIST_FIELDS:
        if field not in parsed or not isinstance(parsed[field], list):
            parsed[field] = []

    state["result"] = parsed
    return state


def _build_graph():
    graph = StateGraph(AnalysisState)
    graph.add_node("validate_policy", _validate_policy)
    graph.add_node("analyze", _analyze)
    graph.set_entry_point("validate_policy")
    graph.add_edge("validate_policy", "analyze")
    graph.add_edge("analyze", END)
    return graph.compile()


_GRAPH = _build_graph()


def run_policy_analysis(sanitized_text: str) -> dict:
    initial: AnalysisState = {
        "sanitized_text": sanitized_text,
        "valid": True,
        "error": None,
        "raw_llm_output": None,
        "provider_used": None,
        "fallback_used": False,
        "result": None,
    }
    final_state = _GRAPH.invoke(initial)

    return {
        "success": final_state["result"] is not None,
        "error": final_state.get("error"),
        "result": final_state.get("result"),
        "provider_used": final_state.get("provider_used"),
        "fallback_used": final_state.get("fallback_used", False),
    }

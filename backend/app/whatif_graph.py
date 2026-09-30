"""
What-If Policy Simulator: LangGraph workflow.

USER SCENARIO -> RAG retrieval -> relevant clauses -> LLM -> scenario analysis.
Never states a claim WILL definitely be accepted/rejected — uses cautious language.
"""
from typing import TypedDict
from langgraph.graph import StateGraph, END

from app import llm, rag

WHATIF_PROMPT_TEMPLATE = """You are a "What-If Policy Simulator" for an insurance policy. You are given
a hypothetical user scenario and RELEVANT EXCERPTS from the actual policy (already PII-redacted).

IMPORTANT RULES:
- Never state that a claim WILL definitely be accepted or rejected.
- Use cautious, conditional language such as "According to the uploaded policy...",
  "Potential condition...", "This clause may affect coverage...".
- Only reference clauses present in the excerpts. Do not invent policy terms.
- If the excerpts are insufficient to address the scenario, say so plainly.

Return STRICT JSON (no markdown, no commentary) with this schema:

{{
  "scenario": "restate the user's scenario briefly",
  "relevantClauses": [{{"text": "", "page": "", "section": ""}}],
  "conditions": ["condition or requirement that may apply"],
  "limits": ["any limits or caps that may apply"],
  "attentionPoints": ["things the user should be cautious about"],
  "explanation": "a clear, cautious, plain-language explanation of how the policy may apply to this scenario"
}}

POLICY EXCERPTS:
{context}

USER SCENARIO:
{scenario}
"""


class WhatIfState(TypedDict):
    document_id: str
    scenario: str
    retrieved: list[dict]
    result: dict | None
    provider_used: str | None
    fallback_used: bool
    error: str | None


def _retrieve(state: WhatIfState) -> WhatIfState:
    state["retrieved"] = rag.query_document(state["document_id"], state["scenario"], top_k=5)
    return state


def _simulate(state: WhatIfState) -> WhatIfState:
    if not state["retrieved"]:
        state["result"] = {
            "scenario": state["scenario"],
            "relevantClauses": [],
            "conditions": [],
            "limits": [],
            "attentionPoints": [],
            "explanation": "I couldn't find relevant policy clauses to analyze this scenario.",
        }
        return state

    context = "\n\n".join(
        f"[Page {c['page']}, Section: {c['section']}]\n{c['text']}" for c in state["retrieved"]
    )
    prompt = WHATIF_PROMPT_TEMPLATE.format(context=context, scenario=state["scenario"])

    try:
        result = llm.generate(prompt)
        state["provider_used"] = result.provider_used
        state["fallback_used"] = result.fallback_used
    except llm.LLMUnavailableError as e:
        state["error"] = str(e)
        state["result"] = {
            "scenario": state["scenario"],
            "relevantClauses": [],
            "conditions": [],
            "limits": [],
            "attentionPoints": [],
            "explanation": "The AI assistant is currently unavailable. Please try again shortly.",
        }
        return state

    try:
        parsed = llm.extract_json(result.text)
    except ValueError:
        parsed = {
            "scenario": state["scenario"],
            "relevantClauses": [{"text": c["text"], "page": c["page"], "section": c["section"]} for c in state["retrieved"]],
            "conditions": [],
            "limits": [],
            "attentionPoints": [],
            "explanation": result.text.strip(),
        }

    parsed.setdefault("scenario", state["scenario"])
    for field in ("relevantClauses", "conditions", "limits", "attentionPoints"):
        if field not in parsed or not isinstance(parsed[field], list):
            parsed[field] = []
    parsed.setdefault("explanation", "")

    state["result"] = parsed
    return state


def _build_graph():
    graph = StateGraph(WhatIfState)
    graph.add_node("retrieve", _retrieve)
    graph.add_node("simulate", _simulate)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "simulate")
    graph.add_edge("simulate", END)
    return graph.compile()


_GRAPH = _build_graph()


def run_what_if(document_id: str, scenario: str) -> dict:
    initial: WhatIfState = {
        "document_id": document_id,
        "scenario": scenario,
        "retrieved": [],
        "result": None,
        "provider_used": None,
        "fallback_used": False,
        "error": None,
    }
    final_state = _GRAPH.invoke(initial)

    return {
        "result": final_state["result"],
        "provider_used": final_state.get("provider_used"),
        "fallback_used": final_state.get("fallback_used", False),
        "error": final_state.get("error"),
    }

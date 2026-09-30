"""
LangGraph policy chatbot, grounded in RAG retrieval.

USER QUESTION -> retrieve chunks -> privacy check (already sanitized at
index time) -> Gemini -> fallback Grok -> answer + source page/section.

Never invents policy details; only answers from retrieved context.
"""
from typing import TypedDict
from langgraph.graph import StateGraph, END

from app import llm, rag

CHAT_PROMPT_TEMPLATE = """You are "Ask Your Policy", an assistant that answers questions about a
specific insurance policy using ONLY the retrieved policy excerpts below (already PII-redacted).

Rules:
- Only use information present in the excerpts.
- If the excerpts do not contain the answer, respond EXACTLY with:
  "I couldn't find this information in the uploaded policy."
- Be concise and clear. Do not guess or add outside knowledge.
- Do not mention that text was redacted or sanitized.

POLICY EXCERPTS:
{context}

USER QUESTION:
{question}

Answer:"""

NOT_FOUND_MSG = "I couldn't find this information in the uploaded policy."


class ChatState(TypedDict):
    document_id: str
    question: str
    retrieved: list[dict]
    answer: str | None
    provider_used: str | None
    fallback_used: bool
    error: str | None


def _retrieve(state: ChatState) -> ChatState:
    state["retrieved"] = rag.query_document(state["document_id"], state["question"], top_k=4)
    return state


def _generate_answer(state: ChatState) -> ChatState:
    if not state["retrieved"]:
        state["answer"] = NOT_FOUND_MSG
        return state

    context = "\n\n".join(
        f"[Page {c['page']}, Section: {c['section']}]\n{c['text']}" for c in state["retrieved"]
    )
    prompt = CHAT_PROMPT_TEMPLATE.format(context=context, question=state["question"])

    try:
        result = llm.generate(prompt)
        state["answer"] = result.text.strip()
        state["provider_used"] = result.provider_used
        state["fallback_used"] = result.fallback_used
    except llm.LLMUnavailableError as e:
        state["error"] = str(e)
        state["answer"] = "The AI assistant is currently unavailable. Please try again shortly."
    return state


def _build_graph():
    graph = StateGraph(ChatState)
    graph.add_node("retrieve", _retrieve)
    graph.add_node("generate_answer", _generate_answer)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate_answer")
    graph.add_edge("generate_answer", END)
    return graph.compile()


_GRAPH = _build_graph()


def ask_policy(document_id: str, question: str) -> dict:
    initial: ChatState = {
        "document_id": document_id,
        "question": question,
        "retrieved": [],
        "answer": None,
        "provider_used": None,
        "fallback_used": False,
        "error": None,
    }
    final_state = _GRAPH.invoke(initial)

    answer_is_valid = final_state["answer"] != NOT_FOUND_MSG and not final_state.get("error")
    sources = [
        {"page": c["page"], "section": c["section"]}
        for c in final_state["retrieved"]
    ] if answer_is_valid else []

    return {
        "answer": final_state["answer"],
        "sources": sources,
        "provider_used": final_state.get("provider_used"),
        "fallback_used": final_state.get("fallback_used", False),
        "error": final_state.get("error"),
    }

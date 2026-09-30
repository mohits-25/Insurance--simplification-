"""
PolicyLens AI — FastAPI backend entrypoint.

Pipeline: upload -> extraction (PyMuPDF/OCR) -> Privacy Gate (redaction) ->
section/clause extraction -> LangGraph policy analysis -> RAG indexing ->
dashboard/chat/what-if endpoints.
"""
import os
import uuid
import logging

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import ingestion, privacy, sections, rag, storage, llm
from app.analysis_graph import run_policy_analysis
from app.chatbot_graph import ask_policy
from app.whatif_graph import run_what_if
from app.readability import flesch_reading_ease

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("policylens")

app = FastAPI(title="PolicyLens AI", description="Privacy-aware AI for understanding insurance policies.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        "grok_configured": bool(os.getenv("GROK_API_KEY")),
    }


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    allowed_ext = ("pdf", "png", "jpg", "jpeg", "bmp", "tiff")
    ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}. Please upload a PDF or image.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 20MB for this MVP).")

    # --- STEP 1: Document ingestion (PyMuPDF / OCR) ---
    try:
        ingest_result = ingestion.extract_document(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail=f"Failed to process document: {e}")

    # --- STEP 2: Privacy Gate (PII detection & redaction) — raw text never leaves this scope ---
    redaction = privacy.redact_pii(ingest_result.full_text)
    readability_before = flesch_reading_ease(ingest_result.full_text)

    # --- STEP 3: Section/clause extraction from SANITIZED text only ---
    clauses = sections.extract_clauses(redaction.sanitized_text)
    if not clauses:
        raise HTTPException(status_code=422, detail="Could not detect any policy sections/clauses in this document.")

    document_id = str(uuid.uuid4())

    # --- STEP 4: RAG indexing (sanitized clauses only) ---
    try:
        chunks_indexed = rag.index_document(document_id, clauses)
    except Exception as e:
        logger.exception("RAG indexing failed")
        chunks_indexed = 0

    storage.save(document_id, {
        "document_id": document_id,
        "filename": file.filename,
        "document_type": ingest_result.document_type,
        "ocr_used": ingest_result.ocr_used,
        "page_count": ingest_result.page_count,
        "pii_detected": redaction.pii_detected,
        "fields_masked": redaction.fields_masked,
        "sanitized_text": redaction.sanitized_text,
        "clauses": [c.to_dict() for c in clauses],
        "chunks_indexed": chunks_indexed,
        "readability_before": readability_before,
        "analysis": None,
        "analysis_status": "pending",
        "warnings": ingest_result.warnings,
    })

    return {
        "documentId": document_id,
        "filename": file.filename,
        "documentType": ingest_result.document_type,
        "ocrUsed": ingest_result.ocr_used,
        "pageCount": ingest_result.page_count,
        "privacy": {
            "piiDetected": redaction.pii_detected,
            "fieldsMasked": redaction.fields_masked,
            "llmReceives": "SANITIZED TEXT ONLY",
        },
        "warnings": ingest_result.warnings,
    }


@app.post("/api/analyze/{document_id}")
def analyze_document(document_id: str):
    doc = storage.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found. Please upload again.")

    analysis_output = run_policy_analysis(doc["sanitized_text"])

    if not analysis_output["success"]:
        storage.update(document_id, analysis_status="failed")
        raise HTTPException(status_code=502, detail=analysis_output.get("error") or "Policy analysis failed.")

    result = analysis_output["result"]
    readability_after = flesch_reading_ease(result.get("summary", ""))

    storage.update(
        document_id,
        analysis=result,
        analysis_status="complete",
        analysis_provider=analysis_output.get("provider_used"),
        analysis_fallback_used=analysis_output.get("fallback_used"),
        readability_after=readability_after,
    )

    return {
        "documentId": document_id,
        "analysis": result,
        "providerUsed": analysis_output.get("provider_used"),
        "fallbackUsed": analysis_output.get("fallback_used", False),
        "readability": {
            "before": doc["readability_before"],
            "after": readability_after,
        },
    }


@app.get("/api/dashboard/{document_id}")
def get_dashboard(document_id: str):
    doc = storage.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found. Please upload again.")

    analysis = doc.get("analysis")
    if not analysis:
        return {
            "documentId": document_id,
            "status": doc.get("analysis_status", "pending"),
            "message": "Analysis not yet complete. Call /api/analyze first.",
        }

    coverage_count = len(analysis.get("coverage", []))
    exclusions_count = len(analysis.get("exclusions", []))
    attention_count = len(analysis.get("attentionPoints", []))

    complexity_score = min(100, (exclusions_count * 8 + attention_count * 10 + coverage_count * 3))

    five_things = []
    for item in analysis.get("attentionPoints", [])[:3]:
        five_things.append(item.get("title", ""))
    for item in analysis.get("exclusions", [])[:2]:
        five_things.append(item.get("title", ""))
    five_things = [t for t in five_things if t][:5]

    return {
        "documentId": document_id,
        "filename": doc["filename"],
        "documentType": doc["document_type"],
        "ocrUsed": doc["ocr_used"],
        "pageCount": doc["page_count"],
        "privacy": {
            "piiDetected": doc["pii_detected"],
            "fieldsMasked": doc["fields_masked"],
            "llmReceives": "SANITIZED TEXT ONLY",
            "originalDocument": "LOCAL ONLY",
        },
        "metrics": {
            "policyComplexity": complexity_score,
            "readabilityBefore": doc.get("readability_before", 0),
            "readabilityAfter": doc.get("readability_after", 0),
            "coverageClauses": coverage_count,
            "exclusions": exclusions_count,
            "attentionPoints": attention_count,
        },
        "fiveThingsToKnow": five_things,
        "analysis": analysis,
    }


class ChatRequest(BaseModel):
    question: str


@app.post("/api/chat/{document_id}")
def chat(document_id: str, req: ChatRequest):
    doc = storage.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found. Please upload again.")
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = ask_policy(document_id, req.question.strip())
    except Exception as e:
        logger.exception("Chat failed")
        raise HTTPException(status_code=502, detail=f"Chat assistant failed: {e}")

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "providerUsed": result.get("provider_used"),
        "fallbackUsed": result.get("fallback_used", False),
    }


class WhatIfRequest(BaseModel):
    scenario: str


@app.post("/api/whatif/{document_id}")
def what_if(document_id: str, req: WhatIfRequest):
    doc = storage.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found. Please upload again.")
    if not req.scenario or not req.scenario.strip():
        raise HTTPException(status_code=400, detail="Scenario cannot be empty.")

    try:
        output = run_what_if(document_id, req.scenario.strip())
    except Exception as e:
        logger.exception("What-if simulation failed")
        raise HTTPException(status_code=502, detail=f"What-if simulation failed: {e}")

    return {
        "result": output["result"],
        "providerUsed": output.get("provider_used"),
        "fallbackUsed": output.get("fallback_used", False),
    }

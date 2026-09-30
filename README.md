# PolicyLens AI

**Privacy-aware AI for understanding insurance policies.**

PolicyLens AI turns a dense, jargon-heavy insurance policy PDF into a plain-language
dashboard — coverage, exclusions, waiting periods, and risk points — while making sure
your personal data (name, phone, email, Aadhaar, PAN, policy/account numbers) is
redacted **locally** before anything is sent to an external AI model.

---

## Table of Contents

- [What it does](#what-it-does)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup & running](#setup--running)
- [Environment variables](#environment-variables)
- [Testing the pipeline](#testing-the-pipeline)
- [API reference](#api-reference)
- [How the Privacy Gate works](#how-the-privacy-gate-works)
- [How the LLM fallback works](#how-the-llm-fallback-works)
- [How the KPS rating is calculated](#how-the-kps-rating-is-calculated)
- [Limitations](#limitations)

---

## What it does

1. **Upload** a health/insurance policy as a PDF or image.
2. The system detects whether it's a **text PDF** (extracted with PyMuPDF) or a
   **scanned PDF/image** (falls back to Tesseract OCR), page by page.
3. Before any AI model sees the text, a **Privacy Gate** scans it locally and
   redacts personally identifiable information (names, phone numbers, emails,
   addresses, Aadhaar, PAN, policy numbers, customer IDs, account numbers).
   Only the **sanitized** text ever leaves this boundary.
4. The sanitized text is split into policy **sections/clauses** (Coverage,
   Exclusions, Waiting Period, Deductible, Hospitalization, Claim Procedure,
   Coverage Limits, Renewal, Conditions, Important Definitions).
5. A **LangGraph** workflow sends the sanitized text to **Gemini** (falling back
   to **Groq** if Gemini fails or is rate-limited) and gets back structured JSON:
   summary, coverage, exclusions, waiting periods, limits, deductibles,
   attention points, important clauses.
6. The same sanitized clauses are chunked and embedded into a local **Chroma**
   vector store for retrieval-augmented generation (RAG).
7. A **dashboard** presents everything: metrics, "5 things you must know",
   readability score, and a live Privacy Guard status card.
8. **Ask Your Policy** — a chatbot grounded only in the retrieved policy
   chunks, with source page/section citations. It refuses to answer if the
   information isn't in the policy.
9. **What-If Policy Simulator** — describe a hypothetical ("What if I'm
   hospitalized for 5 days?") and get a cautious, clause-grounded answer with
   conditions, limits, and attention points — never a definitive "will be
   accepted/rejected" claim.
10. **KPS Rating** — a "Key Policy Understanding / Policy Simplification"
    score (0–100%) computed directly from the real analysis JSON, measuring
    how effectively the extracted coverage, exclusions, conditions, sources,
    plain-language explanations, and attention points actually cover and
    explain the uploaded policy. Recalculated fresh on every analysis — never
    a fixed or fabricated number.

---

## Architecture

```
INSURANCE PDF / IMAGE
        |
DOCUMENT DETECTION
        |
  +-----------+-----------+
  | Text PDF              | Scanned PDF
  | PyMuPDF                | Tesseract OCR
  +-----------+-----------+
              |
           RAW TEXT
              |
        PRIVACY GATE  (PII detection -> redaction, local only)
              |
           SAFE TEXT
              |
   SECTION / CLAUSE EXTRACTION
        |             |
 POLICY ANALYSIS   CHUNKING + EMBEDDING
        |             |
   (LangGraph)     (Chroma vector store)
        |             |
        +------+------+
               |
        POLICY KNOWLEDGE
               |
   +-----------+-----------+
   |           |           |
Chatbot     What-If     Dashboard
 (RAG)      Simulator
```

LLM routing: **Gemini primary → Groq fallback**, used identically for policy
analysis, the chatbot, and the what-if simulator.

> Note on naming: the original spec referred to a "Grok" fallback. The actual
> API key in use is a **Groq Cloud** key (`api.groq.com`, OpenAI-compatible),
> which is a different provider from xAI's Grok. Environment variable names
> (`GROK_API_KEY`, `GROK_MODEL`, `FALLBACK_LLM=grok`) were kept as originally
> specified, but they route to Groq Cloud under the hood.

---

## Project structure

```
Insurance--simplification-/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI app & all HTTP endpoints
│   │   ├── ingestion.py         PyMuPDF extraction + Tesseract OCR fallback
│   │   ├── privacy.py           Privacy Gate: regex-based PII detection/redaction
│   │   ├── sections.py          Section/clause extraction from sanitized text
│   │   ├── llm.py               Gemini/Groq provider abstraction + fallback logic
│   │   ├── analysis_graph.py    LangGraph: policy analysis workflow
│   │   ├── chatbot_graph.py     LangGraph: "Ask Your Policy" chatbot workflow
│   │   ├── whatif_graph.py      LangGraph: What-If simulator workflow
│   │   ├── rag.py               Chroma vector store indexing & retrieval
│   │   ├── readability.py       Flesch Reading Ease implementation
│   │   ├── kps.py               KPS (Key Policy Understanding) rating calculation
│   │   └── storage.py           In-memory document store (no DB for MVP)
│   ├── create_sample_policy.py  Generates a synthetic demo policy PDF
│   ├── sample_policy.pdf        Pre-generated demo policy (fake data)
│   ├── requirements.txt
│   ├── .env.example
│   └── .env                     Your real API keys (gitignored)
├── frontend/
│   ├── src/
│   │   ├── App.jsx              Top-level app state (upload -> dashboard)
│   │   ├── api.js                Fetch wrappers for the backend API
│   │   ├── main.jsx
│   │   ├── index.css             Tailwind entrypoint
│   │   └── components/
│   │       ├── UploadScreen.jsx    Upload UI + processing status
│   │       ├── Dashboard.jsx       Main dashboard (6 tabs)
│   │       ├── PrivacyGuardCard.jsx
│   │       ├── ClauseList.jsx
│   │       ├── ChatPanel.jsx       Ask Your Policy chatbot UI
│   │       ├── WhatIfPanel.jsx     What-If simulator UI
│   │       └── KPSCard.jsx         KPS Rating card (score, bar, breakdown)
│   ├── package.json
│   └── vite.config.js
└── .gitignore
```

---

## Prerequisites

- **Python 3.11+** (tested on 3.13)
- **Node.js 18+** (tested on Node 26)
- **Tesseract OCR** installed locally
  - macOS: `brew install tesseract`
  - Confirm path with `which tesseract` (defaults to `/opt/homebrew/bin/tesseract` on Apple Silicon Macs)
- API keys:
  - **Gemini**: [Google AI Studio](https://aistudio.google.com/apikey)
  - **Groq**: [Groq Console](https://console.groq.com/keys)

---

## Setup & running

### 1. Backend

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt
```

Create your `.env` (copy from `.env.example` and fill in real keys):

```bash
cp .env.example .env
```

```
GEMINI_API_KEY=your_gemini_key_here
GROK_API_KEY=your_groq_key_here
GEMINI_MODEL=gemini-3.8-flash
GROK_MODEL=openai/gpt-oss-120b
PRIMARY_LLM=gemini
FALLBACK_LLM=grok
TESSERACT_PATH=/opt/homebrew/bin/tesseract
```

Run the backend:

```bash
./.venv/bin/uvicorn app.main:app --reload --port 8000
```

Verify it's up:

```bash
curl http://localhost:8000/api/health
# {"status":"ok","gemini_configured":true,"grok_configured":true}
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite will print the local URL (typically `http://localhost:5173`, or the next
free port if that one's taken). Open it in a browser.

> If your frontend runs on a port other than 5173/5174, add it to the
> `allow_origins` list in `backend/app/main.py` (CORS middleware).

---

## Environment variables

| Variable          | Description                                                        | Example                     |
|-------------------|----------------------------------------------------------------------|------------------------------|
| `GEMINI_API_KEY`  | Google AI Studio API key                                            | `AQ.Ab8...`                  |
| `GROK_API_KEY`    | Groq Cloud API key                                                  | `gsk_...`                    |
| `GEMINI_MODEL`    | Gemini model name                                                    | `gemini-3.8-flash`           |
| `GROK_MODEL`      | Groq model name                                                     | `openai/gpt-oss-120b`        |
| `PRIMARY_LLM`     | Which provider to try first (`gemini` or `grok`)                     | `gemini`                     |
| `FALLBACK_LLM`    | Which provider to fall back to                                       | `grok`                       |
| `TESSERACT_PATH`  | Path to the Tesseract binary                                          | `/opt/homebrew/bin/tesseract`|

`.env` is gitignored — never commit real keys. `.env.example` documents the
shape without secrets.

**Model names drift over time** — providers deprecate old models. If you hit a
404/"model not found" error, list currently available models and update
`GEMINI_MODEL` / `GROK_MODEL` in `.env`:

```bash
# Gemini
./.venv/bin/python -c "
import google.generativeai as genai, os
from dotenv import load_dotenv; load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
"

# Groq
curl -s https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROK_API_KEY"
```

---

## Testing the pipeline

### Using the built-in sample policy (text PDF)

A synthetic demo policy (fake data only) is already generated at
`backend/sample_policy.pdf`. Regenerate it any time with:

```bash
cd backend
./.venv/bin/python create_sample_policy.py
```

Upload it through the UI, or test the API directly:

```bash
curl -X POST http://localhost:8000/api/upload -F "file=@sample_policy.pdf"
# -> { "documentId": "...", "documentType": "Text PDF", "ocrUsed": false, ... }

curl -X POST http://localhost:8000/api/analyze/<documentId>
curl http://localhost:8000/api/dashboard/<documentId>
curl -X POST http://localhost:8000/api/chat/<documentId> \
  -H "Content-Type: application/json" -d '{"question":"Is hospitalization covered?"}'
curl -X POST http://localhost:8000/api/whatif/<documentId> \
  -H "Content-Type: application/json" -d '{"scenario":"What if I am hospitalized for 5 days?"}'
```

### Testing a scanned PDF / image

Any page with less than ~20 characters of extractable text automatically
triggers the OCR fallback (page is rendered to an image and run through
Tesseract). To test this path:

1. Print `sample_policy.pdf` and re-scan it (or photograph a printed page), **or**
2. Take a screenshot of a policy page and upload it as a `.png`/`.jpg`.

The upload response will show `"documentType": "Scanned PDF"` and
`"ocrUsed": true`, and the UI displays **OCR: Used**.

---

## API reference

| Method | Endpoint                     | Description                                             |
|--------|-------------------------------|-----------------------------------------------------------|
| GET    | `/api/health`                 | Backend + LLM key configuration status                    |
| POST   | `/api/upload`                 | Upload PDF/image → extraction, redaction, RAG indexing     |
| POST   | `/api/analyze/{documentId}`   | Run LangGraph policy analysis (Gemini → Groq fallback)      |
| GET    | `/api/dashboard/{documentId}` | Get dashboard metrics + full structured analysis            |
| POST   | `/api/chat/{documentId}`      | Ask a grounded question about the policy                    |
| POST   | `/api/whatif/{documentId}`    | Run a what-if scenario against the policy                   |

---

## How the Privacy Gate works

`backend/app/privacy.py` runs entirely locally, before any network call to an
LLM. It uses deterministic regex + label-based matching (no data leaves the
process for this step):

| Detected                | Replaced with              |
|--------------------------|------------------------------|
| Name (labeled)           | `[PERSON_REDACTED]`         |
| Address (labeled)        | `[ADDRESS_REDACTED]`        |
| Email                    | `[EMAIL_REDACTED]`          |
| Phone (Indian mobile)     | `[PHONE_REDACTED]`          |
| Aadhaar-like number       | `[AADHAAR_REDACTED]`        |
| PAN-like code             | `[PAN_REDACTED]`             |
| Policy number (labeled)   | `[POLICY_ID_REDACTED]`      |
| Customer/Member ID        | `[CUSTOMER_ID_REDACTED]`    |
| Account number (labeled)  | `[ACCOUNT_REDACTED]`        |

Only the resulting **sanitized text** is used for section extraction, RAG
embedding, and every LLM call. The raw text and file never leave the backend
process and are never persisted to disk.

The upload response and dashboard both expose a `privacy` block:

```json
{
  "piiDetected": true,
  "fieldsMasked": 9,
  "llmReceives": "SANITIZED TEXT ONLY",
  "originalDocument": "LOCAL ONLY"
}
```

---

## How the LLM fallback works

`backend/app/llm.py` exposes a single `generate(prompt)` function used by all
three LangGraph workflows (analysis, chat, what-if):

1. Try `PRIMARY_LLM` (Gemini).
2. If it raises any exception (missing key, rate limit, network error, model
   not found, etc.), try `FALLBACK_LLM` (Groq) automatically.
3. If both fail, raise a single combined error with both failure reasons —
   surfaced to the frontend as a friendly message, never a crash.
4. Every response includes `providerUsed` and `fallbackUsed` so the UI can
   show: *"Gemini unavailable — response generated using Grok fallback."*

Gemini's free tier is limited (5 requests/minute on `gemini-3.8-flash` at time
of writing), so the Groq fallback triggers naturally under normal demo usage
— this is expected behavior, not a bug.

## How the KPS rating is calculated

`backend/app/kps.py` exports a single reusable function:

```python
calculateKPS(policy_analysis: dict, readability_before: float, readability_after: float) -> dict
```

It computes the **KPS (Key Policy Understanding / Policy Simplification)**
rating — a 0–100% score measuring how effectively PolicyLens converted the
*actual* uploaded policy into understandable, actionable information. It is
**derived entirely from the real analysis JSON** for that document (the same
`coverage` / `exclusions` / `waitingPeriods` / `claimConditions` / `limits` /
`deductibles` / `attentionPoints` / `importantClauses` arrays shown elsewhere
in the dashboard) plus the Flesch readability scores already computed for
that document. It is **never a random or fixed value** — an empty or weak
analysis scores low; a rich, well-sourced, well-explained analysis scores
high, deterministically, every time.

Six weighted components, each normalized to 0–100:

| Component                     | Weight | What it measures |
|--------------------------------|--------|-------------------|
| Coverage Understanding         | 20%    | Fraction of extracted `coverage` items that have a real explanation (≥25 chars, not a placeholder) **and** a valid page/section reference, weighted by explanation quality. |
| Exclusion Understanding        | 20%    | Same measurement applied to `exclusions`. |
| Condition / Waiting Period     | 15%    | Same measurement applied to the combined `waitingPeriods` + `claimConditions` + `limits` + `deductibles`. |
| Source Traceability            | 15%    | Percentage of **every** extracted insight (all categories combined) that carries a non-empty page **and** section reference back to the source document. |
| Plain-Language Simplification  | 15%    | Blend of (a) average "explanation quality" across all items — penalizing explanations that are too thin *or* just long copy-pasted clauses, peaking around ~220 characters of concise prose — and (b) the Flesch Reading Ease lift between the raw policy text and the AI-generated summary. |
| Attention Point Detection      | 15%    | Combination of how well `attentionPoints` are explained/sourced, and what fraction of risk-bearing items (exclusions, waiting periods, conditions, limits, deductibles) were actually flagged with medium/high severity rather than left as neutral facts. |

```
KPS Score =
  CoverageUnderstanding   * 0.20 +
  ExclusionUnderstanding  * 0.20 +
  ConditionUnderstanding  * 0.15 +
  SourceTraceability      * 0.15 +
  PlainLanguage           * 0.15 +
  AttentionDetection      * 0.15
```

The result is exposed on both `POST /api/analyze/{documentId}` and
`GET /api/dashboard/{documentId}` as:

```json
{
  "overallScore": 84,
  "target": 80,
  "components": {
    "coverageUnderstanding": 88,
    "exclusionUnderstanding": 79,
    "conditionUnderstanding": 88,
    "sourceTraceability": 100,
    "plainLanguage": 54,
    "attentionDetection": 94
  },
  "label": "Strong understanding"
}
```

Descriptive labels (informational only — never implies the target was met
unless the calculated score actually reaches it):

| Score range | Label                  |
|-------------|--------------------------|
| 90–100      | Excellent understanding |
| 80–89       | Strong understanding    |
| 70–79       | Moderate understanding  |
| Below 70    | Needs improvement       |

The KPS card is shown prominently on the dashboard's Overview tab, with the
score, a progress bar, the 80% target line, the descriptive label, a
per-component breakdown, and an info tooltip explaining what KPS measures.
It recalculates automatically every time a new policy is uploaded and
analyzed — verified with an empty analysis (scores ~3%), a thin/unsourced
analysis (scores ~4%), and a rich well-sourced analysis (scores ~88%), all
computed from the same deterministic function.

---

---

## Limitations

- **In-memory storage only.** Restarting the backend clears all uploaded
  documents and their vector indices (by design — no database in this MVP).
- **No live API key test coverage in CI** — correctness of the Gemini/Groq
  calls was verified manually against the real APIs during development, not
  via an automated test suite.
- **Regex/label-based PII detection**, not NLP/NER-based. Names or addresses
  without a recognizable label (e.g. "Name:", "Address:") won't be redacted.
  Sufficient for structured policy documents, not a general-purpose PII
  scrubber.
- **Chroma runs in ephemeral (in-process) mode** — fine for a single demo
  session, not for concurrent multi-user production use.
- **Model names drift.** Gemini and Groq periodically deprecate models; if
  you see a 404, see [Environment variables](#environment-variables) for how
  to find current model names.
- Large documents are truncated to ~18,000 characters before analysis to keep
  prompt size manageable.

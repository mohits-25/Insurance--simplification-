"""
LLM provider abstraction: Gemini primary, Groq (Llama) fallback.
Never expose API keys to frontend. Only sanitized text is ever sent here.

Note: the fallback provider is Groq Cloud (api.groq.com), an OpenAI-compatible
LPU inference API — not to be confused with xAI's "Grok" model. Internal
variable/function names retain "grok" for naming consistency with env vars.
"""
import os
import json
import requests
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROK_API_KEY = os.getenv("GROK_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GROK_MODEL = os.getenv("GROK_MODEL", "openai/gpt-oss-120b")
PRIMARY_LLM = os.getenv("PRIMARY_LLM", "gemini")
FALLBACK_LLM = os.getenv("FALLBACK_LLM", "grok")

GROK_API_URL = "https://api.groq.com/openai/v1/chat/completions"  # Groq Cloud (OpenAI-compatible)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


class LLMResult:
    def __init__(self, text: str, provider_used: str, fallback_used: bool, error: str | None = None):
        self.text = text
        self.provider_used = provider_used
        self.fallback_used = fallback_used
        self.error = error


class LLMUnavailableError(Exception):
    pass


def _call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not configured")
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(prompt)
    if not response or not getattr(response, "text", None):
        raise RuntimeError("Gemini returned empty response")
    return response.text


def _call_grok(prompt: str) -> str:
    if not GROK_API_KEY:
        raise RuntimeError("GROK_API_KEY not configured")
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 8000,
    }
    resp = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


_PROVIDERS = {
    "gemini": _call_gemini,
    "grok": _call_grok,
}


def generate(prompt: str) -> LLMResult:
    """
    Try PRIMARY_LLM first, fall back to FALLBACK_LLM on any failure.
    Raises LLMUnavailableError if both fail.
    """
    primary_fn = _PROVIDERS.get(PRIMARY_LLM)
    fallback_fn = _PROVIDERS.get(FALLBACK_LLM)

    primary_error = None
    if primary_fn:
        try:
            text = primary_fn(prompt)
            return LLMResult(text=text, provider_used=PRIMARY_LLM, fallback_used=False)
        except Exception as e:
            primary_error = str(e)

    if fallback_fn:
        try:
            text = fallback_fn(prompt)
            return LLMResult(text=text, provider_used=FALLBACK_LLM, fallback_used=True, error=primary_error)
        except Exception as e:
            raise LLMUnavailableError(
                f"Both LLM providers failed. {PRIMARY_LLM} error: {primary_error}. {FALLBACK_LLM} error: {e}"
            )

    raise LLMUnavailableError(
        f"No LLM providers configured/available. {PRIMARY_LLM} error: {primary_error}"
    )


def extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from LLM output (handles markdown fences)."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError("Could not parse JSON from LLM response")

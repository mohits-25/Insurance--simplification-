"""
Privacy Gate: deterministic regex-based PII detection & redaction.
Raw text NEVER leaves this module boundary — only sanitized text
is passed onward to LangChain/embeddings/vector store/Gemini/Grok.
"""
import re

# Order matters: more specific/labeled patterns must run BEFORE generic
# numeric patterns (e.g. Account/Policy number) to avoid Aadhaar's 12-digit
# pattern greedily consuming other numeric identifiers first.
PII_PATTERNS = [
    ("EMAIL_REDACTED", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
    ("POLICY_ID_REDACTED", re.compile(r"\b(?:Policy\s*(?:No\.?|Number|ID)\s*[:\-]?\s*)([A-Za-z0-9\-\/]{5,20})\b", re.IGNORECASE)),
    ("CUSTOMER_ID_REDACTED", re.compile(r"\b(?:Customer\s*ID|Client\s*ID|Member\s*ID)\s*[:\-]?\s*([A-Za-z0-9\-\/]{4,20})\b", re.IGNORECASE)),
    ("ACCOUNT_REDACTED", re.compile(r"\b(?:Account\s*(?:No\.?|Number)|A\/c\s*No\.?)\s*[:\-]?\s*(\d{6,18})\b", re.IGNORECASE)),
    ("PAN_REDACTED", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")),
    ("AADHAAR_REDACTED", re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")),
    ("PHONE_REDACTED", re.compile(r"(?:\+91[-\s]?)?\b[6-9]\d{9}\b")),
    ("PINCODE_REDACTED", re.compile(r"\b\d{6}\b(?=\s*(?:India|IN)?\b)")),
]

# Name detection: label-based (deterministic, avoids NLP false positives).
# Anchored to a single line so it cannot bleed into the following field.
NAME_LABEL_PATTERN = re.compile(
    r"(?:Name|Policyholder|Insured|Nominee|Applicant)\s*[:\-]\s*([A-Z][a-zA-Z.]+(?:[ \t]+[A-Z][a-zA-Z.]+){0,3})(?=\s*(?:\r?\n|$))",
)

ADDRESS_LABEL_PATTERN = re.compile(
    r"(?:Address)\s*[:\-]\s*([^\n]+)"
)


class RedactionResult:
    def __init__(self):
        self.sanitized_text: str = ""
        self.pii_detected: bool = False
        self.fields_masked: int = 0
        self.detections: list[dict] = []  # [{type, original_len}]


def redact_pii(raw_text: str) -> RedactionResult:
    result = RedactionResult()
    text = raw_text
    count = 0

    # Label-based name redaction first (Name: John Smith -> Name: [PERSON_REDACTED])
    def _name_sub(m):
        nonlocal count
        count += 1
        result.detections.append({"type": "PERSON_REDACTED"})
        start, end = m.span(1)
        return m.group(0)[: start - m.start()] + "[PERSON_REDACTED]" + m.group(0)[end - m.start():]

    text = NAME_LABEL_PATTERN.sub(_name_sub, text)

    def _addr_sub(m):
        nonlocal count
        count += 1
        result.detections.append({"type": "ADDRESS_REDACTED"})
        start, end = m.span(1)
        return m.group(0)[: start - m.start()] + "[ADDRESS_REDACTED]" + m.group(0)[end - m.start():]

    text = ADDRESS_LABEL_PATTERN.sub(_addr_sub, text)

    for label, pattern in PII_PATTERNS:
        def _sub(m, label=label):
            nonlocal count
            count += 1
            result.detections.append({"type": label})
            if m.groups():
                # replace only the captured group (keep the label prefix e.g. "Policy No: ")
                start, end = m.span(1)
                return m.group(0)[: start - m.start()] + f"[{label}]" + m.group(0)[end - m.start():]
            return f"[{label}]"

        text = pattern.sub(_sub, text)

    result.sanitized_text = text
    result.fields_masked = count
    result.pii_detected = count > 0
    return result

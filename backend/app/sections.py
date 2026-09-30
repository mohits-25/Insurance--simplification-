"""
Section/clause extraction from sanitized text.
Detects known insurance section headers and groups following text as clauses,
preserving page number + section name + sanitized clause text.
Does not invent sections that aren't present.
"""
import re

SECTION_KEYWORDS = {
    "Coverage": [r"\bcoverage\b", r"\bwhat is covered\b", r"\bbenefits\b"],
    "Exclusions": [r"\bexclusions?\b", r"\bwhat is not covered\b", r"\bnot covered\b"],
    "Waiting Period": [r"\bwaiting period\b"],
    "Deductible": [r"\bdeductible\b", r"\bco-?pay(?:ment)?\b"],
    "Hospitalization": [r"\bhospitali[sz]ation\b", r"\bin-?patient\b"],
    "Claim Procedure": [r"\bclaim procedure\b", r"\bhow to claim\b", r"\bclaim process\b", r"\bfiling a claim\b"],
    "Coverage Limits": [r"\bcoverage limits?\b", r"\bsum insured\b", r"\blimit of liability\b", r"\bmaximum limit\b"],
    "Renewal": [r"\brenewal\b", r"\brenewing\b"],
    "Conditions": [r"\bconditions?\b", r"\bterms and conditions\b"],
    "Important Definitions": [r"\bdefinitions?\b", r"\bmeaning of terms\b"],
}

_COMPILED = {
    name: [re.compile(p, re.IGNORECASE) for p in patterns]
    for name, patterns in SECTION_KEYWORDS.items()
}

HEADER_LINE = re.compile(r"^\s{0,4}([A-Z][A-Za-z /,&\-]{2,60})\s*$")


class Clause:
    def __init__(self, section: str, page: int, text: str):
        self.section = section
        self.page = page
        self.text = text

    def to_dict(self):
        return {"section": self.section, "page": self.page, "text": self.text}


def _match_section(line: str) -> str | None:
    for name, patterns in _COMPILED.items():
        for p in patterns:
            if p.search(line):
                return name
    return None


def extract_clauses(sanitized_full_text: str) -> list[Clause]:
    """
    Walk page-tagged text, split into lines, detect section headers,
    and accumulate clause text under the most recent detected section.
    """
    clauses: list[Clause] = []
    current_page = 1
    current_section = "General"
    buffer: list[str] = []

    def flush():
        if buffer:
            text = "\n".join(buffer).strip()
            if len(text) > 15:
                clauses.append(Clause(current_section, current_page, text))
            buffer.clear()

    page_pattern = re.compile(r"^--- PAGE (\d+) ---$")

    for raw_line in sanitized_full_text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        page_match = page_pattern.match(line)
        if page_match:
            flush()
            current_page = int(page_match.group(1))
            continue

        section_hit = _match_section(line)
        # Treat short lines that match a section keyword as headers (new section starts)
        if section_hit and len(line) < 80:
            flush()
            current_section = section_hit
            continue

        buffer.append(line)

    flush()
    return clauses


def group_by_section(clauses: list[Clause]) -> dict[str, list[Clause]]:
    grouped: dict[str, list[Clause]] = {}
    for c in clauses:
        grouped.setdefault(c.section, []).append(c)
    return grouped

"""
Readability metric: Flesch Reading Ease, implemented directly (no external
textstat dependency — avoids pkg_resources/setuptools compatibility issues
on Python 3.13). Formula is the standard, well-known Flesch formula —
transparent and not fabricated.

Flesch Reading Ease = 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
"""
import re

VOWEL_GROUPS = re.compile(r"[aeiouy]+", re.IGNORECASE)
SENTENCE_SPLIT = re.compile(r"[.!?]+")
WORD_SPLIT = re.compile(r"[A-Za-z']+")


def _count_syllables(word: str) -> int:
    word = word.lower().strip()
    if not word:
        return 0
    groups = VOWEL_GROUPS.findall(word)
    count = len(groups)
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def flesch_reading_ease(text: str) -> float:
    if not text or len(text.strip()) < 10:
        return 0.0

    sentences = [s for s in SENTENCE_SPLIT.split(text) if s.strip()]
    words = WORD_SPLIT.findall(text)

    num_sentences = max(1, len(sentences))
    num_words = max(1, len(words))
    num_syllables = sum(_count_syllables(w) for w in words)

    score = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (num_syllables / num_words)
    return max(0.0, min(100.0, round(score, 1)))

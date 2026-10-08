"""
analysis/metrics/readability.py
───────────────────────────────
Standard readability metrics via textstat:
- Flesch Reading Ease (FRE)
- Flesch-Kincaid Grade Level (FKGL)
- SMOG Index
- Gunning Fog Index
- Coleman-Liau Index
"""

import re
from typing import Dict, List

import textstat


def tokenize_words(text: str) -> List[str]:
    """Tokenize text into alphanumeric words (shared helper for other metric modules)."""
    return re.findall(r"\b[A-Za-z0-9\'-]+\b", text)


def compute_readability_metrics(text: str) -> Dict[str, float]:
    """Readability scores of `text` (textstat), plus word / sentence / syllable counts."""
    cleaned = text.strip()
    if not tokenize_words(cleaned):
        return {"flesch_reading_ease": 0.0, "flesch_kincaid_grade_level": 0.0, "smog_index": 0.0,
                "gunning_fog": 0.0, "coleman_liau": 0.0, "num_words": 0, "num_sentences": 0, "num_syllables": 0}
    return {
        "flesch_reading_ease": round(textstat.flesch_reading_ease(cleaned), 2),
        "flesch_kincaid_grade_level": round(textstat.flesch_kincaid_grade(cleaned), 2),
        "smog_index": round(textstat.smog_index(cleaned), 2),
        "gunning_fog": round(textstat.gunning_fog(cleaned), 2),
        "coleman_liau": round(textstat.coleman_liau_index(cleaned), 2),
        "num_words": textstat.lexicon_count(cleaned),
        "num_sentences": textstat.sentence_count(cleaned),
        "num_syllables": textstat.syllable_count(cleaned),
    }

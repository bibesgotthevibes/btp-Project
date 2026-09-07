"""
analysis/metrics/readability.py
───────────────────────────────
Pure-Python implementations of standard readability metrics:
- Flesch Reading Ease (FRE)
- Flesch-Kincaid Grade Level (FKGL)
- SMOG Index
- Gunning Fog Index
- Coleman-Liau Index
"""

import re
import math
from typing import Dict, Any, List

def count_syllables_word(word: str) -> int:
    """Estimate syllable count in an English word."""
    w = word.lower().strip()
    if not w:
        return 0
    # Strip non-alpha
    w = re.sub(r"[^a-z]", "", w)
    if not w:
        return 0
    if len(w) <= 3:
        return 1

    # Basic vowel group count
    vowels = "aeiouy"
    count = 0
    prev_is_vowel = False

    for char in w:
        is_vowel = char in vowels
        if is_vowel and not prev_is_vowel:
            count += 1
        prev_is_vowel = is_vowel

    # Silent 'e' adjustments
    if w.endswith("e") and not w.endswith("le") and len(w) > 2:
        if count > 1:
            count -= 1
    if w.endswith("ed") and not w.endswith("ted") and not w.endswith("ded"):
        if count > 1:
            count -= 1

    return max(1, count)

def tokenize_words(text: str) -> List[str]:
    """Tokenize text into alphanumeric words."""
    return re.findall(r"\b[A-Za-z0-9\'-]+\b", text)

def tokenize_sentences(text: str) -> List[str]:
    """Tokenize text into sentences."""
    # Split on sentence terminals
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sents if s.strip()]

def compute_readability_metrics(text: str) -> Dict[str, float]:
    """
    Compute core readability scores:
    - flesch_reading_ease
    - flesch_kincaid_grade_level
    - smog_index
    - gunning_fog
    - coleman_liau
    """
    cleaned = text.strip()
    if not cleaned:
        return {
            "flesch_reading_ease": 0.0,
            "flesch_kincaid_grade_level": 0.0,
            "smog_index": 0.0,
            "gunning_fog": 0.0,
            "coleman_liau": 0.0,
            "num_words": 0,
            "num_sentences": 0,
            "num_syllables": 0,
        }

    words = tokenize_words(cleaned)
    sentences = tokenize_sentences(cleaned)

    n_words = len(words)
    n_sentences = max(1, len(sentences))

    if n_words == 0:
        return {
            "flesch_reading_ease": 0.0,
            "flesch_kincaid_grade_level": 0.0,
            "smog_index": 0.0,
            "gunning_fog": 0.0,
            "coleman_liau": 0.0,
            "num_words": 0,
            "num_sentences": 0,
            "num_syllables": 0,
        }

    syllable_counts = [count_syllables_word(w) for w in words]
    total_syllables = sum(syllable_counts)
    polysyllables = sum(1 for s in syllable_counts if s >= 3)
    complex_words = sum(1 for s in syllable_counts if s >= 3)

    words_per_sentence = n_words / n_sentences
    syllables_per_word = total_syllables / n_words

    # 1. Flesch Reading Ease
    # 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
    fre = 206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
    fre = max(0.0, min(100.0, fre))

    # 2. Flesch-Kincaid Grade Level
    # 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
    fkgl = (0.39 * words_per_sentence) + (11.8 * syllables_per_word) - 15.59
    fkgl = max(0.0, fkgl)

    # 3. SMOG Index
    # 1.0430 * sqrt(30 * polysyllables / sentences) + 3.1291
    if n_sentences >= 3:
        smog = 1.0430 * math.sqrt(30.0 * (polysyllables / n_sentences)) + 3.1291
    else:
        # Adjusted for short passages
        smog = 1.0430 * math.sqrt(polysyllables * (30.0 / max(1, n_sentences))) + 3.1291
    smog = max(0.0, smog)

    # 4. Gunning Fog Index
    # 0.4 * ((words/sentences) + 100 * (complex_words/words))
    gunning_fog = 0.4 * (words_per_sentence + 100.0 * (complex_words / n_words))
    gunning_fog = max(0.0, gunning_fog)

    # 5. Coleman-Liau Index
    # 0.0588 * L - 0.296 * S - 15.8
    # L = letters per 100 words, S = sentences per 100 words
    total_letters = sum(len(re.sub(r"[^A-Za-z0-9]", "", w)) for w in words)
    L = (total_letters / n_words) * 100.0
    S = (n_sentences / n_words) * 100.0
    coleman_liau = 0.0588 * L - 0.296 * S - 15.8
    coleman_liau = max(0.0, coleman_liau)

    return {
        "flesch_reading_ease": round(fre, 2),
        "flesch_kincaid_grade_level": round(fkgl, 2),
        "smog_index": round(smog, 2),
        "gunning_fog": round(gunning_fog, 2),
        "coleman_liau": round(coleman_liau, 2),
        "num_words": n_words,
        "num_sentences": n_sentences,
        "num_syllables": total_syllables,
    }

"""
analysis/metrics/lexical_complexity.py
──────────────────────────────────────
Lexical complexity and diversity metrics:
- Average word length
- Average word frequency (Zipf-scale log frequency, via wordfreq)
- Type-Token Ratio (TTR)
- Measure of Textual Lexical Diversity (MTLD)
- Proportion of difficult words (Zipf < 3)
"""

import re
import math
from typing import Dict, List
from collections import Counter
from .readability import tokenize_words

# Words rarer than ~1 per million (Zipf < 3) count as difficult, e.g. "pneumothorax" 2.4, "lungs" 4.0.
DIFFICULT_ZIPF_THRESHOLD = 3.0


def compute_ttr(words: List[str]) -> float:
    """Type-Token Ratio: unique words / total words."""
    if not words:
        return 0.0
    return round(len(set(w.lower() for w in words)) / len(words), 4)

def compute_mtld(words: List[str], ttr_threshold: float = 0.72) -> float:
    """
    Measure of Textual Lexical Diversity (MTLD, McCarthy & Jarvis 2010).
    Calculates the mean length of sequential text segments maintaining TTR >= 0.72.
    Evaluated in both forward and reverse directions.
    """
    if len(words) < 10:
        return round(float(len(set(w.lower() for w in words))), 2)

    def _calc_factors(seq: List[str]) -> float:
        factors = 0.0
        current_words = []
        for w in seq:
            current_words.append(w.lower())
            current_ttr = len(set(current_words)) / len(current_words)
            if current_ttr < ttr_threshold:
                factors += 1.0
                current_words = []
        if current_words:
            # Partial factor calculation
            current_ttr = len(set(current_words)) / len(current_words)
            if current_ttr < 1.0:
                partial = (1.0 - current_ttr) / (1.0 - ttr_threshold)
                factors += partial
        return factors

    forward_factors = _calc_factors(words)
    backward_factors = _calc_factors(list(reversed(words)))

    mean_factors = (forward_factors + backward_factors) / 2.0
    if mean_factors == 0:
        return float(len(words))

    mtld = len(words) / mean_factors
    return round(mtld, 2)

def compute_zipf_frequency(word: str) -> float:
    """Zipf log frequency of an English word (0 = unseen, ~7 = 'the'), via wordfreq."""
    from wordfreq import zipf_frequency  # fail loudly if missing
    return zipf_frequency(word.lower(), "en")


def compute_lexical_complexity(text: str) -> Dict[str, float]:
    """
    Compute comprehensive lexical complexity metrics:
    - average_word_length (characters per word)
    - average_word_frequency (Zipf score)
    - ttr (Type-Token Ratio)
    - mtld (Measure of Textual Lexical Diversity)
    - proportion_difficult_words (ratio of words with Zipf < 3)
    """
    words = tokenize_words(text)
    if not words:
        return {
            "average_word_length": 0.0,
            "average_word_frequency": 0.0,
            "ttr": 0.0,
            "mtld": 0.0,
            "proportion_difficult_words": 0.0,
        }

    # 1. Average word length
    total_chars = sum(len(w) for w in words)
    avg_len = total_chars / len(words)

    # 2. Average word frequency (Zipf-like scale)
    freq_scores = [compute_zipf_frequency(w) for w in words]
    avg_freq = sum(freq_scores) / len(freq_scores)

    # 3. TTR
    ttr = compute_ttr(words)

    # 4. MTLD
    mtld = compute_mtld(words)

    # 5. Proportion of difficult / rare words
    difficult_count = sum(1 for f in freq_scores if f < DIFFICULT_ZIPF_THRESHOLD)
    prop_difficult = difficult_count / len(words)

    return {
        "average_word_length": round(avg_len, 2),
        "average_word_frequency": round(avg_freq, 2),
        "ttr": round(ttr, 4),
        "mtld": round(mtld, 2),
        "proportion_difficult_words": round(prop_difficult, 4),
    }

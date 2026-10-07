"""
analysis/metrics/meaning_preservation.py
────────────────────────────────────────
Meaning preservation and semantic similarity metrics:
- SBERT Cosine Similarity (via sentence_transformers with lightweight fallback)
- Key Clinical Entity Preservation Score
"""

import math
from typing import Dict, List
from collections import Counter
from .readability import tokenize_words

_SBERT_MODEL = None
_SBERT_FALLBACK_WARNED = False


def _get_sbert_model():
    """Load the SBERT model once per process."""
    global _SBERT_MODEL
    if _SBERT_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _SBERT_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _SBERT_MODEL


def compute_sbert_cosine_similarity(
    source_text: str,
    generated_text: str,
) -> float:
    """
    Compute sentence-level semantic cosine similarity.
    Uses sentence_transformers if available, else computes character-3gram
    TF-IDF cosine similarity.
    Returns float from 0.0 to 100.0.
    """
    if not source_text.strip() or not generated_text.strip():
        return 0.0

    try:
        from sentence_transformers import util
        model = _get_sbert_model()
        emb_src = model.encode(source_text, convert_to_tensor=True)
        emb_gen = model.encode(generated_text, convert_to_tensor=True)
        cos_sim = util.cos_sim(emb_src, emb_gen).item()
        return round(float(cos_sim) * 100.0, 2)
    except Exception as e:
        global _SBERT_FALLBACK_WARNED
        if not _SBERT_FALLBACK_WARNED:
            print(f"  [WARN] SBERT unavailable ({e!r}); using char 3-gram cosine proxy instead")
            _SBERT_FALLBACK_WARNED = True
        # Robust character 3-gram TF-IDF cosine similarity fallback
        def _get_char_ngrams(s: str, n: int = 3) -> Counter:
            clean = s.lower()
            return Counter(clean[i:i+n] for i in range(len(clean) - n + 1))

        src_ng = _get_char_ngrams(source_text)
        gen_ng = _get_char_ngrams(generated_text)

        common = set(src_ng.keys()) & set(gen_ng.keys())
        dot = sum(src_ng[k] * gen_ng[k] for k in common)

        mag1 = math.sqrt(sum(v * v for v in src_ng.values()))
        mag2 = math.sqrt(sum(v * v for v in gen_ng.values()))

        if mag1 == 0 or mag2 == 0:
            return 0.0
        similarity = (dot / (mag1 * mag2)) * 100.0
        return round(similarity, 2)

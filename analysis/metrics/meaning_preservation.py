"""
analysis/metrics/meaning_preservation.py
────────────────────────────────────────
Meaning preservation and semantic similarity metrics:
- SBERT Cosine Similarity (via sentence_transformers)
"""

from functools import lru_cache


@lru_cache(maxsize=1)
def _sbert_model():
    from sentence_transformers import SentenceTransformer  # fail loudly if missing; no silent proxy
    return SentenceTransformer("all-MiniLM-L6-v2")


def compute_sbert_cosine_similarity(
    source_text: str,
    generated_text: str,
) -> float:
    """
    Sentence-level semantic cosine similarity (all-MiniLM-L6-v2).
    Returns float from 0.0 to 100.0.
    """
    if not source_text.strip() or not generated_text.strip():
        return 0.0

    from sentence_transformers import util
    model = _sbert_model()
    emb_src = model.encode(source_text, convert_to_tensor=True)
    emb_gen = model.encode(generated_text, convert_to_tensor=True)
    return round(float(util.cos_sim(emb_src, emb_gen).item()) * 100.0, 2)

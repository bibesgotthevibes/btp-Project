"""
analysis/metrics/quality.py
───────────────────────────
Text generation quality and overlap metrics:
- SARI (Xu et al. 2016) via EASSE
- ROUGE-1, ROUGE-2, ROUGE-L (via rouge_score)
- BERTScore (via bert_score)
"""

from functools import lru_cache
from typing import Dict, List

# ── 1. SARI (Xu et al. 2016) via EASSE ─────────────────────────────────────────

def compute_sari(
    source_text: str,
    generated_text: str,
    reference_texts: List[str] = None,
) -> float:
    """
    SARI with the EASSE reference implementation (standard in simplification papers):
    mean of ADD F1, KEEP F1 and DELETE precision over 1-4-grams, 0-100.
    Without a gold reference it falls back to the source as reference (self-reference
    mode used by the curated runner); that only measures how much was kept.
    """
    if not generated_text.strip() or not source_text.strip():
        return 0.0
    from easse.sari import corpus_sari  # fail loudly if missing
    refs = reference_texts or [source_text]
    return round(float(corpus_sari(orig_sents=[source_text], sys_sents=[generated_text],
                                   refs_sents=[[r] for r in refs])), 2)


# ── 2. ROUGE Calculation ───────────────────────────────────────────────────────

def compute_rouge_scores(reference: str, hypothesis: str) -> Dict[str, float]:
    """Compute ROUGE-1, ROUGE-2, ROUGE-L F1 scores."""
    from rouge_score import rouge_scorer  # fail loudly if missing; no silent token-overlap proxy
    scores = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True).score(reference, hypothesis)
    return {
        "rouge1_f1": round(scores["rouge1"].fmeasure * 100.0, 2),
        "rouge2_f1": round(scores["rouge2"].fmeasure * 100.0, 2),
        "rougeL_f1": round(scores["rougeL"].fmeasure * 100.0, 2),
    }


# ── 3. BERTScore ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _bert_scorer():
    import bert_score  # fail loudly if missing; no silent word-overlap proxy
    return bert_score.BERTScorer(lang="en")  # roberta-large, loaded once


def compute_bertscore(
    reference: str,
    hypothesis: str,
) -> Dict[str, float]:
    """Compute BERTScore (F1, Precision, Recall) on a 0-100 scale."""
    P, R, F1 = _bert_scorer().score([hypothesis], [reference])
    return {
        "bertscore_precision": round(float(P[0]) * 100.0, 2),
        "bertscore_recall": round(float(R[0]) * 100.0, 2),
        "bertscore_f1": round(float(F1[0]) * 100.0, 2),
    }

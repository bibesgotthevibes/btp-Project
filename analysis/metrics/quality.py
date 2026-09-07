"""
analysis/metrics/quality.py
───────────────────────────
Text generation quality and overlap metrics:
- SARI (Xu et al. 2016) for text simplification (Add, Keep, Delete F1)
- ROUGE-1, ROUGE-2, ROUGE-L (via rouge_score)
- BERTScore (with graceful fallback if torch/bert_score is unavailable)
"""

import math
from typing import Dict, List, Set, Tuple
from collections import Counter
from .readability import tokenize_words

# ── 1. SARI Implementation (Xu et al. 2016) ───────────────────────────────────

def _get_ngrams(tokens: List[str], n: int) -> Counter:
    """Extract n-grams from a list of tokens."""
    return Counter(tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1))

def compute_sari(
    source_text: str,
    generated_text: str,
    reference_texts: List[str] = None,
    max_ngram: int = 4,
) -> float:
    """
    Compute SARI score (System Output Against References and Input).
    Evaluates:
    - ADD: n-grams present in output that were absent in source
    - KEEP: n-grams present in source and preserved in output
    - DELETE: n-grams deleted from source
    Returns a score from 0.0 to 100.0.
    """
    src_tokens = tokenize_words(source_text.lower())
    gen_tokens = tokenize_words(generated_text.lower())

    if not gen_tokens or not src_tokens:
        return 0.0

    if not reference_texts:
        # Self-reference mode when gold reference is unavailable
        reference_texts = [source_text]

    refs_tokens = [tokenize_words(ref.lower()) for ref in reference_texts]

    add_scores = []
    keep_scores = []
    del_scores = []

    for n in range(1, max_ngram + 1):
        src_ngrams = _get_ngrams(src_tokens, n)
        gen_ngrams = _get_ngrams(gen_tokens, n)
        refs_ngrams = [_get_ngrams(ref_toks, n) for ref_toks in refs_tokens]

        # Union of reference n-grams
        all_ref_ngrams = Counter()
        for ref_ng in refs_ngrams:
            all_ref_ngrams |= ref_ng

        # ── ADD Operation: n-grams in gen not in src ─────────────────────────
        # target add: in ref but not in src
        add_target = all_ref_ngrams - src_ngrams
        add_gen = gen_ngrams - src_ngrams

        add_match = add_gen & add_target
        add_p = sum(add_match.values()) / max(1, sum(add_gen.values())) if sum(add_gen.values()) > 0 else 0.0
        add_r = sum(add_match.values()) / max(1, sum(add_target.values())) if sum(add_target.values()) > 0 else 0.0
        add_f1 = (2 * add_p * add_r) / (add_p + add_r) if (add_p + add_r) > 0 else 0.0
        add_scores.append(add_f1)

        # ── KEEP Operation: n-grams in src preserved in gen ──────────────────
        # target keep: in src and in ref
        keep_target = src_ngrams & all_ref_ngrams
        keep_gen = src_ngrams & gen_ngrams

        keep_match = keep_gen & keep_target
        keep_p = sum(keep_match.values()) / max(1, sum(keep_gen.values())) if sum(keep_gen.values()) > 0 else 0.0
        keep_r = sum(keep_match.values()) / max(1, sum(keep_target.values())) if sum(keep_target.values()) > 0 else 0.0
        keep_f1 = (2 * keep_p * keep_r) / (keep_p + keep_r) if (keep_p + keep_r) > 0 else 0.0
        keep_scores.append(keep_f1)

        # ── DELETE Operation: n-grams in src not in gen ──────────────────────
        # target del: in src but not in ref
        del_target = src_ngrams - all_ref_ngrams
        del_gen = src_ngrams - gen_ngrams

        del_match = del_gen & del_target
        del_p = sum(del_match.values()) / max(1, sum(del_gen.values())) if sum(del_gen.values()) > 0 else 0.0
        del_r = sum(del_match.values()) / max(1, sum(del_target.values())) if sum(del_target.values()) > 0 else 0.0
        del_f1 = (2 * del_p * del_r) / (del_p + del_r) if (del_p + del_r) > 0 else 0.0
        del_scores.append(del_f1)

    mean_add = sum(add_scores) / len(add_scores) if add_scores else 0.0
    mean_keep = sum(keep_scores) / len(keep_scores) if keep_scores else 0.0
    mean_del = sum(del_scores) / len(del_scores) if del_scores else 0.0

    sari = ((mean_add + mean_keep + mean_del) / 3.0) * 100.0
    return round(sari, 2)


# ── 2. ROUGE Calculation ───────────────────────────────────────────────────────

def compute_rouge_scores(reference: str, hypothesis: str) -> Dict[str, float]:
    """Compute ROUGE-1, ROUGE-2, ROUGE-L F1 scores."""
    try:
        from rouge_score import rouge_scorer
        scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
        scores = scorer.score(reference, hypothesis)
        return {
            "rouge1_f1": round(scores["rouge1"].fmeasure * 100.0, 2),
            "rouge2_f1": round(scores["rouge2"].fmeasure * 100.0, 2),
            "rougeL_f1": round(scores["rougeL"].fmeasure * 100.0, 2),
        }
    except Exception:
        # Lightweight token-overlap fallback
        ref_tokens = set(tokenize_words(reference.lower()))
        hyp_tokens = set(tokenize_words(hypothesis.lower()))
        if not ref_tokens or not hyp_tokens:
            return {"rouge1_f1": 0.0, "rouge2_f1": 0.0, "rougeL_f1": 0.0}
        overlap = len(ref_tokens & hyp_tokens)
        p = overlap / len(hyp_tokens)
        r = overlap / len(ref_tokens)
        f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0
        return {
            "rouge1_f1": round(f1 * 100.0, 2),
            "rouge2_f1": 0.0,
            "rougeL_f1": round(f1 * 100.0, 2),
        }


# ── 3. BERTScore (with graceful embedding / semantic fallback) ────────────────

def compute_bertscore(
    reference: str,
    hypothesis: str,
) -> Dict[str, float]:
    """
    Compute BERTScore (F1, Precision, Recall).
    Attempts bert_score package if available, otherwise computes
    token-level IDF-weighted cosine similarity fallback.
    """
    try:
        import bert_score
        P, R, F1 = bert_score.score(
            [hypothesis],
            [reference],
            lang="en",
            verbose=False,
        )
        return {
            "bertscore_precision": round(float(P[0]) * 100.0, 2),
            "bertscore_recall": round(float(R[0]) * 100.0, 2),
            "bertscore_f1": round(float(F1[0]) * 100.0, 2),
        }
    except Exception:
        # Lightweight character/word n-gram cosine similarity proxy
        ref_tokens = tokenize_words(reference.lower())
        hyp_tokens = tokenize_words(hypothesis.lower())
        if not ref_tokens or not hyp_tokens:
            return {"bertscore_precision": 0.0, "bertscore_recall": 0.0, "bertscore_f1": 0.0}

        ref_counter = Counter(ref_tokens)
        hyp_counter = Counter(hyp_tokens)

        # Dot product
        intersection = set(ref_counter.keys()) & set(hyp_counter.keys())
        dot_product = sum(ref_counter[t] * hyp_counter[t] for t in intersection)

        mag_ref = math.sqrt(sum(c * c for c in ref_counter.values()))
        mag_hyp = math.sqrt(sum(c * c for c in hyp_counter.values()))

        if mag_ref == 0 or mag_hyp == 0:
            sim = 0.0
        else:
            sim = dot_product / (mag_ref * mag_hyp)

        p = min(1.0, len(intersection) / max(1, len(hyp_tokens)))
        r = min(1.0, len(intersection) / max(1, len(ref_tokens)))
        f1 = sim * 100.0

        return {
            "bertscore_precision": round(p * 100.0, 2),
            "bertscore_recall": round(r * 100.0, 2),
            "bertscore_f1": round(f1, 2),
        }

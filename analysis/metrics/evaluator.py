"""
analysis/metrics/evaluator.py
─────────────────────────────
Unified evaluator bringing together all metric dimensions:
- Quality (SARI, ROUGE-1/2/L, BERTScore)
- Readability (FKGL, Flesch Reading Ease, SMOG, Gunning Fog, Coleman-Liau)
- Lexical Complexity (average word frequency, average word length, MTLD, TTR, proportion difficult words)
- Meaning Preservation (SBERT cosine similarity)
- Clinical & Jargon (parenthetical explanation count/rate, jargon reduction, compression ratio)
"""

from typing import Dict, Any, Optional

from .readability import compute_readability_metrics
from .lexical_complexity import compute_lexical_complexity
from .quality import compute_sari, compute_rouge_scores, compute_bertscore
from .meaning_preservation import compute_sbert_cosine_similarity
from .clinical_jargon import compute_clinical_jargon_metrics

def evaluate_generation(
    source_text: str,
    generated_text: str,
    reference_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run full metric battery on a single generated text against its source
    and optional reference text.
    """
    scores: Dict[str, Any] = {}

    # Guard against empty generations
    if not generated_text or not generated_text.strip():
        return {
            "flesch_reading_ease": 0.0,
            "flesch_kincaid_grade_level": 0.0,
            "smog_index": 0.0,
            "gunning_fog": 0.0,
            "coleman_liau": 0.0,
            "average_word_length": 0.0,
            "average_word_frequency": 0.0,
            "ttr": 0.0,
            "mtld": 0.0,
            "proportion_difficult_words": 0.0,
            "sari": 0.0,
            "rouge1_f1": 0.0,
            "rouge2_f1": 0.0,
            "rougeL_f1": 0.0,
            "bertscore_f1": 0.0,
            "sbert_cosine_similarity": 0.0,
            "parenthetical_explanation_count": 0,
            "parenthetical_explanation_rate": 0.0,
            "jargon_reduction_pct": 0.0,
            "compression_ratio_chars": 0.0,
            "compression_ratio_words": 0.0,
        }

    # 1. Readability
    read_scores = compute_readability_metrics(generated_text)
    scores.update(read_scores)

    # 2. Lexical Complexity
    lex_scores = compute_lexical_complexity(generated_text)
    scores.update(lex_scores)

    # 3. Meaning Preservation & Overlap
    target_ref = reference_text if (reference_text and reference_text.strip()) else source_text

    rouge_scores = compute_rouge_scores(target_ref, generated_text)
    scores.update(rouge_scores)

    bert_scores = compute_bertscore(target_ref, generated_text)
    scores.update(bert_scores)

    sari_score = compute_sari(source_text, generated_text, [target_ref] if target_ref else None)
    scores["sari"] = sari_score

    sbert_score = compute_sbert_cosine_similarity(source_text, generated_text)
    scores["sbert_cosine_similarity"] = sbert_score

    # 4. Clinical Domain & Jargon
    jargon_scores = compute_clinical_jargon_metrics(source_text, generated_text)
    scores.update(jargon_scores)

    return scores

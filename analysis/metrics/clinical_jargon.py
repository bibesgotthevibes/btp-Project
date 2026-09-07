"""
analysis/metrics/clinical_jargon.py
───────────────────────────────────
Clinical domain-specific evaluation metrics:
- Parenthetical explanation count & rate (detects 'medical term (plain explanation)' per Rule 1)
- Medical jargon density and reduction percentage (before vs after)
- Compression ratio (characters and words)
"""

import re
from typing import Dict, List, Set
from .readability import tokenize_words

# Curated clinical terms from btp_lite / MedSimplify dictionary
CLINICAL_JARGON_TERMS: Set[str] = {
    "hypertension", "diabetes", "mellitus", "myocardial", "infarction", "renal", "septicemia",
    "sepsis", "pneumonia", "tuberculosis", "pneumothorax", "endocarditis", "spondylodiscitis",
    "hypotension", "pyrexia", "dyspnea", "edema", "abscess", "crohn", "cerebrovascular",
    "anemia", "tachycardia", "bradycardia", "fibrillation", "hemodialysis", "tracheostomy",
    "thoracotomy", "pneumonectomy", "ileocolectomy", "anastomosis", "debridement", "fistula",
    "intramuscular", "intravenous", "percutaneous", "antibiotic", "procalcitonin", "hemoglobin",
    "creatinine", "bilirubin", "saturation", "afebrile", "eupneic", "acyanotic", "anicteric",
    "vesicular", "adenocarcinoma", "carcinoma", "perineural", "gleason", "isup", "tnm",
    "resection", "margin", "amacr", "cytokeratin", "cavernoma", "gliotic", "ischemic",
    "ventriculitis", "periventricular", "osteomyelitis", "leukocytosis", "hyponatremia",
}

PARENTHETICAL_PATTERN = re.compile(r"\b([A-Za-z\'-]+(?:\s+[A-Za-z\'-]+){0,3})\s*\(([^)]{3,80})\)")

def count_parenthetical_explanations(text: str) -> List[Dict[str, str]]:
    """
    Detect all occurrences where a medical term is explained in parentheses,
    e.g. 'hypertension (high BP)'.
    """
    matches = PARENTHETICAL_PATTERN.findall(text)
    results = []
    for term, expl in matches:
        t_clean = term.strip().lower()
        e_clean = expl.strip()
        # Filter out purely numeric citations or short abbreviations
        if not re.match(r"^[\d\s.,-]+$", e_clean):
            results.append({"term": t_clean, "explanation": e_clean})
    return results

def count_jargon_terms(text: str) -> int:
    """Count total occurrences of clinical jargon terms in text."""
    words = [w.lower() for w in tokenize_words(text)]
    return sum(1 for w in words if w in CLINICAL_JARGON_TERMS)

def compute_clinical_jargon_metrics(source_text: str, generated_text: str) -> Dict[str, float]:
    """
    Compute domain-specific metrics for simplification & summarization:
    - parenthetical_explanation_count
    - parenthetical_explanation_rate (per 100 words)
    - jargon_source_count
    - jargon_generated_count
    - jargon_reduction_pct
    - compression_ratio_chars
    - compression_ratio_words
    """
    src_words = tokenize_words(source_text)
    gen_words = tokenize_words(generated_text)

    n_src_words = max(1, len(src_words))
    n_gen_words = max(1, len(gen_words))

    n_src_chars = max(1, len(source_text.strip()))
    n_gen_chars = len(generated_text.strip())

    # Parenthetical explanations
    explanations = count_parenthetical_explanations(generated_text)
    num_explanations = len(explanations)
    explanation_rate = (num_explanations / n_gen_words) * 100.0

    # Jargon counts
    src_jargon = count_jargon_terms(source_text)
    gen_jargon = count_jargon_terms(generated_text)

    if src_jargon > 0:
        jargon_reduction = ((src_jargon - gen_jargon) / src_jargon) * 100.0
    else:
        jargon_reduction = 0.0

    # Compression ratios
    comp_chars = n_gen_chars / n_src_chars
    comp_words = n_gen_words / n_src_words

    return {
        "parenthetical_explanation_count": num_explanations,
        "parenthetical_explanation_rate": round(explanation_rate, 2),
        "jargon_source_count": src_jargon,
        "jargon_generated_count": gen_jargon,
        "jargon_reduction_pct": round(jargon_reduction, 2),
        "compression_ratio_chars": round(comp_chars, 3),
        "compression_ratio_words": round(comp_words, 3),
    }

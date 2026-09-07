"""
analysis/evaluate_only.py
─────────────────────────
Standalone evaluation script that computes multi-metric evaluation scores
on previously generated results stored in results/generations.json.

Does NOT make any API calls. Re-evaluates quickly and saves to:
- results/evaluations.json
- results/evaluations.csv
"""

import sys
import json
import csv
from pathlib import Path
from typing import Dict, List, Any

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis.config import RESULTS_DIR
from analysis.metrics import evaluate_generation

GENERATIONS_JSON = RESULTS_DIR / "generations.json"
EVALUATIONS_JSON = RESULTS_DIR / "evaluations.json"
EVALUATIONS_CSV = RESULTS_DIR / "evaluations.csv"


def run_evaluation_on_saved_results() -> List[Dict[str, Any]]:
    """Read generations.json, evaluate all completed trials, and write evaluations."""
    if not GENERATIONS_JSON.exists():
        print(f"❌ Error: {GENERATIONS_JSON} does not exist. Run runner.py first to generate outputs.")
        return []

    with open(GENERATIONS_JSON, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"\n======================================================================")
    print(f"📊 DECOUPLED METRIC EVALUATOR")
    print(f"======================================================================")
    print(f"• Input Records: {len(records)} from {GENERATIONS_JSON}")
    print(f"• Computing metrics across Quality, Readability, Lexical, & Jargon...")
    print(f"======================================================================\n")

    eval_records = []
    evaluated_count = 0

    for i, r in enumerate(records):
        trial_id = r.get("trial_id", f"trial_{i}")
        status = r.get("status", "")
        src = r.get("source_text", "")
        out = r.get("output_text", "")

        entry = dict(r)

        if status == "success" and out.strip():
            scores = evaluate_generation(source_text=src, generated_text=out)
            entry["metrics"] = scores
            evaluated_count += 1
            if evaluated_count % 10 == 0 or evaluated_count == 1:
                print(f"  [{evaluated_count}] Evaluated {trial_id} -> FKGL={scores.get('flesch_kincaid_grade_level')}, SARI={scores.get('sari')}, ROUGE1={scores.get('rouge1_f1')}")
        else:
            entry["metrics"] = None

        eval_records.append(entry)

    # 1. Save evaluations.json
    tmp_json = EVALUATIONS_JSON.with_suffix(".tmp")
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(eval_records, f, indent=2, ensure_ascii=False)
    tmp_json.replace(EVALUATIONS_JSON)

    # 2. Save evaluations.csv (flattened metrics)
    if eval_records:
        metric_keys = [
            "flesch_reading_ease", "flesch_kincaid_grade_level", "smog_index", "gunning_fog", "coleman_liau",
            "average_word_length", "average_word_frequency", "ttr", "mtld", "proportion_difficult_words",
            "sari", "rouge1_f1", "rouge2_f1", "rougeL_f1", "bertscore_f1", "sbert_cosine_similarity",
            "parenthetical_explanation_count", "parenthetical_explanation_rate", "jargon_reduction_pct",
            "compression_ratio_chars", "compression_ratio_words",
        ]

        fieldnames = [
            "trial_id", "task", "datatype", "sample_id", "sample_title",
            "model", "strategy", "status", "provider", "latency_seconds",
        ] + metric_keys

        tmp_csv = EVALUATIONS_CSV.with_suffix(".tmp")
        with open(tmp_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in eval_records:
                flat = dict(r)
                m = r.get("metrics") or {}
                for k in metric_keys:
                    flat[k] = m.get(k, "")
                writer.writerow(flat)
        tmp_csv.replace(EVALUATIONS_CSV)

    print(f"\n======================================================================")
    print(f"✅ EVALUATION FINISHED")
    print(f"======================================================================")
    print(f"• Successfully Evaluated: {evaluated_count} / {len(records)} trials")
    print(f"• Scored JSON: {EVALUATIONS_JSON}")
    print(f"• Scored CSV:  {EVALUATIONS_CSV}")
    print(f"======================================================================\n")

    return eval_records


if __name__ == "__main__":
    run_evaluation_on_saved_results()

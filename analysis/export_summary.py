"""
analysis/export_summary.py
──────────────────────────
Generates comparative summary reports and markdown leaderboard tables
from results/evaluations.json.

Groups comparisons by:
- Model performance (Quality, Readability, Lexical Complexity, Meaning Preservation)
- Task comparison (Summarization vs Simplification)
- Datatype comparison (Discharge vs Pathology vs Radiology)
- Prompt Strategy (Zero-shot vs Few-shot)
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis.config import RESULTS_DIR

EVALUATIONS_JSON = RESULTS_DIR / "evaluations.json"
SUMMARY_REPORT_MD = RESULTS_DIR / "summary_report.md"


def mean(values: List[float]) -> float:
    vals = [v for v in values if isinstance(v, (int, float))]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def generate_summary_report() -> str:
    if not EVALUATIONS_JSON.exists():
        print(f"❌ Error: {EVALUATIONS_JSON} does not exist. Run evaluate_only.py first.")
        return ""

    with open(EVALUATIONS_JSON, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Filter to successful trials with metrics
    valid_records = [r for r in records if r.get("status") == "success" and r.get("metrics")]

    lines = []
    lines.append("# Comparative Analysis & Benchmark Summary Report\n")
    lines.append(f"**Total Records**: {len(records)} | **Successfully Scored**: {len(valid_records)}\n")

    if not valid_records:
        lines.append("> [!WARNING]\n> No successful generations with metrics were found in evaluations.json.\n")
        content = "\n".join(lines)
        with open(SUMMARY_REPORT_MD, "w", encoding="utf-8") as f:
            f.write(content)
        return content

    # ── 1. Model Leaderboard ──────────────────────────────────────────────────
    lines.append("## 1. Model Comparison Leaderboard\n")
    lines.append("| Model | Task | FKGL (↓) | FRE (↑) | SARI (↑) | ROUGE-1 | BERTScore | SBERT Cos | Jargon Red % | Latency (s) |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")

    # Group by (model, task)
    by_model_task = defaultdict(list)
    for r in valid_records:
        key = (r["model"], r["task"])
        by_model_task[key].append(r)

    for (model, task), group in sorted(by_model_task.items()):
        fkgl = mean([g["metrics"].get("flesch_kincaid_grade_level") for g in group])
        fre = mean([g["metrics"].get("flesch_reading_ease") for g in group])
        sari = mean([g["metrics"].get("sari") for g in group])
        r1 = mean([g["metrics"].get("rouge1_f1") for g in group])
        bs = mean([g["metrics"].get("bertscore_f1") for g in group])
        sbert = mean([g["metrics"].get("sbert_cosine_similarity") for g in group])
        j_red = mean([g["metrics"].get("jargon_reduction_pct") for g in group])
        lat = mean([g.get("latency_seconds", 0) for g in group])

        lines.append(f"| **{model}** | {task} | {fkgl} | {fre} | {sari} | {r1}% | {bs}% | {sbert}% | {j_red}% | {lat}s |")

    lines.append("\n---\n")

    # ── 2. Task Comparison: Simplification vs Summarization ───────────────────
    lines.append("## 2. Task Comparison: Simplification vs. Summarization\n")
    lines.append("| Task | Avg FKGL | Avg FRE | Complex Words % | Avg Word Len | SARI | Comp (Words) | Par Explanations/100w |")
    lines.append("|---|---|---|---|---|---|---|---|")

    by_task = defaultdict(list)
    for r in valid_records:
        by_task[r["task"]].append(r)

    for task, group in sorted(by_task.items()):
        fkgl = mean([g["metrics"].get("flesch_kincaid_grade_level") for g in group])
        fre = mean([g["metrics"].get("flesch_reading_ease") for g in group])
        cw_pct = mean([g["metrics"].get("proportion_difficult_words", 0) * 100 for g in group])
        wl = mean([g["metrics"].get("average_word_length") for g in group])
        sari = mean([g["metrics"].get("sari") for g in group])
        comp = mean([g["metrics"].get("compression_ratio_words") for g in group])
        expl_rate = mean([g["metrics"].get("parenthetical_explanation_rate") for g in group])

        lines.append(f"| **{task.capitalize()}** | {fkgl} | {fre} | {cw_pct}% | {wl} | {sari} | {comp}x | {expl_rate} |")

    lines.append("\n---\n")

    # ── 3. Datatype Breakdown: Discharge vs Pathology vs Radiology ────────────
    lines.append("## 3. Datatype Performance Comparison\n")
    lines.append("| Datatype | Task | Samples | FKGL (↓) | FRE (↑) | SARI (↑) | ROUGE-L | Jargon Red % |")
    lines.append("|---|---|---|---|---|---|---|---|")

    by_dt_task = defaultdict(list)
    for r in valid_records:
        key = (r["datatype"], r["task"])
        by_dt_task[key].append(r)

    for (dt, task), group in sorted(by_dt_task.items()):
        n = len(group)
        fkgl = mean([g["metrics"].get("flesch_kincaid_grade_level") for g in group])
        fre = mean([g["metrics"].get("flesch_reading_ease") for g in group])
        sari = mean([g["metrics"].get("sari") for g in group])
        rl = mean([g["metrics"].get("rougeL_f1") for g in group])
        j_red = mean([g["metrics"].get("jargon_reduction_pct") for g in group])

        lines.append(f"| **{dt.capitalize()}** | {task} | {n} | {fkgl} | {fre} | {sari} | {rl}% | {j_red}% |")

    lines.append("\n---\n")

    # ── 4. Prompt Strategy: Zero-shot vs Few-shot ─────────────────────────────
    lines.append("## 4. Prompt Strategy: Zero-Shot vs. Few-Shot\n")
    lines.append("| Strategy | Task | SARI (↑) | Par Explanations/100w | ROUGE-1 | FKGL (↓) | FRE (↑) |")
    lines.append("|---|---|---|---|---|---|---|")

    by_strat_task = defaultdict(list)
    for r in valid_records:
        key = (r["strategy"], r["task"])
        by_strat_task[key].append(r)

    for (strat, task), group in sorted(by_strat_task.items()):
        sari = mean([g["metrics"].get("sari") for g in group])
        expl_rate = mean([g["metrics"].get("parenthetical_explanation_rate") for g in group])
        r1 = mean([g["metrics"].get("rouge1_f1") for g in group])
        fkgl = mean([g["metrics"].get("flesch_kincaid_grade_level") for g in group])
        fre = mean([g["metrics"].get("flesch_reading_ease") for g in group])

        lines.append(f"| **{strat}** | {task} | {sari} | {expl_rate} | {r1}% | {fkgl} | {fre} |")

    content = "\n".join(lines)
    with open(SUMMARY_REPORT_MD, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Summary report generated at {SUMMARY_REPORT_MD}")
    return content


if __name__ == "__main__":
    generate_summary_report()

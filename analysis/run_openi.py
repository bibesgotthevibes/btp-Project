"""
analysis/run_openi.py
─────────────────────
Reference-based radiology simplification benchmark on Open-i (NLMCXR) reports
paired with LaymanRRG lay references
(datasets/lay_reference_datasets/radiology/openi_lay_pairs.csv).

Uses the chest X-ray prompt variant (RADIOLOGY_CXR_SIMPLIFY_* in prompts/radiology_prompts.py).
Unlike runner.py (curated samples, scored against the source), every output here
is scored against a lay-language ground truth, so SARI / ROUGE / BERTScore are
meaningful. A "reference" row scores the gold lay text itself as a readability
baseline (its overlap scores are trivially perfect; ignore those).

Usage:
  python -m analysis.run_openi --n 20                      # all configured models
  python -m analysis.run_openi --n 50 --models ollama/llama3.1:8b --strategies zero-shot
  python -m analysis.run_openi --summary                   # re-print summary only
"""

import sys
import json
import itertools
import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis.config import MODELS, STRATEGIES, RESULTS_DIR, DATASETS_DIR
from analysis.prompts import build_prompt
from analysis.providers import ModelRouter
from analysis.metrics import evaluate_generation

PAIRS_CSV = DATASETS_DIR / "lay_reference_datasets" / "radiology" / "openi_lay_pairs.csv"
OUT_DIR = RESULTS_DIR / "openi"
OUT_JSON = OUT_DIR / "results.json"
OUT_CSV = OUT_DIR / "results.csv"

SUMMARY_METRICS = ["sari", "bertscore_f1", "rougeL_f1", "alignscore", "negation_dropped", "negation_added",
                   "negation_cue_retention", "flesch_kincaid_grade_level", "proportion_difficult_words"]


def load_results():
    return json.loads(OUT_JSON.read_text()) if OUT_JSON.exists() else []


def save_results(records):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = OUT_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    tmp.replace(OUT_JSON)
    flat = [{**{k: v for k, v in r.items() if k != "metrics"}, **(r.get("metrics") or {})} for r in records]
    pd.DataFrame(flat).to_csv(OUT_CSV, index=False)


def _key(r):
    return r["sample_id"], r["model"], r["strategy"]


def print_summary(records):
    rows = [{"model": r["model"], "strategy": r["strategy"], **r["metrics"]} for r in records if r.get("metrics")]
    if not rows:
        print("No scored results yet.")
        return
    df = pd.DataFrame(rows)
    groups = ["model", "strategy"]
    table = df.groupby(groups)[SUMMARY_METRICS].mean().round(3)
    table.insert(0, "n", df.groupby(groups).size())
    print("\n" + table.to_string())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20, help="Number of report pairs to run.")
    ap.add_argument("--split", default="validation", choices=["train", "validation"])
    ap.add_argument("--models", nargs="+", default=MODELS, choices=MODELS)
    ap.add_argument("--strategies", nargs="+", default=STRATEGIES, choices=STRATEGIES)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--summary", action="store_true", help="Only print the summary of saved results.")
    args = ap.parse_args()

    records = load_results()
    if args.summary:
        print_summary(records)
        return

    pairs = pd.read_csv(PAIRS_CSV)
    pairs = pairs[pairs.split == args.split]
    pairs = pairs.sample(n=min(args.n, len(pairs)), random_state=args.seed)
    done = {_key(r) for r in records if r["status"] == "success"}
    records = [r for r in records if _key(r) in done]  # drop failed, retry them
    router = ModelRouter()

    for _, p in pairs.iterrows():
        sid, src, ref = p.nlmcxr_file, p.radiology_report, p.layman_report

        if (sid, "reference", "-") not in done:
            records.append({"sample_id": sid, "model": "reference", "strategy": "-", "status": "success",
                            "source_text": src, "reference_text": ref, "output_text": ref,
                            "metrics": evaluate_generation(src, ref, reference_text=ref)})

        for model, strategy in itertools.product(args.models, args.strategies):
            if (sid, model, strategy) in done:
                continue
            system_prompt, user_prompt, _ = build_prompt("simplification", "radiology_cxr", strategy, src)
            res = router.generate(model, system_prompt, user_prompt)
            rec = {"sample_id": sid, "model": model, "strategy": strategy, "status": res.status,
                   "error": res.error, "provider": res.provider, "actual_model": res.model, "latency_seconds": round(res.latency_seconds, 2),
                   "source_text": src, "reference_text": ref, "output_text": res.text, "metrics": None}
            if res.status == "success":
                rec["metrics"] = evaluate_generation(src, res.text, reference_text=ref)
                print(f"✓ {sid} {model} {strategy} ({res.latency_seconds:.1f}s) "
                      f"SARI={rec['metrics']['sari']} FKGL={rec['metrics']['flesch_kincaid_grade_level']}")
            else:
                print(f"✗ {sid} {model} {strategy}: {res.status} — {res.error}")
            records.append(rec)
            save_results(records)  # checkpoint after every trial

    save_results(records)
    print_summary(records)
    print(f"\nSaved: {OUT_JSON}\n       {OUT_CSV}")


if __name__ == "__main__":
    main()

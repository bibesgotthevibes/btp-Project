"""
analysis/runner.py
──────────────────
Main CLI runner for comparative experiments across:
- Tasks: summarization, simplification
- Datatypes: discharge, pathology, radiology (5 curated samples each = 15 total)
- Models: cerebras/gptoss, cerebras/qwen3.8, gemini/3.8flash, gemini/3.1pro
- Strategies: zero-shot, few-shot

Features:
- Deterministic trial keys & instant resumability via atomic checkpoints
- Dual JSON and CSV persistence after every step
- Non-blocking error recovery (missing keys or rate-limits are logged gracefully)
- Optional inline or decoupled multi-metric evaluation
- Built-in --smoke-test and --dry-run modes
"""

import os
import sys
import json
import csv
import time
import argparse
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ensure project root is in path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis.config import (
    TASKS,
    DATATYPES,
    STRATEGIES,
    MODELS,
    RESULTS_DIR,
    CHECKPOINTS_DIR,
)
from analysis.samples import get_curated_samples, get_sample_by_id
from analysis.prompts import build_prompt
from analysis.providers import ModelRouter, GenerationResult
from analysis.metrics import evaluate_generation

GENERATIONS_JSON = RESULTS_DIR / "generations.json"
GENERATIONS_CSV = RESULTS_DIR / "generations.csv"
EVALUATIONS_JSON = RESULTS_DIR / "evaluations.json"
EVALUATIONS_CSV = RESULTS_DIR / "evaluations.csv"


def make_trial_id(task: str, datatype: str, sample_id: str, model: str, strategy: str) -> str:
    """Generate a clean, deterministic filesystem-safe trial key."""
    m_slug = model.replace("/", "_").replace(".", "").replace("-", "_")
    return f"{task}_{datatype}_{sample_id}_{m_slug}_{strategy}"


def load_checkpoint(trial_id: str) -> Optional[Dict[str, Any]]:
    """Load a previously completed trial from checkpoint file."""
    ckpt_path = CHECKPOINTS_DIR / f"{trial_id}.json"
    if ckpt_path.exists():
        try:
            with open(ckpt_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def save_checkpoint(trial_id: str, record: Dict[str, Any]) -> None:
    """Atomically save trial record to checkpoints directory."""
    ckpt_path = CHECKPOINTS_DIR / f"{trial_id}.json"
    tmp_path = ckpt_path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        tmp_path.replace(ckpt_path)
    except Exception as e:
        print(f"  [WARN] Failed to write checkpoint {trial_id}: {e}")


def save_aggregated_results(records: List[Dict[str, Any]]) -> None:
    """Atomically save all trial records to generations.json and generations.csv."""
    # 1. Write generations.json
    tmp_json = GENERATIONS_JSON.with_suffix(".tmp")
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    tmp_json.replace(GENERATIONS_JSON)

    # 2. Write generations.csv
    if records:
        fieldnames = [
            "trial_id", "task", "datatype", "sample_id", "sample_title",
            "model", "strategy", "status", "error", "provider",
            "prompt_tokens", "completion_tokens", "total_tokens",
            "latency_seconds", "source_char_len", "output_char_len",
            "source_snippet", "output_snippet",
        ]
        tmp_csv = GENERATIONS_CSV.with_suffix(".tmp")
        with open(tmp_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in records:
                flat = dict(r)
                src = flat.get("source_text", "")
                out = flat.get("output_text", "")
                flat["source_char_len"] = len(src)
                flat["output_char_len"] = len(out)
                flat["source_snippet"] = src[:120].replace("\n", " ") + "..." if len(src) > 120 else src
                flat["output_snippet"] = out[:120].replace("\n", " ") + "..." if len(out) > 120 else out
                writer.writerow(flat)
        tmp_csv.replace(GENERATIONS_CSV)


def run_benchmark(
    tasks: List[str] = None,
    datatypes: List[str] = None,
    models: List[str] = None,
    strategies: List[str] = None,
    sample_ids: List[str] = None,
    resume: bool = True,
    dry_run: bool = False,
    smoke_test: bool = False,
    run_eval_inline: bool = False,
    pace_delay: float = 1.0,
) -> List[Dict[str, Any]]:
    """Execute the benchmark grid across all requested combinations."""
    tasks = tasks or TASKS
    datatypes = datatypes or DATATYPES
    models = models or MODELS
    strategies = strategies or STRATEGIES

    router = ModelRouter()

    # If smoke test requested, run only 1 sample across tasks and models
    if smoke_test:
        print("\n🧪 [SMOKE TEST MODE]: Running 1 sample across tasks, models, and strategies to verify connectivity.")
        sample_ids = ["DS-01"]
        datatypes = ["discharge"]
        strategies = ["zero-shot"]

    # Filter curated samples
    all_samples = get_curated_samples()
    if datatypes:
        all_samples = [s for s in all_samples if s["datatype"] in datatypes]
    if sample_ids:
        all_samples = [s for s in all_samples if s["sample_id"] in sample_ids]

    total_trials = len(tasks) * len(all_samples) * len(models) * len(strategies)

    print(f"\n======================================================================")
    print(f"🚀 MEDSIMPLIFY BENCHMARK RUNNER")
    print(f"======================================================================")
    print(f"• Tasks ({len(tasks)}): {tasks}")
    print(f"• Datatypes ({len(datatypes)}): {datatypes}")
    print(f"• Samples ({len(all_samples)}): {[s['sample_id'] for s in all_samples]}")
    print(f"• Models ({len(models)}): {models}")
    print(f"• Strategies ({len(strategies)}): {strategies}")
    print(f"• Total Trials in Grid: {total_trials}")
    print(f"• Resumable Checkpoints: {'ENABLED' if resume else 'DISABLED'}")
    print(f"• Mode: {'DRY RUN' if dry_run else 'LIVE EXECUTION'}")
    print(f"======================================================================\n")

    records: List[Dict[str, Any]] = []
    trial_counter = 0
    num_skipped = 0
    num_success = 0
    num_errors = 0

    for task in tasks:
        for sample in all_samples:
            dt = sample["datatype"]
            s_id = sample["sample_id"]
            s_title = sample.get("title", s_id)
            s_text = sample["text"]

            for model in models:
                for strategy in strategies:
                    trial_counter += 1
                    trial_id = make_trial_id(task, dt, s_id, model, strategy)

                    print(f"[{trial_counter}/{total_trials}] {trial_id} ...", end=" ", flush=True)

                    # Checkpoint check
                    if resume and not dry_run:
                        cached = load_checkpoint(trial_id)
                        if cached and cached.get("status") == "success":
                            print(f"⚡ [CACHED] ({cached.get('latency_seconds', 0)}s)")
                            records.append(cached)
                            num_success += 1
                            continue

                    # Assemble prompts
                    sys_prompt, user_content, messages = build_prompt(task, dt, strategy, s_text)

                    if dry_run:
                        print(f"🔎 [DRY RUN OK] (sys_len={len(sys_prompt)}, usr_len={len(user_content)})")
                        records.append({
                            "trial_id": trial_id,
                            "task": task,
                            "datatype": dt,
                            "sample_id": s_id,
                            "sample_title": s_title,
                            "model": model,
                            "strategy": strategy,
                            "status": "dry_run",
                            "error": None,
                            "provider": "mock",
                            "system_prompt": sys_prompt,
                            "user_prompt": user_content,
                            "source_text": s_text,
                            "output_text": "[DRY RUN PLACEHOLDER]",
                            "latency_seconds": 0.0,
                        })
                        continue

                    # Execute live generation call
                    gen_res: GenerationResult = router.generate(
                        model_key=model,
                        system_prompt=sys_prompt,
                        user_prompt=user_content,
                        temperature=0.2,
                        max_tokens=4096,
                    )

                    record = {
                        "trial_id": trial_id,
                        "task": task,
                        "datatype": dt,
                        "sample_id": s_id,
                        "sample_title": s_title,
                        "model": model,
                        "strategy": strategy,
                        "status": gen_res.status,
                        "error": gen_res.error,
                        "provider": gen_res.provider,
                        "prompt_tokens": gen_res.prompt_tokens,
                        "completion_tokens": gen_res.completion_tokens,
                        "total_tokens": gen_res.total_tokens,
                        "latency_seconds": gen_res.latency_seconds,
                        "system_prompt": sys_prompt,
                        "user_prompt": user_content,
                        "source_text": s_text,
                        "output_text": gen_res.text,
                        "extra": gen_res.extra,
                    }

                    # Inline evaluation if requested and generation was successful
                    if run_eval_inline and gen_res.status == "success":
                        scores = evaluate_generation(s_text, gen_res.text)
                        record["metrics"] = scores

                    # Print status
                    if gen_res.status == "success":
                        print(f"✅ OK ({gen_res.latency_seconds:.2f}s, len={len(gen_res.text.split())} words)")
                        num_success += 1
                        save_checkpoint(trial_id, record)
                    elif gen_res.status == "skipped":
                        print(f"⏭️ SKIPPED ({gen_res.error})")
                        num_skipped += 1
                    else:
                        print(f"❌ ERROR ({gen_res.error})")
                        num_errors += 1

                    records.append(record)
                    save_aggregated_results(records)

                    if pace_delay > 0:
                        time.sleep(pace_delay)

    # Save final aggregated results (for dry-run and all completions)
    save_aggregated_results(records)

    print(f"\n======================================================================")
    print(f"📊 BENCHMARK COMPLETE")
    print(f"======================================================================")
    print(f"• Total Processed: {len(records)}")
    print(f"• Successful: {num_success}")
    print(f"• Skipped (no key): {num_skipped}")
    print(f"• Errors: {num_errors}")
    print(f"• Results JSON: {GENERATIONS_JSON}")
    print(f"• Results CSV:  {GENERATIONS_CSV}")
    print(f"======================================================================\n")

    return records


def main():
    parser = argparse.ArgumentParser(description="Run MedSimplify comparative model/prompt benchmark.")
    parser.add_argument("--smoke-test", action="store_true", help="Run 1 sample test across models to verify API connectivity.")
    parser.add_argument("--dry-run", action="store_true", help="Validate prompts and configurations without calling APIs.")
    parser.add_argument("--no-resume", action="store_true", help="Do not load from checkpoints; rerun all trials.")
    parser.add_argument("--eval", action="store_true", help="Run evaluation metrics inline on successful generations.")
    parser.add_argument("--task", type=str, choices=TASKS, help="Filter to a single task.")
    parser.add_argument("--datatype", type=str, choices=DATATYPES, help="Filter to a single datatype.")
    parser.add_argument("--model", type=str, choices=MODELS, help="Filter to a single model.")
    parser.add_argument("--strategy", type=str, choices=STRATEGIES, help="Filter to a single prompt strategy.")
    parser.add_argument("--sample-id", type=str, help="Filter to a specific sample ID (e.g. DS-01, PATH-03).")
    parser.add_argument("--pace-delay", type=float, default=1.0, help="Delay in seconds between API calls to avoid rate limits.")

    args = parser.parse_args()

    tasks = [args.task] if args.task else None
    datatypes = [args.datatype] if args.datatype else None
    models = [args.model] if args.model else None
    strategies = [args.strategy] if args.strategy else None
    sample_ids = [args.sample_id] if args.sample_id else None

    run_benchmark(
        tasks=tasks,
        datatypes=datatypes,
        models=models,
        strategies=strategies,
        sample_ids=sample_ids,
        resume=not args.no_resume,
        dry_run=args.dry_run,
        smoke_test=args.smoke_test,
        run_eval_inline=args.eval,
        pace_delay=args.pace_delay,
    )


if __name__ == "__main__":
    main()

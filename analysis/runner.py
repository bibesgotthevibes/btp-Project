"""
analysis/runner.py
──────────────────
Main CLI runner for comparative experiments across:
- Tasks: summarization, simplification
- Datatypes: discharge, pathology, radiology (5 curated samples each = 15 total)
- Models: cerebras/gptoss, cerebras/qwen3.8, gemini/3.8flash, gemini/3.1pro
- Strategies: zero-shot, few-shot, ner-guided

Features:
- Deterministic trial keys & instant resumability via atomic checkpoints
- Dual JSON and CSV persistence after every step
- Non-blocking error recovery (missing keys or rate-limits are logged gracefully)
- Optional inline or decoupled multi-metric evaluation
- Built-in --smoke-test and --dry-run modes
- Two-stage ner-guided strategy: Stage 1 extracts clinical entities into JSON,
  Stage 2 simplifies with those entities as explicit retention constraints.
  Falls back to zero-shot simplification if NER extraction fails.
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
from analysis.prompts import build_prompt, build_ner_extraction_prompt, build_ner_guided_prompt
from analysis.prompts.json_parser import parse_json_from_llm_response
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


def load_existing_results() -> List[Dict[str, Any]]:
    """Load previously saved generations so filtered runs don't wipe them."""
    if GENERATIONS_JSON.exists():
        try:
            with open(GENERATIONS_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def merge_results(existing: List[Dict[str, Any]], current: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Replace existing records by trial_id with this run's records; append new ones."""
    by_id = {r.get("trial_id"): r for r in current}
    merged = [by_id.pop(r.get("trial_id"), r) for r in existing]
    merged.extend(r for r in current if r.get("trial_id") in by_id)
    return merged


def save_aggregated_results(records: List[Dict[str, Any]]) -> None:
    """Atomically save all trial records to generations.json and generations.csv.
    Merges in-memory records with all available checkpoints in CHECKPOINTS_DIR."""
    # 1. Collect all checkpoints from disk
    all_trials = {}
    if CHECKPOINTS_DIR.exists():
        for ckpt in sorted(CHECKPOINTS_DIR.glob("*.json")):
            try:
                with open(ckpt, "r", encoding="utf-8") as f:
                    cdata = json.load(f)
                    tid = cdata.get("trial_id") or ckpt.stem
                    all_trials[tid] = cdata
            except Exception:
                pass

    # 2. Update with current in-memory records (never overwrite a success checkpoint with dry_run)
    for r in records:
        tid = r.get("trial_id")
        if tid:
            if r.get("status") == "dry_run" and tid in all_trials and all_trials[tid].get("status") == "success":
                continue
            all_trials[tid] = r

    merged_records = list(all_trials.values()) if all_trials else records

    # 3. Write generations.json
    tmp_json = GENERATIONS_JSON.with_suffix(".tmp")
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(merged_records, f, indent=2, ensure_ascii=False)
    tmp_json.replace(GENERATIONS_JSON)

    # 4. Write generations.csv
    if merged_records:
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
            for r in merged_records:
                flat = dict(r)
                src = flat.get("source_text", "")
                out = flat.get("output_text", "")
                flat["source_char_len"] = len(src)
                flat["output_char_len"] = len(out)
                flat["source_snippet"] = src[:120].replace("\n", " ") + "..." if len(src) > 120 else src
                flat["output_snippet"] = out[:120].replace("\n", " ") + "..." if len(out) > 120 else out
                writer.writerow(flat)
        try:
            tmp_csv.replace(GENERATIONS_CSV)
        except PermissionError:
            # e.g. the CSV is open in Excel; generations.json and checkpoints are the source of truth
            print(f"\n  [WARN] {GENERATIONS_CSV.name} is locked by another program; CSV not updated this time")
            tmp_csv.unlink(missing_ok=True)


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
    strict_models: bool = False,
    rerun_substituted: bool = False,
    force_trials: Optional[set] = None,
    reuse_ner: bool = False,
) -> List[Dict[str, Any]]:
    """Execute the benchmark grid across all requested combinations."""
    tasks = tasks or TASKS
    datatypes = datatypes or DATATYPES
    models = models or MODELS
    strategies = strategies or STRATEGIES

    router = ModelRouter(allow_substitute=not strict_models)
    force_trials = force_trials or set()

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
    existing = [] if dry_run else load_existing_results()
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

                    # ── Skip ner-guided for summarization (only simplification supported) ──
                    if strategy == "ner-guided" and task != "simplification":
                        print(f"⏭️ SKIPPED (ner-guided only applies to simplification task)")
                        num_skipped += 1
                        continue

                    # Checkpoint check
                    cached = None
                    if resume and not dry_run:
                        cached = load_checkpoint(trial_id)
                        substituted = bool(cached and (cached.get("extra") or {}).get("fallback_used"))
                        forced = trial_id in force_trials
                        if cached and cached.get("status") == "success" and not (rerun_substituted and substituted) and not forced:
                            print(f"⚡ [CACHED] ({cached.get('latency_seconds', 0)}s)")
                            records.append(cached)
                            num_success += 1
                            continue
                        if not (cached and cached.get("status") == "success"):
                            cached = None
                        else:
                            reason = "forced" if forced else "cached output came from substitute model"
                            print(f"🔁 [RERUN: {reason}] ", end="", flush=True)

                    # ══════════════════════════════════════════════════════════
                    # NER-GUIDED: Two-stage execution
                    # ══════════════════════════════════════════════════════════
                    if strategy == "ner-guided":
                        # ── Stage 1: NER Extraction ────────────────────────
                        ner_sys, ner_user, ner_messages = build_ner_extraction_prompt(dt, s_text)

                        if dry_run:
                            print(f"🔎 [DRY RUN OK — NER Stage 1] (sys_len={len(ner_sys)})")
                            records.append({
                                "trial_id": trial_id, "task": task, "datatype": dt,
                                "sample_id": s_id, "sample_title": s_title,
                                "model": model, "strategy": strategy,
                                "status": "dry_run", "error": None, "provider": "mock",
                                "source_text": s_text, "output_text": "[DRY RUN PLACEHOLDER]",
                                "latency_seconds": 0.0, "ner_extraction_status": "dry_run",
                                "ner_extraction_json": None,
                            })
                            continue

                        ner_reused = bool(
                            reuse_ner and cached
                            and cached.get("ner_extraction_status") == "success"
                            and cached.get("ner_extraction_json")
                        )
                        if ner_reused:
                            # Stage 1 already succeeded for this trial: reuse its entities, skip the call
                            print(f"\n  → Stage 1: reusing saved NER entities (no API call)", end=" ", flush=True)
                            ner_res = GenerationResult(
                                text=cached.get("ner_raw_text") or "",
                                status="success",
                                provider=cached.get("provider", ""),
                                model=cached.get("ner_model_used") or "",
                                total_tokens=cached.get("ner_extraction_tokens"),
                                latency_seconds=cached.get("ner_extraction_latency_seconds") or 0.0,
                            )
                        else:
                            print(f"\n  → Stage 1: NER extraction...", end=" ", flush=True)
                            ner_res = router.generate(
                                model_key=model,
                                system_prompt=ner_sys,
                                user_prompt=ner_user,
                                temperature=0.1,   # Low temp for precise JSON extraction
                                max_tokens=4096,
                            )

                        # Parse the NER JSON response
                        ner_json = None
                        ner_status = "failed"
                        if ner_reused:
                            ner_json = cached["ner_extraction_json"]
                            ner_status = "success"
                        elif ner_res.status == "success":
                            ner_json = parse_json_from_llm_response(ner_res.text)
                            ner_status = "success" if ner_json else "parse_failed"

                        if ner_json:
                            print(f"✅ ({ner_res.latency_seconds:.2f}s, {len(ner_json)} fields)")
                        elif strict_models and ner_res.status != "success":
                            # API failure (quota/overload): don't spend a second call on a
                            # zero-shot stand-in that would be mislabelled as ner-guided.
                            print(f"❌ NER stage API error ({ner_res.error}) → trial left for a later rerun")
                            num_errors += 1
                            if cached:
                                print(f"  ↩ keeping previous (substitute-model) record")
                                records.append(cached)
                            else:
                                records.append({
                                    "trial_id": trial_id, "task": task, "datatype": dt,
                                    "sample_id": s_id, "sample_title": s_title,
                                    "model": model, "strategy": strategy,
                                    "status": "error", "error": f"NER stage: {ner_res.error}",
                                    "provider": ner_res.provider, "source_text": s_text,
                                    "output_text": "", "latency_seconds": round(ner_res.latency_seconds, 3),
                                    "ner_extraction_status": ner_status, "ner_extraction_json": None,
                                })
                            save_aggregated_results(merge_results(existing, records))
                            continue
                        else:
                            print(f"⚠️ NER failed ({ner_res.error or 'parse error'}) → falling back to zero-shot")

                        # ── Stage 2: NER-Guided Simplification ─────────────
                        print(f"  → Stage 2: NER-guided simplification...", end=" ", flush=True)

                        if ner_json:
                            # Use NER-guided prompt with extracted entities
                            sys_prompt, user_content, messages = build_ner_guided_prompt(
                                task=task, datatype=dt, text=s_text, ner_json=ner_json
                            )
                        else:
                            # Fallback: zero-shot simplification if NER failed
                            sys_prompt, user_content, messages = build_prompt(
                                task, dt, "zero-shot", s_text
                            )

                        gen_res: GenerationResult = router.generate(
                            model_key=model,
                            system_prompt=sys_prompt,
                            user_prompt=user_content,
                            temperature=0.2,
                            max_tokens=4096,
                        )

                        # Combine token counts from both stages
                        total_prompt_tokens = (
                            (ner_res.prompt_tokens or 0) + (gen_res.prompt_tokens or 0)
                        )
                        total_completion_tokens = (
                            (ner_res.completion_tokens or 0) + (gen_res.completion_tokens or 0)
                        )
                        total_tokens_combined = (
                            (ner_res.total_tokens or 0) + (gen_res.total_tokens or 0)
                        )
                        total_latency = ner_res.latency_seconds + gen_res.latency_seconds

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
                            "prompt_tokens": total_prompt_tokens,
                            "completion_tokens": total_completion_tokens,
                            "total_tokens": total_tokens_combined,
                            "latency_seconds": round(total_latency, 3),
                            "system_prompt": sys_prompt,
                            "user_prompt": user_content,
                            "source_text": s_text,
                            "output_text": gen_res.text,
                            "model_used": gen_res.model,
                            "extra": gen_res.extra,
                            # NER-specific metadata
                            "ner_extraction_status": ner_status,
                            "ner_extraction_json": ner_json,
                            "ner_model_used": ner_res.model,
                            "ner_reused": ner_reused,
                            "ner_raw_text": ner_res.text,
                            "ner_extraction_latency_seconds": round(ner_res.latency_seconds, 3),
                            "ner_extraction_tokens": ner_res.total_tokens,
                            "ner_fallback_used": ner_json is None,
                        }

                        # Inline evaluation
                        if run_eval_inline and gen_res.status == "success":
                            scores = evaluate_generation(s_text, gen_res.text)
                            record["metrics"] = scores

                        if gen_res.status == "success":
                            fallback_note = " [NER fallback]" if ner_json is None else ""
                            print(f"✅ OK ({gen_res.latency_seconds:.2f}s, {len(gen_res.text.split())} words){fallback_note}")
                            num_success += 1
                            save_checkpoint(trial_id, record)
                        elif gen_res.status == "skipped":
                            print(f"⏭️ SKIPPED ({gen_res.error})")
                            num_skipped += 1
                        else:
                            print(f"❌ ERROR ({gen_res.error})")
                            num_errors += 1

                        if gen_res.status != "success" and cached:
                            print(f"  ↩ keeping previous (substitute-model) record")
                            record = cached
                        records.append(record)
                        save_aggregated_results(merge_results(existing, records))

                        # Pace delay after each NER-guided trial (two API calls already made)
                        if pace_delay > 0:
                            time.sleep(pace_delay)
                        continue

                    # ══════════════════════════════════════════════════════════
                    # STANDARD: zero-shot / few-shot
                    # ══════════════════════════════════════════════════════════

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
                        "model_used": gen_res.model,
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

                    if gen_res.status != "success" and cached:
                        print(f"  ↩ keeping previous record")
                        record = cached
                    records.append(record)
                    save_aggregated_results(merge_results(existing, records))

                    if pace_delay > 0:
                        time.sleep(pace_delay)

    # Save final aggregated results. Dry runs hold only placeholders (and existing=[]),
    # so saving them would overwrite real generations.json/csv.
    if not dry_run:
        save_aggregated_results(merge_results(existing, records))

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


def parse_trial_list(value: str) -> set:
    """'a,b,c' or '@path' (one trial ID per line) -> set of trial IDs."""
    if not value:
        return set()
    if value.startswith("@"):
        lines = Path(value[1:]).read_text(encoding="utf-8").splitlines()
        return {l.strip() for l in lines if l.strip()}
    return {v.strip() for v in value.split(",") if v.strip()}


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
    parser.add_argument("--strict-models", action="store_true", help="Never substitute a different model on quota/overload errors; leave the trial failed for a later rerun.")
    parser.add_argument("--rerun-substituted", action="store_true", help="Rerun cached trials whose output came from a substitute model (keeps the old record if the rerun fails).")
    parser.add_argument("--force-trials", type=str, default="", help="Comma-separated trial IDs (or @file with one per line) to rerun even if cached; the old record is kept if the rerun fails.")
    parser.add_argument("--reuse-ner", action="store_true", help="For forced ner-guided reruns, reuse the saved stage-1 entities when extraction had succeeded (saves one call).")

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
        strict_models=args.strict_models,
        rerun_substituted=args.rerun_substituted,
        force_trials=parse_trial_list(args.force_trials),
        reuse_ner=args.reuse_ner,
    )


if __name__ == "__main__":
    main()

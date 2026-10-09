"""
analysis/run_openi.py
─────────────────────
Reference-based radiology simplification benchmark on Open-i (NLMCXR) reports
paired with LaymanRRG lay references
(datasets/lay_reference_datasets/radiology/openi_lay_pairs.csv).

Uses the chest X-ray prompt variant (RADIOLOGY_CXR_SIMPLIFY_* in prompts/radiology_prompts.py).
Strategies: zero-shot, few-shot (direct) and ner-guided (entity extraction, then the same
chest X-ray prompt with the extracted entities as retention constraints).
Unlike runner.py (curated samples, scored against the source), every output here
is scored against a lay-language ground truth, so SARI / ROUGE / BERTScore are
meaningful. A "reference" row scores the gold lay text itself as a readability
baseline (its overlap scores are trivially perfect; ignore those).

Usage:
  python -m analysis.run_openi                             # 30 reports, all models and strategies
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
from analysis.prompts import build_prompt, build_ner_extraction_prompt
from analysis.prompts.json_parser import parse_json_from_llm_response, ner_json_to_retention_block
from analysis.prompts.radiology_prompts import (
    RADIOLOGY_CXR_NER_GUIDED_SIMPLIFY_SYSTEM_PROMPT,
    RADIOLOGY_CXR_FINDINGS_EXTRACTION_PROMPT,
    RADIOLOGY_CXR_FINDINGS_EXAMPLE,
    RADIOLOGY_CXR_CHECKLIST_SIMPLIFY_SYSTEM_PROMPT,
    RADIOLOGY_CXR_REPAIR_SYSTEM_PROMPT,
)
from analysis.providers import ModelRouter, GenerationResult
from analysis.metrics import evaluate_generation, corpus_chexbert_f1

PAIRS_CSV = DATASETS_DIR / "lay_reference_datasets" / "radiology" / "openi_lay_pairs.csv"
OUT_DIR = RESULTS_DIR / "openi"
OUT_JSON = OUT_DIR / "results.json"
OUT_CSV = OUT_DIR / "results.csv"

SUMMARY_METRICS = ["sari", "rougeL_f1", "bertscore_f1", "sim_reference", "alignscore", "radgraph_f1",
                   "flesch_reading_ease", "flesch_kincaid_grade_level", "dale_chall", "coleman_liau"]


def load_results():
    return json.loads(OUT_JSON.read_text()) if OUT_JSON.exists() else []


def save_results(records):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = OUT_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    tmp.replace(OUT_JSON)
    flat = [{**{k: v for k, v in r.items() if k != "metrics"}, **(r.get("metrics") or {})} for r in records]
    pd.DataFrame(flat).to_csv(OUT_CSV, index=False)


# Improved NER variants (see radiology_prompts.py): A = few-shot + plain checklist, B = check & repair.
NER_VARIANTS = ["ner-fewshot", "ner-repair"]


def _failed(stage, res):
    why = res.error if res.status != "success" else "could not parse findings JSON"
    return GenerationResult(status="error", error=f"{stage}: {why}", provider=res.provider,
                            model=res.model, latency_seconds=res.latency_seconds)


def extract_findings(router, model, src):
    """Stage 1 of the variants: every finding as a plain-English sentence. Returns (res, findings | None)."""
    ex = RADIOLOGY_CXR_FINDINGS_EXAMPLE
    user = (f"Example report:\n{ex['input']}\n\nExample JSON:\n{ex['output']}\n\n"
            f"Extract the findings from this report:\n{src.strip()}")
    res = router.generate(model, RADIOLOGY_CXR_FINDINGS_EXTRACTION_PROMPT, user, temperature=0.1)
    data = parse_json_from_llm_response(res.text) if res.status == "success" else None
    findings = [f for f in (data or {}).get("findings", []) if isinstance(f, dict) and f.get("plain")]
    return res, findings or None


def generate(router, model, strategy, src, draft=None):
    """Returns (GenerationResult, extra fields for the record).
    ner-guided = teammate's entity extraction + chest X-ray prompt with the entity block.
    ner-fewshot / ner-repair: see NER_VARIANTS. ner-repair reuses the saved few-shot output as its draft."""
    if strategy in NER_VARIANTS:
        ext, findings = extract_findings(router, model, src)
        if not findings:
            return _failed("findings stage", ext), {}
        checklist = "\n".join(f"- {f['plain']}" for f in findings)
        extra = {"ner_json": findings}
        if strategy == "ner-fewshot":
            system_prompt = RADIOLOGY_CXR_CHECKLIST_SIMPLIFY_SYSTEM_PROMPT.replace("{checklist}", checklist)
            _, user_prompt, _ = build_prompt("simplification", "radiology_cxr", "few-shot", src)
            res = router.generate(model, system_prompt, user_prompt)
        else:
            if draft is None:
                sp, up, _ = build_prompt("simplification", "radiology_cxr", "few-shot", src)
                d = router.generate(model, sp, up)
                if d.status != "success":
                    return _failed("draft stage", d), extra
                draft = d.text
            user = (f"Original report:\n{src.strip()}\n\nChecklist:\n{checklist}\n\n"
                    f"Draft rewrite:\n{draft.strip()}\n\nFinal text:")
            res = router.generate(model, RADIOLOGY_CXR_REPAIR_SYSTEM_PROMPT, user)
            extra["draft"] = draft
            extra["repaired"] = res.status == "success" and res.text.strip() != draft.strip()
        res.latency_seconds += ext.latency_seconds
        return res, extra

    if strategy != "ner-guided":
        system_prompt, user_prompt, _ = build_prompt("simplification", "radiology_cxr", strategy, src)
        return router.generate(model, system_prompt, user_prompt), {}

    ner_sys, _, msgs = build_ner_extraction_prompt("radiology", src)
    # The shared builder omits the one-shot example because it is a curated test report (RAD-02,
    # brain MRI). Open-i is a different dataset (chest X-ray), so here it is safe to include it.
    ner_user = "\n\n".join([f"Example request:\n{m['content']}" if m["role"] == "user" else f"Example JSON answer:\n{m['content']}"
                             for m in msgs[1:-1]] + [msgs[-1]["content"]])
    ner_res = router.generate(model, ner_sys, ner_user, temperature=0.1)
    ner_json = parse_json_from_llm_response(ner_res.text) if ner_res.status == "success" else None
    if not ner_json:
        # No silent zero-shot fallback: a failed extraction is recorded as a failed trial.
        why = ner_res.error if ner_res.status != "success" else "could not parse entity JSON"
        return GenerationResult(status="error", error=f"NER stage: {why}", provider=ner_res.provider,
                                model=ner_res.model, latency_seconds=ner_res.latency_seconds), {}

    # exam_info left out: the scan is known to be a chest X-ray and the prompt doesn't explain it;
    # small extractors mislabel it ("Chest CT"), which the retention rule would then force in.
    block = ner_json_to_retention_block({k: v for k, v in ner_json.items() if k != "exam_info"}, "radiology")
    system_prompt = RADIOLOGY_CXR_NER_GUIDED_SIMPLIFY_SYSTEM_PROMPT.replace("{ner_retention_block}", block)
    _, user_prompt, _ = build_prompt("simplification", "radiology_cxr", "zero-shot", src)
    res = router.generate(model, system_prompt, user_prompt)
    res.latency_seconds += ner_res.latency_seconds  # report end-to-end latency for both stages
    return res, {"ner_json": ner_json}


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
    if "chexbert_out" in df:  # corpus-level micro-F1 over the 14 CheXpert classes, as BioLaySumm reports it
        table["chexbert_f1"] = df.groupby(groups).apply(lambda g: corpus_chexbert_f1(zip(g.chexbert_out, g.chexbert_ref)))
    print("\n" + table.to_string())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30, help="Number of report pairs to run.")
    ap.add_argument("--split", default="validation", choices=["train", "validation"])
    ap.add_argument("--models", nargs="+", default=MODELS, choices=MODELS)
    ap.add_argument("--strategies", nargs="+", default=STRATEGIES + NER_VARIANTS, choices=STRATEGIES + NER_VARIANTS)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--summary", action="store_true", help="Only print the summary of saved results.")
    ap.add_argument("--rescore", action="store_true", help="Recompute metrics for all saved outputs (no generation).")
    args = ap.parse_args()

    records = load_results()
    if args.summary:
        print_summary(records)
        return
    if args.rescore:
        for i, r in enumerate(records):
            if r["status"] == "success":
                r["metrics"] = evaluate_generation(r["source_text"], r["output_text"], reference_text=r["reference_text"])
            if i % 50 == 0:
                print(f"rescored {i}/{len(records)}", flush=True)
        save_results(records)
        print_summary(records)
        return

    pairs = pd.read_csv(PAIRS_CSV)
    pairs = pairs[pairs.split == args.split]
    pairs = pairs.sample(n=min(args.n, len(pairs)), random_state=args.seed)
    done = {_key(r) for r in records if r["status"] == "success"}
    records = [r for r in records if _key(r) in done]  # drop failed, retry them
    router = ModelRouter(allow_substitute=False)  # never relabel another model's output
    by_key = {_key(r)[:3]: r["output_text"] for r in records if r["status"] == "success"}

    for _, p in pairs.iterrows():
        sid, src, ref = p.nlmcxr_file, p.radiology_report, p.layman_report

        if (sid, "reference", "-") not in done:
            records.append({"sample_id": sid, "model": "reference", "strategy": "-", "status": "success",
                            "source_text": src, "reference_text": ref, "output_text": ref,
                            "metrics": evaluate_generation(src, ref, reference_text=ref)})

        for model, strategy in itertools.product(args.models, args.strategies):
            if (sid, model, strategy) in done:
                continue
            draft = by_key.get((sid, model, "few-shot")) if strategy == "ner-repair" else None
            res, extra = generate(router, model, strategy, src, draft=draft)
            rec = {"sample_id": sid, "model": model, "strategy": strategy, "status": res.status,
                   "error": res.error, "provider": res.provider, "actual_model": res.model, "latency_seconds": round(res.latency_seconds, 2),
                   "source_text": src, "reference_text": ref, "output_text": res.text, "metrics": None, **extra}
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
    ner_failed = sum(1 for r in records if (r.get("error") or "").split(":")[0] in ("NER stage", "findings stage", "draft stage"))
    if ner_failed:
        print(f"\nNER stage failed on {ner_failed} trials (not scored; rerun to retry)")
    print(f"\nSaved: {OUT_JSON}\n       {OUT_CSV}")


if __name__ == "__main__":
    main()

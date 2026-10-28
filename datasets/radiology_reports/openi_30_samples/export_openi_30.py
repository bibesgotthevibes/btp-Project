"""
export_openi_30.py
──────────────────
Extracts the 30 Open-i chest X-ray benchmark reports and their ground-truth
simplified summaries from analysis/results/openi/results.json and exports them
into a 2-column CSV file.

Columns:
  1. report: The original clinical chest X-ray report
  2. simplified_summary: The doctor-curated ground truth lay-language summary
"""

import json
import csv
from pathlib import Path


def extract_30_samples():
    current_dir = Path(__file__).resolve().parent
    repo_root = current_dir.parents[2]
    source_json_path = repo_root / "analysis" / "results" / "openi" / "results.json"
    output_csv_path = current_dir / "openi_30_samples.csv"

    if not source_json_path.exists():
        raise FileNotFoundError(f"Source results JSON not found at: {source_json_path}")

    with open(source_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Filter records with model == "reference" (the ground truth pairs)
    reference_records = [
        r for r in data
        if r.get("model") == "reference" and r.get("source_text") and r.get("reference_text")
    ]

    # Deduplicate by sample_id just in case, preserving order
    seen_ids = set()
    samples = []
    for r in reference_records:
        sid = r.get("sample_id")
        if sid and sid not in seen_ids:
            seen_ids.add(sid)
            samples.append({
                "report": r["source_text"].strip(),
                "": "",
                "simplified_summary": r["reference_text"].strip()
            })

    # If reference records are fewer than 30, also fall back to distinct sample_ids
    if len(samples) < 30:
        for r in data:
            sid = r.get("sample_id")
            if sid and sid not in seen_ids and r.get("source_text") and r.get("reference_text"):
                seen_ids.add(sid)
                samples.append({
                    "report": r["source_text"].strip(),
                    "": "",
                    "simplified_summary": r["reference_text"].strip()
                })
            if len(samples) >= 30:
                break

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["report", "", "simplified_summary"])
        writer.writeheader()
        writer.writerows(samples)

    print(f"Successfully extracted {len(samples)} samples to: {output_csv_path}")
    return output_csv_path


if __name__ == "__main__":
    extract_30_samples()

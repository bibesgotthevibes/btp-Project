"""
analysis/build_viewer.py
────────────────────────
Builds analysis/viewer/index.html: a self-contained page to read each original
report next to every model's simplified version (no server, no API calls).

Inputs : results/evaluations.json, results/content_retention.json
Run    : python analysis/build_viewer.py
"""

import sys
import json
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis.config import RESULTS_DIR, MODEL_ENDPOINTS

TEMPLATE = CURRENT_DIR / "viewer" / "template.html"
OUT_HTML = CURRENT_DIR / "viewer" / "index.html"

MODEL_ORDER = ["gemini/3.8flash", "gemini/3.1pro", "cerebras/gptoss", "cerebras/qwen3.8"]
MODEL_NAMES = {
    "gemini/3.8flash": "Gemini 3.8 Flash",
    "gemini/3.1pro": "Gemini 3.1 Pro",
    "cerebras/gptoss": "GPT-OSS",
    "cerebras/qwen3.8": "Qwen 3.8",
}


def actual_model(r):
    extra = r.get("extra") or {}
    if extra.get("fallback_used"):
        return r.get("model_used") or MODEL_ENDPOINTS[r["model"]]["fallback_models"][0]
    return None


def build_data():
    records = json.load(open(RESULTS_DIR / "evaluations.json", encoding="utf-8"))
    retention = json.load(open(RESULTS_DIR / "content_retention.json", encoding="utf-8"))
    checks = retention["trials"]

    samples = {}
    for r in records:
        if r.get("task") != "simplification":
            continue
        s = samples.setdefault(r["sample_id"], {
            "id": r["sample_id"],
            "type": r["datatype"],
            "title": r.get("sample_title", r["sample_id"]),
            "source": r.get("source_text", ""),
            "outputs": [],
        })
        if not s["source"] and r.get("source_text"):
            s["source"] = r["source_text"]

        c = checks.get(r["trial_id"], {})
        if r.get("status") != "success":
            state = "missing"
        elif c.get("reasoning_leak"):
            state = "leak"
        elif c.get("template_echo"):
            state = "echo"
        elif c.get("truncated") or c.get("incomplete"):
            state = "cut"
        else:
            state = "ok"

        m = r.get("metrics") or {}
        s["outputs"].append({
            "model": r["model"],
            "name": MODEL_NAMES.get(r["model"], r["model"]),
            "ranOn": actual_model(r),
            "strategy": r["strategy"],
            "entities": bool(c.get("uses_entities")),
            "state": state,
            "error": " ".join(str(r.get("error") or "").split())[:180] if state == "missing" else "",
            "text": r.get("output_text") or "",
            "found": c.get("own_found", []),
            "missed": c.get("own_missed", []),
            "words": c.get("out_words"),
            "fkgl": m.get("flesch_kincaid_grade_level"),
            "numbers": c.get("numeric_retention"),
            "coverage": c.get("ref_entity_coverage"),
        })

    order = {"discharge": 0, "pathology": 1, "radiology": 2}
    out = sorted(samples.values(), key=lambda s: (order.get(s["type"], 9), s["id"]))
    for s in out:
        s["outputs"].sort(key=lambda o: (o["strategy"] != "ner-guided", MODEL_ORDER.index(o["model"]) if o["model"] in MODEL_ORDER else 9))
    return out


def main():
    data = build_data()
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/[]", payload)
    OUT_HTML.write_text(html, encoding="utf-8")
    n_out = sum(len(s["outputs"]) for s in data)
    print(f"Wrote {OUT_HTML} ({len(data)} reports, {n_out} model outputs, {OUT_HTML.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()

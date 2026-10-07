"""
analysis/review_form.py
───────────────────────
Doctor review of the Open-i benchmark outputs (results/openi/results.json).

  build:  python -m analysis.review_form build --model cerebras/qwen3.8 --n 15
          -> results/openi/doctor_review.html      (send this single file to the doctor)
             results/openi/doctor_review_key.csv   (version id -> system; keep it, don't send)
  import: python -m analysis.review_form import answers.csv
          -> per-system summary of the doctor's ratings

Per report the doctor sees the original chest X-ray report and three blinded versions:
the model's direct (zero-shot) output, its NER-guided output, and the dataset reference.
Version letters are shuffled per report so the reviewer can't tell which is which.
Questions match build_doctor_pdf.py so both reviews can be compared.

The page saves answers in the browser as the doctor goes and has a
"Download my answers" button that produces the CSV to send back.
"""

import sys
import csv
import json
import random
import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis.run_openi import OUT_DIR, PAIRS_CSV, load_results

OUT_HTML = OUT_DIR / "doctor_review.html"
OUT_KEY = OUT_DIR / "doctor_review_key.csv"

QUESTIONS = [  # (field, label, options) — same as build_doctor_pdf.py
    ("accuracy", "Accuracy", ["No errors", "Minor errors", "Serious errors"]),
    ("invented", "Invented information", ["None", "Yes"]),
    ("missing", "Important information missing", ["None", "Yes"]),
    ("understandable", "Easy for a patient or family to understand (1 = very hard, 5 = very easy)", ["1", "2", "3", "4", "5"]),
    ("suitable", "Could this be given to the patient?", ["As written", "After edits", "No"]),
]


def build(model: str, n: int, seed: int = 42):
    pairs = pd.read_csv(PAIRS_CSV)
    order = list(pairs[pairs.split == "validation"].sample(n=30, random_state=seed).nlmcxr_file)  # benchmark order
    by_key = {(r["sample_id"], r["model"], r["strategy"]): r for r in load_results() if r["status"] == "success"}

    reports, key_rows = [], []
    for sid in order:
        systems = {"direct": by_key.get((sid, model, "zero-shot")),
                   "ner-guided": by_key.get((sid, model, "ner-guided")),
                   "reference": by_key.get((sid, "reference", "-"))}
        if not all(systems.values()):
            continue  # need all three versions to compare
        items = list(systems.items())
        random.Random(f"review-{sid}").shuffle(items)
        versions = []
        for i, (system, r) in enumerate(items):
            letter = "ABC"[i]
            versions.append({"letter": letter, "text": r["output_text"]})
            key_rows.append({"report": sid, "version": letter, "system": system,
                             "model": model if system != "reference" else "LaymanRRG reference"})
        reports.append({"id": sid, "source": r["source_text"], "versions": versions})
        if len(reports) == n:
            break

    if len(reports) < n:
        print(f"Only {len(reports)} reports have all three versions for {model}; using those.")
    payload = json.dumps({"reports": reports, "questions": QUESTIONS}, ensure_ascii=False)
    OUT_HTML.write_text(HTML.replace("__DATA__", payload.replace("</", "<\\/")), encoding="utf-8")
    with open(OUT_KEY, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(key_rows[0]))
        w.writeheader()
        w.writerows(key_rows)
    print(f"Wrote {OUT_HTML} ({len(reports)} reports, {len(key_rows)} versions)\n      {OUT_KEY} (keep; don't send)")


def import_answers(path: str):
    answers = pd.read_csv(path, dtype=str)
    key = pd.read_csv(OUT_KEY, dtype=str)
    df = answers.merge(key, on=["report", "version"], how="left")
    if df.system.isna().any():
        print("WARNING: some answers don't match the key (was the form rebuilt after sending?)")
    df["understandable"] = pd.to_numeric(df.understandable, errors="coerce")
    g = df.groupby("system")
    summary = pd.DataFrame({
        "n": g.size(),
        "serious_errors_%": g.accuracy.apply(lambda s: (s == "Serious errors").mean() * 100),
        "any_error_%": g.accuracy.apply(lambda s: (s != "No errors").mean() * 100),
        "invented_%": g.invented.apply(lambda s: (s == "Yes").mean() * 100),
        "missing_%": g.missing.apply(lambda s: (s == "Yes").mean() * 100),
        "understandable_mean": g.understandable.mean(),
        "usable_as_written_%": g.suitable.apply(lambda s: (s == "As written").mean() * 100),
        "not_usable_%": g.suitable.apply(lambda s: (s == "No").mean() * 100),
    }).round(1)
    print(summary.to_string())
    out = Path(path).with_name(Path(path).stem + "_with_key.csv")
    df.to_csv(out, index=False)
    print(f"\nAnswers joined with the key: {out}")


HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chest X-ray Report Review</title>
<style>
:root{--bg:#f6f8f9;--card:#fff;--ink:#17222b;--muted:#5a6975;--accent:#1d5c73;--on-accent:#fff;--line:#d5dde2;--tint:#eef4f6;--ok:#2e7d4f}
@media (prefers-color-scheme:dark){:root{--bg:#12181c;--card:#1b2329;--ink:#e6ecef;--muted:#9aa8b2;--accent:#7cc0d8;--on-accent:#12181c;--line:#2e3a42;--tint:#22303a;--ok:#6fcf97}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:860px;margin:0 auto;padding:16px}
header{position:sticky;top:0;background:var(--bg);padding:10px 0;border-bottom:1px solid var(--line);z-index:1;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
h1{font-size:1.5rem;margin:.5rem 0}h2{font-size:1.15rem;margin:0 0 .5rem}h3{font-size:1rem;margin:1rem 0 .4rem;color:var(--accent)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:16px 0}
.source{background:var(--tint);border-radius:8px;padding:12px;white-space:pre-wrap}
.version{border-top:1px solid var(--line);margin-top:16px;padding-top:8px}
.text{white-space:pre-wrap}
fieldset{border:0;padding:0;margin:10px 0}legend{font-weight:600;font-size:.95rem;margin-bottom:4px}
.opts{display:flex;flex-wrap:wrap;gap:6px}
.opts label{border:1px solid var(--line);border-radius:999px;padding:6px 12px;cursor:pointer;font-size:.92rem}
.opts input{position:absolute;opacity:0}
.opts input:checked+span{font-weight:600;color:var(--accent)}
.opts label:has(input:checked){border-color:var(--accent);background:var(--tint)}
.opts label:has(input:focus-visible){outline:2px solid var(--accent)}
textarea,input[type=text]{width:100%;font:inherit;color:inherit;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:8px}
button{font:inherit;background:var(--accent);color:var(--on-accent);border:0;border-radius:8px;padding:10px 16px;cursor:pointer}
.muted{color:var(--muted);font-size:.92rem}.done{color:var(--ok);font-weight:600}
</style></head><body><main>
<h1>Chest X-ray report review</h1>
<div class="card">
<p>We are testing whether AI models can rewrite chest X-ray reports into plain language a patient can understand. Each original report below is followed by <b>three plain-language versions (A, B, C)</b> in random order; they don't reveal how they were made, so please judge each on its own.</p>
<p>For each version, check: <b>accuracy</b> (anything wrong or misinterpreted?), <b>invented information</b> (anything not in the original?), <b>missing information</b> (anything clinically important left out?), <b>understandability</b>, and whether it <b>could be given to a patient</b>. Short notes are very helpful.</p>
<p class="muted">The reports are from a public, de-identified research dataset (Open-i); "XXXX" marks text removed during anonymisation. Your answers are saved in this browser as you go, so you can close the page and come back. When finished, press <b>Download my answers</b> and send us the file.</p>
<label for="reviewer"><b>Your name</b></label><input type="text" id="reviewer" autocomplete="name">
</div>
<header><button id="download" type="button">Download my answers</button><span id="progress" class="muted" aria-live="polite"></span></header>
<div id="reports"></div>
</main>
<script>
const DATA = __DATA__;
const STORE = "cxr-review-v1";
let saved = {};
try { saved = JSON.parse(localStorage.getItem(STORE) || "{}"); } catch (e) {}
const persist = () => { try { localStorage.setItem(STORE, JSON.stringify(saved)); } catch (e) {} };
const esc = s => s.replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const root = document.getElementById("reports");

DATA.reports.forEach((r, i) => {
  const card = document.createElement("section");
  card.className = "card";
  let html = `<h2>Report ${i + 1} of ${DATA.reports.length} <span class="muted">(${esc(r.id)})</span></h2>
    <h3>Original report</h3><div class="source">${esc(r.source)}</div>`;
  r.versions.forEach(v => {
    const k = `${r.id}|${v.letter}`;
    html += `<div class="version"><h3>Version ${v.letter}</h3><div class="text">${esc(v.text)}</div>`;
    DATA.questions.forEach(([field, label, opts]) => {
      html += `<fieldset><legend>${esc(label)}</legend><div class="opts">` + opts.map(o =>
        `<label><input type="radio" name="${esc(k)}|${field}" value="${esc(o)}" data-k="${esc(k)}" data-f="${field}"><span>${esc(o)}</span></label>`).join("") + `</div></fieldset>`;
    });
    html += `<label class="muted" for="${esc(k)}|notes">What was done well / what was missed or wrong</label>
      <textarea id="${esc(k)}|notes" rows="2" data-k="${esc(k)}" data-f="notes"></textarea></div>`;
  });
  card.innerHTML = html;
  root.appendChild(card);
});

const reviewer = document.getElementById("reviewer");
reviewer.value = saved._reviewer || "";
reviewer.addEventListener("input", () => { saved._reviewer = reviewer.value; persist(); });

document.querySelectorAll("[data-k]").forEach(el => {
  const val = (saved[el.dataset.k] || {})[el.dataset.f];
  if (el.type === "radio") el.checked = val === el.value; else if (val) el.value = val;
  el.addEventListener(el.type === "radio" ? "change" : "input", () => {
    (saved[el.dataset.k] = saved[el.dataset.k] || {})[el.dataset.f] = el.value;
    persist(); progress();
  });
});

const total = DATA.reports.reduce((n, r) => n + r.versions.length, 0);
function progress() {
  const done = Object.keys(saved).filter(k => k !== "_reviewer" &&
    DATA.questions.every(([f]) => saved[k] && saved[k][f])).length;
  const el = document.getElementById("progress");
  el.textContent = `${done} of ${total} versions fully rated`;
  el.className = done === total ? "done" : "muted";
}
progress();

document.getElementById("download").addEventListener("click", () => {
  const cols = ["reviewer", "report", "version", ...DATA.questions.map(q => q[0]), "notes"];
  const q = s => `"${String(s ?? "").replace(/"/g, '""')}"`;
  const rows = [cols.join(",")];
  DATA.reports.forEach(r => r.versions.forEach(v => {
    const a = saved[`${r.id}|${v.letter}`] || {};
    rows.push([saved._reviewer, r.id, v.letter, ...DATA.questions.map(x => a[x[0]]), a.notes].map(q).join(","));
  }));
  const blob = new Blob([rows.join("\n")], {type: "text/csv"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `cxr_review_${(saved._reviewer || "answers").replace(/\W+/g, "_")}.csv`;
  a.click();
});
</script></body></html>
"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--model", required=True, help="e.g. cerebras/qwen3.8")
    b.add_argument("--n", type=int, default=15)
    i = sub.add_parser("import")
    i.add_argument("answers_csv")
    args = ap.parse_args()
    build(args.model, args.n) if args.cmd == "build" else import_answers(args.answers_csv)

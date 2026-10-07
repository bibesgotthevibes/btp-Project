"""
analysis/content_retention.py
─────────────────────────────
Reference-free content checks on saved simplifications (no API calls).

For every successful simplification in results/evaluations.json it computes:
- numeric_retention      : share of numbers/dates/measurements in the source that
                           reappear in the output (independent of NER)
- ref_entity_coverage    : share of the sample's reference entity list found in the
                           output. The reference list is the union of entities from
                           every successful NER extraction of that sample, so NER and
                           non-NER outputs are scored against the same list.
- own_entity_coverage    : (NER-guided with entities only) share of the model's own
                           extracted entities found in its output — constraint adherence
- missed_entities        : reference entities not found (for review)
- placeholders_kept      : share of {..} / [..] anonymisation placeholders preserved
- person_ok              : correct voice (3rd person for deceased DS-04, 2nd otherwise)
- format_violations      : bullet/heading lines despite the "continuous prose" rule

Writes results/content_retention.json (one entry per trial_id).
"""

import sys
import json
import re
from pathlib import Path
from collections import defaultdict

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from analysis.config import RESULTS_DIR

EVALUATIONS_JSON = RESULTS_DIR / "evaluations.json"
OUT_JSON = RESULTS_DIR / "content_retention.json"

# Keys whose values are model-written explanations or judgements, not source facts
SKIP_KEY = re.compile(
    r"lay|explanation|purpose|severity|chronicity|enhancement|normal_range|^type$|"
    r"gender|outcome|status$|icd|variant|modality|body_region|contrast_used|sequences",
    re.I,
)
STOP = set("""a an the and or of in on at to for with without by from as is are was were be been
this that these those it its into over under up down per not no both left right side sides
due after before during about than then there their his her he she they patient person
""".split())
DECEASED_SAMPLES = {"DS-04"}


def stem(tok: str) -> str:
    return tok[:6]


def content_tokens(text: str):
    toks = re.findall(r"[a-z0-9]+(?:[.,/+][0-9]+)*", text.lower())
    return [t for t in toks if (len(t) >= 3 or t.isdigit() or any(c.isdigit() for c in t)) and t not in STOP]


def numbers_in(text: str):
    """Numbers, dates, ratios and scores as normalised strings (e.g. 26/12/2021, 4+3, 1.5)."""
    t = text.lower().replace(",", ".")
    found = re.findall(r"\d+(?:\s*[./+x×:-]\s*\d+)*(?:\.\d+)?", t)
    out = set()
    for f in found:
        f = re.sub(r"\s+", "", f).replace("×", "x")
        out.add(f)
    return out


def flatten_entities(obj, key=""):
    """Collect fact strings from an NER JSON, skipping model-written explanations."""
    items = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if SKIP_KEY.search(k):
                continue
            items.extend(flatten_entities(v, k))
    elif isinstance(obj, list):
        for v in obj:
            items.extend(flatten_entities(v, key))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        items.append(str(obj))
    elif isinstance(obj, str):
        s = obj.strip()
        if s and s.lower() not in {"null", "none", "not mentioned", "n/a", "absent", "present", "negative", "positive", "unknown"}:
            items.append(s)
    return items


def entity_key(ent: str) -> str:
    return " ".join(stem(t) for t in content_tokens(ent))


def entity_found(ent: str, out_stems: set, out_numbers: set) -> bool:
    toks = content_tokens(ent)
    if not toks:
        return True
    nums = [t for t in toks if any(c.isdigit() for c in t)]
    words = [stem(t) for t in toks if not any(c.isdigit() for c in t)]
    num_ok = all(n.replace(",", ".") in out_numbers or n in out_stems for n in nums)
    if not words:
        return num_ok
    hit = sum(1 for w in words if w in out_stems)
    need = len(words) if len(words) <= 2 else max(2, round(0.6 * len(words)))
    return num_ok and hit >= need


def main():
    records = json.load(open(EVALUATIONS_JSON, encoding="utf-8"))
    simp = [r for r in records if r.get("task") == "simplification" and r.get("status") == "success" and (r.get("output_text") or "").strip()]

    # Reference entity list per sample: union over successful NER extractions, deduplicated
    ref = defaultdict(dict)
    for r in simp:
        if r.get("ner_extraction_status") == "success" and r.get("ner_extraction_json"):
            for e in flatten_entities(r["ner_extraction_json"]):
                k = entity_key(e)
                if k and k not in ref[r["sample_id"]]:
                    ref[r["sample_id"]][k] = e

    results = {}
    for r in simp:
        src, out = r["source_text"], r["output_text"]
        out_toks = content_tokens(out)
        out_stems = {stem(t) for t in out_toks} | set(out_toks)
        out_nums = numbers_in(out)
        src_nums = numbers_in(src)

        entry = {
            "trial_id": r["trial_id"],
            "sample_id": r["sample_id"],
            "datatype": r["datatype"],
            "model": r["model"],
            "strategy": r["strategy"],
            "ner_status": r.get("ner_extraction_status"),
            "uses_entities": r.get("strategy") == "ner-guided" and r.get("ner_extraction_status") == "success",
            "substitute_model": bool((r.get("extra") or {}).get("fallback_used")),
            "src_words": len(src.split()),
            "out_words": len(out.split()),
        }

        entry["numeric_retention"] = round(len(src_nums & out_nums) / len(src_nums), 3) if src_nums else None
        entry["numbers_missing"] = sorted(src_nums - out_nums)
        entry["numbers_added"] = sorted(out_nums - src_nums)

        ref_ents = list(ref.get(r["sample_id"], {}).values())
        if ref_ents:
            found = [e for e in ref_ents if entity_found(e, out_stems, out_nums)]
            entry["ref_entity_coverage"] = round(len(found) / len(ref_ents), 3)
            entry["ref_entities_total"] = len(ref_ents)
            entry["missed_entities"] = [e for e in ref_ents if e not in found]
        else:
            entry["ref_entity_coverage"] = None

        if entry["uses_entities"]:
            own = list({entity_key(e): e for e in flatten_entities(r["ner_extraction_json"]) if entity_key(e)}.values())
            own_found = [e for e in own if entity_found(e, out_stems, out_nums)]
            entry["own_entity_coverage"] = round(len(own_found) / len(own), 3) if own else None
            entry["own_entities_total"] = len(own)
            entry["own_missed"] = [e for e in own if e not in own_found]
            entry["own_found"] = own_found

        src_ph = re.findall(r"\{[a-z_]+\}|\[[a-z_0-9]+\]", src)
        entry["placeholders_kept"] = (
            round(sum(1 for p in set(src_ph) if p in out) / len(set(src_ph)), 3) if src_ph else None
        )

        # Voice rule exists only in the discharge prompts: 3rd person if the patient died, else "you"
        lower = out.lower()
        second = len(re.findall(r"\byou(r|rs)?\b", lower))
        entry["second_person_count"] = second
        if r["datatype"] != "discharge":
            entry["person_ok"] = None
        elif r["sample_id"] in DECEASED_SAMPLES:
            # generic "helps you breathe" is fine; addressing the deceased patient as "your" is not
            entry["person_ok"] = len(re.findall(r"\byour\b", lower)) == 0
        else:
            entry["person_ok"] = second > 0

        # Output cut off mid-sentence (e.g. token budget exhausted)
        entry["truncated"] = not re.search(r"[.!?)\]\"'”]\s*$", out.strip())
        # Model's reasoning trace returned instead of an answer ("We need to produce simplified text...")
        leak_hits = len(re.findall(r"\b(we must|we need to|let's|the user|we should)\b", lower))
        entry["reasoning_leak"] = leak_hits >= 3 or bool(re.match(r"\s*we need to\b", lower))
        # Stopped early at a sentence boundary: far shorter than the source it should cover
        entry["incomplete"] = entry["out_words"] < 0.25 * entry["src_words"]
        # Prompt's entity block copied back instead of prose ("[MILD] ...", "MUST explain all of these", "✓")
        echo_hits = len(re.findall(
            r"\[(?:MILD|MODERATE|SEVERE|NONE|CRITICAL|ABNORMAL|BORDERLINE|ROUTINE|URGENT)\]|\bMUST (?:explain|appear|mention)|✓", out))
        entry["template_echo"] = echo_hits >= 3
        entry["valid_output"] = not (entry["truncated"] or entry["reasoning_leak"] or entry["incomplete"] or entry["template_echo"])

        lines = [l.strip() for l in out.splitlines() if l.strip()]
        entry["format_violations"] = sum(1 for l in lines if re.match(r"^([-*•·]|\d+[.)]|#+)\s", l) or (l.startswith("**") and l.endswith("**")))

        results[r["trial_id"]] = entry

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"reference_entities": {k: list(v.values()) for k, v in ref.items()}, "trials": results}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {OUT_JSON} ({len(results)} trials, reference lists for {len(ref)} samples)")


if __name__ == "__main__":
    main()

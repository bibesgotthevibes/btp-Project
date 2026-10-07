"""
analysis/prompts/json_parser.py
────────────────────────────────
Reusable LLM JSON response parser.
Handles responses from all providers including:
  - Qwen models that wrap output in <think>...</think> reasoning blocks
  - Models that wrap JSON in ```json ... ``` markdown code fences
  - Bare JSON with surrounding whitespace or explanation text

Returns None if parsing completely fails — callers must handle gracefully.
"""

import json
import re
from typing import Optional


def parse_json_from_llm_response(raw_text: str) -> Optional[dict]:
    """
    Parse a JSON object from an LLM response string.

    Tries (in order):
    1. Strip <think>...</think> blocks, then direct parse
    2. Extract from ```json ... ``` code fence
    3. Extract from ``` ... ``` code fence
    4. Regex-extract the first {...} block from cleaned text
    5. Same regex on the original raw text as last resort

    Returns a dict on success, None on complete failure.
    """
    if not raw_text or not raw_text.strip():
        return None

    # ── Step 1: Strip <think>...</think> reasoning blocks (Qwen, DeepSeek etc.) ──
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_text).strip()
    # Also handle unclosed <think> block at the start
    cleaned = re.sub(r"^<think>[\s\S]*", "", cleaned).strip()

    # ── Step 2: Try direct JSON parse on cleaned text ─────────────────────────
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # ── Step 3–5: Pattern-based extraction ───────────────────────────────────
    patterns = [
        r"```json\s*\n([\s\S]*?)\n\s*```",   # ```json ... ```
        r"```\s*\n([\s\S]*?)\n\s*```",         # ``` ... ```
        r"(\{[\s\S]*\})",                        # First {...} block
    ]

    for source in (cleaned, raw_text):
        for pattern in patterns:
            match = re.search(pattern, source)
            if match:
                candidate = match.group(1) if match.lastindex else match.group(0)
                try:
                    result = json.loads(candidate)
                    if isinstance(result, dict):
                        return result
                except (json.JSONDecodeError, ValueError):
                    continue

    return None


# Schema defaults the extractor fills in when the report says nothing. Left in, the
# "MUST retain" rule makes the model state them ("The reason for the test was not mentioned").
_PLACEHOLDERS = {"", "no", "none", "null", "n/a", "na", "unknown", "not mentioned", "not specified",
                 "not stated", "not applicable", "not available", "not reported", "not provided"}


def _drop_placeholders(value):
    """Recursively remove placeholder strings and the empty containers they leave behind."""
    if isinstance(value, dict):
        cleaned = {k: _drop_placeholders(v) for k, v in value.items()}
        return {k: v for k, v in cleaned.items() if v not in (None, "", [], {})}
    if isinstance(value, list):
        cleaned = [_drop_placeholders(v) for v in value]
        return [v for v in cleaned if v not in (None, "", [], {})]
    if isinstance(value, str) and value.strip().lower().rstrip(".") in _PLACEHOLDERS:
        return None
    return value


def ner_json_to_retention_block(ner_data: dict, datatype: str) -> str:
    """
    Convert extracted NER JSON into a human-readable retention constraint block
    to be injected into the simplification system prompt.

    This gives the model a clear, structured list of all entities it MUST
    mention in its simplified output.
    """
    ner_data = _drop_placeholders(ner_data) or {}
    lines = ["=== EXTRACTED CLINICAL ENTITIES — YOU MUST RETAIN ALL OF THESE ==="]

    if datatype == "discharge":
        _format_discharge_retention(ner_data, lines)
    elif datatype == "pathology":
        _format_pathology_retention(ner_data, lines)
    elif datatype == "radiology":
        _format_radiology_retention(ner_data, lines)
    else:
        # Generic fallback: dump as compact JSON
        lines.append(json.dumps(ner_data, indent=2, ensure_ascii=False))

    lines.append("=================================================================")
    lines.append(
        "CRITICAL RETENTION RULE: Every entity, value, measurement, date, "
        "medication name, finding, and recommendation listed above MUST appear "
        "in your simplified output. Do not omit any of them."
    )
    return "\n".join(lines)


# ── Datatype-specific formatters ──────────────────────────────────────────────

def _format_discharge_retention(data: dict, lines: list) -> None:
    demo = data.get("patient_demographics", {})
    if demo.get("age") or demo.get("gender"):
        lines.append(f"Patient: {demo.get('gender', 'unknown')} | Age: {demo.get('age', 'unknown')}")

    diag = data.get("diagnoses", {})
    if diag.get("primary"):
        lines.append(f"Primary Diagnosis: {diag['primary']}")
    for sec in diag.get("secondary", []):
        lines.append(f"  Secondary: {sec}")

    symptoms = data.get("symptoms_at_admission", [])
    if symptoms:
        lines.append("Symptoms at admission: " + "; ".join(symptoms))

    anomalies = data.get("anomalies_detected", [])
    if anomalies:
        lines.append("Anomalies/Findings:")
        for a in anomalies:
            val = f" = {a['value']}" if a.get("value") else ""
            norm = f" (normal: {a['normal_range']})" if a.get("normal_range") else ""
            lines.append(f"  [{a.get('severity','?').upper()}] {a.get('finding','')}{val}{norm}")

    procs = data.get("procedures_performed", [])
    if procs:
        lines.append("Procedures performed:")
        for p in procs:
            date_str = f" on {p['date']}" if p.get("date") else ""
            lines.append(f"  • {p.get('name','')}{date_str}")

    meds = data.get("medications", [])
    if meds:
        lines.append("Medications:")
        for m in meds:
            dosage = f" | Dosage: {m['timing_dosage']}" if m.get("timing_dosage") else ""
            lines.append(f"  • {m.get('name','')} — {m.get('purpose_lay','')}{dosage}")

    warnings = data.get("warning_signs_red_flags", [])
    if warnings:
        lines.append("Warning signs to mention:")
        for w in warnings:
            lines.append(f"  ⚠ {w}")

    followup = data.get("follow_up_care", {})
    for appt in followup.get("appointments", []):
        lines.append(f"Follow-up appointment: {appt}")
    for rx in followup.get("ongoing_treatments", []):
        lines.append(f"Ongoing treatment: {rx}")

    if data.get("stay_duration"):
        lines.append(f"Hospital stay duration: {data['stay_duration']}")
    if data.get("outcome"):
        lines.append(f"Outcome: {data['outcome']}")


def _format_pathology_retention(data: dict, lines: list) -> None:
    spec = data.get("specimen_info", {})
    if spec:
        parts = []
        if spec.get("organ"):
            parts.append(spec["organ"])
        if spec.get("procedure_type"):
            parts.append(spec["procedure_type"])
        if spec.get("weight_grams"):
            parts.append(f"weight {spec['weight_grams']}g")
        if spec.get("dimensions_cm"):
            parts.append(f"dimensions {spec['dimensions_cm']} cm")
        lines.append("Specimen: " + "; ".join(parts))
        for struct in spec.get("associated_structures", []):
            lines.append(f"  Associated structure: {struct}")

    hist = data.get("histologic_diagnosis", {})
    if hist.get("tumor_type"):
        lines.append(f"Histologic diagnosis: {hist['tumor_type']} ({hist.get('distribution', '')})")
    if hist.get("icd_o3_code"):
        lines.append(f"  ICD-O-3: {hist['icd_o3_code']}")

    grade = data.get("grading", {})
    if grade:
        gs_primary = grade.get("gleason_score_primary", "?")
        gs_secondary = grade.get("gleason_score_secondary", "?")
        gs_total = grade.get("gleason_total", "?")
        gs_variant = f" ({grade['gleason_variant']})" if grade.get("gleason_variant") else ""
        isup = grade.get("isup_grade_group", "?")
        pct = grade.get("percent_high_grade_pattern", "")
        lines.append(
            f"Gleason Score: {gs_primary} + {gs_secondary} = {gs_total}{gs_variant} | "
            f"ISUP Grade Group: {isup}"
            + (f" | High-grade pattern: {pct}" if pct else "")
        )

    inv = data.get("invasion_status", {})
    if inv:
        inv_parts = []
        for k, label in [
            ("perineural_invasion", "Perineural invasion"),
            ("lymphovascular_invasion", "Lymphovascular invasion"),
            ("extracapsular_extension", "Extracapsular extension"),
            ("seminal_vesicle_invasion", "Seminal vesicle invasion"),
        ]:
            if inv.get(k) and inv[k] != "not mentioned":
                inv_parts.append(f"{label}: {inv[k]}")
        if inv_parts:
            lines.append("Invasion status: " + "; ".join(inv_parts))

    margins = data.get("margin_status", {})
    if margins.get("resection_status"):
        lines.append(f"Resection status: {margins['resection_status']}")
    for md in margins.get("margin_details", []):
        ext = f" ({md['extent_mm']} mm)" if md.get("extent_mm") else ""
        lines.append(f"  Margin — {md.get('location','')}: {md.get('status','')}{ext}")

    ihc = data.get("ihc_markers", [])
    if ihc:
        lines.append("IHC markers:")
        for marker in ihc:
            lines.append(f"  • {marker.get('marker','')}: {marker.get('result','')} — {marker.get('interpretation','')}")

    for finding in data.get("additional_findings", []):
        lines.append(f"Additional finding: {finding}")


def _format_radiology_retention(data: dict, lines: list) -> None:
    exam = data.get("exam_info", {})
    if exam:
        modality = exam.get("modality", "")
        region = exam.get("body_region", "")
        indication = exam.get("clinical_indication", "")
        contrast = exam.get("contrast_used", "")
        sequences = ", ".join(exam.get("sequences_used", []))
        lines.append(f"Exam: {modality} of {region}")
        if sequences:
            lines.append(f"  Sequences: {sequences}")
        if contrast:
            lines.append(f"  Contrast: {contrast}")
        if indication:
            lines.append(f"  Clinical indication: {indication}")

    normal = data.get("normal_findings", [])
    if normal:
        lines.append("Normal structures (reassure about these):")
        for nf in normal:
            lines.append(f"  ✓ {nf}")

    abnormal = data.get("abnormal_findings", [])
    if abnormal:
        lines.append("Abnormal findings (MUST explain all of these):")
        for af in abnormal:
            chronicity = f" | {af.get('chronicity','')}" if af.get("chronicity") else ""
            enh = f" | {af.get('enhancement','')}" if af.get("enhancement") else ""
            lines.append(
                f"  [{af.get('severity','?').upper()}] {af.get('location','')}: "
                f"{af.get('finding','')}{chronicity}{enh}"
            )

    incidental = data.get("incidental_findings", [])
    if incidental:
        lines.append("Incidental findings:")
        for inf in incidental:
            lines.append(f"  • {inf}")

    measurements = data.get("measurements", [])
    if measurements:
        lines.append("Measurements to include:")
        for m in measurements:
            lines.append(f"  • {m.get('structure','')}: {m.get('value','')} {m.get('unit','')}")

    if data.get("impression"):
        lines.append(f"Radiologist impression: {data['impression']}")

    recs = data.get("recommendations", [])
    if recs:
        lines.append("Recommended follow-up actions (mention all of these):")
        for r in recs:
            urgency = f" [{r.get('urgency','').upper()}]" if r.get("urgency") else ""
            reason = f" — {r['reason']}" if r.get("reason") else ""
            lines.append(f"  → {r.get('action','')}{urgency}{reason}")


if __name__ == "__main__":
    raw = {"exam_info": {"modality": "Chest X-ray", "contrast_used": "no", "clinical_indication": "Not mentioned",
                         "sequences_used": [""]},
           "normal_findings": ["No pneumothorax", "Unknown"], "impression": "None"}
    assert _drop_placeholders(raw) == {"exam_info": {"modality": "Chest X-ray"}, "normal_findings": ["No pneumothorax"]}
    block = ner_json_to_retention_block(raw, "radiology")
    assert "not mentioned" not in block.lower() and "Contrast" not in block and "No pneumothorax" in block, block
    print("json_parser self-check passed")

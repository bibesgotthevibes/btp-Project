"""
schema.py
─────────
JSON schema validation for extracted medical information.
"""

REQUIRED_TOP_LEVEL_KEYS = [
    "patient_demographics",
    "diagnoses",
    "symptoms_at_admission",
    "anomalies_detected",
    "procedures_performed",
    "medications",
    "warning_signs_red_flags",
    "follow_up_care",
    "stay_duration",
    "outcome",
]

REQUIRED_DIAGNOSIS_KEYS = [
    "primary",
    "primary_lay_explanation",
    "secondary",
]

REQUIRED_MEDICATION_KEYS = [
    "name",
    "purpose_lay",
]


def validate_extraction(data: dict) -> tuple[bool, list[str]]:
    """
    Validate that an extracted JSON object contains all required keys.
    Returns (is_valid, list_of_issues).
    """
    issues = []

    if not isinstance(data, dict):
        return False, ["Root element is not a JSON object"]

    # Check top-level keys
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in data:
            issues.append(f"Missing top-level key: '{key}'")

    # Check diagnoses structure
    diag = data.get("diagnoses", {})
    if isinstance(diag, dict):
        for key in REQUIRED_DIAGNOSIS_KEYS:
            if key not in diag:
                issues.append(f"Missing diagnoses key: '{key}'")
    else:
        issues.append("'diagnoses' should be a dict/object")

    # Check medications structure
    meds = data.get("medications", [])
    if isinstance(meds, list):
        for i, med in enumerate(meds):
            if isinstance(med, dict):
                for key in REQUIRED_MEDICATION_KEYS:
                    if key not in med:
                        issues.append(f"Medication [{i}] missing key: '{key}'")
            else:
                issues.append(f"Medication [{i}] is not a dict/object")

    # Check anomalies structure
    anomalies = data.get("anomalies_detected", [])
    if isinstance(anomalies, list):
        for i, anom in enumerate(anomalies):
            if isinstance(anom, dict):
                if "finding" not in anom:
                    issues.append(f"Anomaly [{i}] missing key: 'finding'")
            else:
                issues.append(f"Anomaly [{i}] is not a dict/object")

    is_valid = len(issues) == 0
    return is_valid, issues


def extraction_summary(data: dict) -> dict:
    """
    Generate a quick summary of what was extracted.
    """
    return {
        "has_demographics": bool(data.get("patient_demographics")),
        "primary_diagnosis": data.get("diagnoses", {}).get("primary", "N/A"),
        "num_secondary_diagnoses": len(data.get("diagnoses", {}).get("secondary", [])),
        "num_symptoms": len(data.get("symptoms_at_admission", [])),
        "num_anomalies": len(data.get("anomalies_detected", [])),
        "num_procedures": len(data.get("procedures_performed", [])),
        "num_medications": len(data.get("medications", [])),
        "num_warning_signs": len(data.get("warning_signs_red_flags", [])),
        "outcome": data.get("outcome", "N/A"),
    }

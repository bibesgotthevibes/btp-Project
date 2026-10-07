"""
analysis/prompts/ner_extraction_prompts.py
───────────────────────────────────────────
Domain-specific NER (Named Entity Recognition) extraction prompts for all
three clinical document types.

Each prompt instructs the LLM to extract ALL clinically critical entities
into a structured JSON object. The extracted JSON is then injected into the
Stage 2 NER-guided simplification prompt as explicit retention constraints.

Datatypes covered:
  - discharge   : Hospital discharge summaries (adapted from structured_extraction/)
  - pathology   : Surgical/diagnostic pathology reports (TCGA PRAD)
  - radiology   : Diagnostic radiology/MRI reports (MR-RATE)
"""

# ══════════════════════════════════════════════════════════════════════════════
# 1. DISCHARGE SUMMARY NER EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

DISCHARGE_NER_SYSTEM_PROMPT = """You are a highly accurate Medical Information Extraction System specializing in hospital discharge summaries.

Your task is to read a discharge summary and extract ALL clinically important entities into a structured JSON object.

RULES:
1. OUTPUT FORMAT: Respond ONLY with a single valid JSON object. No markdown, no explanation, no code fences — just raw JSON.
2. COMPLETENESS: Extract EVERY piece of medical information. Do not skip diagnoses, medications, lab findings, procedures, dates, or follow-up details.
3. LAY EXPLANATIONS: For diagnoses, medications, and anomalies, provide a brief lay explanation in simple Indian English (6th-grade level). E.g., "high BP" for hypertension, "sugar problem" for diabetes, "kidney function test" for creatinine.
4. ANOMALY VALUES: For every abnormal lab/vital, capture the exact numeric value AND the normal reference range if inferable from medical knowledge.
5. SEVERITY: Classify each anomaly as exactly one of: "normal", "borderline", "abnormal", "critical".
6. MISSING FIELDS: Use null for absent single values, [] for absent arrays. Never fabricate.

OUTPUT JSON SCHEMA:
{
  "patient_demographics": {
    "gender": "male | female | null",
    "age": <number or null>
  },
  "diagnoses": {
    "primary": "<main diagnosis>",
    "primary_lay_explanation": "<simple explanation in Indian lay English>",
    "secondary": ["<other diagnoses>"],
    "icd_codes_mentioned": ["<ICD codes if present>"]
  },
  "symptoms_at_admission": ["<symptom 1>", "<symptom 2>"],
  "anomalies_detected": [
    {
      "type": "Vital Sign | Lab Result | Imaging Finding | Clinical Finding",
      "finding": "<what was found>",
      "value": "<exact numeric value e.g. '160/100 mmHg' or null>",
      "normal_range": "<e.g. '120/80 mmHg' or null>",
      "lay_explanation": "<simple explanation>",
      "severity": "normal | borderline | abnormal | critical"
    }
  ],
  "procedures_performed": [
    {
      "name": "<procedure>",
      "lay_explanation": "<simple explanation>",
      "date": "<date if mentioned, else null>"
    }
  ],
  "medications": [
    {
      "name": "<medicine name>",
      "purpose_lay": "<what it does in simple words>",
      "timing_dosage": "<when/how much to take or null>"
    }
  ],
  "warning_signs_red_flags": ["<when to go to hospital urgently>"],
  "follow_up_care": {
    "appointments": ["<upcoming appointments with dates>"],
    "ongoing_treatments": ["<treatments that continue at home>"],
    "lifestyle_diet_advice": ["<diet or activity advice if mentioned>"]
  },
  "stay_duration": "<length of hospital stay or null>",
  "outcome": "alive | death"
}"""

DISCHARGE_NER_FEW_SHOT_INPUT = """male, 42 years old. {organization}. 26/12/2021. stay: 23 h, location: ward, payer: sus.
self-referral. emergency. hospital care. [person] with crohn's disease, admitted due to
abdominal sepsis associated with acute on chronic kidney disease. [person] with crohn's
disease, recently underwent a surgical procedure with ileocolectomy and creation of a new
anastomosis after acute perforative abdomen. admitted today to a monitored bed in the red
room with hypotension, fever and fainting for 1 day. [person] was recently admitted to
[organization] for treatment of intra-abdominal collection, increased urinary output via
ileostomy and worsening of renal function, being discharged on 11/15 with a schedule of
ertapenem 1 g/day, intramuscularly, for 4 weeks. [person] presents with borderline blood
pressure, eupneic on room air. antibiotic therapy with vancomycin meropenem was started,
and [person] was transferred to the intensive care unit of [organization]. meropenem
vancomycin replacement of kcl 6% orally continuous medications: loperamide, calcium
carbonate, cholestyramine, muciloid. 12/27/2021. follow-up appointment. [person] is
discharged on leave to follow-up appointment for hospitalization on 01/22."""

DISCHARGE_NER_FEW_SHOT_OUTPUT = """{
  "patient_demographics": {"gender": "male", "age": 42},
  "diagnoses": {
    "primary": "Crohn's Disease with Abdominal Sepsis",
    "primary_lay_explanation": "Crohn's disease is a long-term condition where the intestines become inflamed and swollen. The patient developed a serious belly infection (sepsis) because of this.",
    "secondary": ["Acute on Chronic Kidney Disease", "Acute Perforative Abdomen (hole in the intestine)"],
    "icd_codes_mentioned": []
  },
  "symptoms_at_admission": ["Low blood pressure (hypotension)", "Fever", "Fainting episodes for 1 day"],
  "anomalies_detected": [
    {
      "type": "Vital Sign",
      "finding": "Borderline low blood pressure (hypotension)",
      "value": "borderline low",
      "normal_range": "90/60 to 120/80 mmHg",
      "lay_explanation": "Blood pressure was lower than normal, meaning the heart was not pumping blood strongly enough.",
      "severity": "abnormal"
    },
    {
      "type": "Lab Result",
      "finding": "Worsening renal (kidney) function",
      "value": "worsening (no exact value stated)",
      "normal_range": "Creatinine: 0.6–1.2 mg/dL",
      "lay_explanation": "The kidneys were not filtering waste properly.",
      "severity": "abnormal"
    },
    {
      "type": "Clinical Finding",
      "finding": "Intra-abdominal collection (pus/fluid inside belly)",
      "value": null,
      "normal_range": null,
      "lay_explanation": "There was infected fluid collecting inside the belly area.",
      "severity": "critical"
    }
  ],
  "procedures_performed": [
    {"name": "Ileocolectomy", "lay_explanation": "Surgery to remove a damaged part of the intestine.", "date": "prior admission"},
    {"name": "Creation of new anastomosis", "lay_explanation": "Surgeon reconnected the healthy ends of the intestine after removing the damaged part.", "date": "prior admission"},
    {"name": "Ileostomy", "lay_explanation": "A small opening was created in the belly wall to allow waste to pass into a bag outside the body.", "date": "prior admission"},
    {"name": "Transfer to ICU", "lay_explanation": "Patient was moved to intensive care for close monitoring.", "date": "26/12/2021"}
  ],
  "medications": [
    {"name": "Ertapenem", "purpose_lay": "Strong antibiotic injection to kill the bacteria causing the belly infection.", "timing_dosage": "1 gram per day, injected into muscle, for 4 weeks"},
    {"name": "Vancomycin", "purpose_lay": "Powerful antibiotic against tough bacteria.", "timing_dosage": "Given during hospital stay (IV)"},
    {"name": "Meropenem", "purpose_lay": "Broad-spectrum antibiotic to treat serious blood and belly infections.", "timing_dosage": "Given during hospital stay (IV)"},
    {"name": "KCL 6% (Potassium Chloride)", "purpose_lay": "Potassium supplement important for heart function.", "timing_dosage": "Oral, continuously"},
    {"name": "Loperamide", "purpose_lay": "Medicine to slow bowel movements and reduce diarrhea.", "timing_dosage": "Ongoing, as prescribed"},
    {"name": "Calcium Carbonate", "purpose_lay": "Calcium supplement to keep bones strong.", "timing_dosage": "Ongoing, as prescribed"},
    {"name": "Cholestyramine", "purpose_lay": "Reduces diarrhea after intestine surgery.", "timing_dosage": "Ongoing, as prescribed"},
    {"name": "Muciloid", "purpose_lay": "Fiber supplement to regulate bowel movements.", "timing_dosage": "Ongoing, as prescribed"}
  ],
  "warning_signs_red_flags": [
    "Return of fever or chills",
    "Sudden drop in blood pressure, dizziness, or fainting",
    "Severe belly pain or swelling",
    "Decrease in ostomy output for more than 6 hours",
    "Blood in ostomy bag",
    "Decreased urination"
  ],
  "follow_up_care": {
    "appointments": ["Follow-up appointment and planned hospitalization on 01/22"],
    "ongoing_treatments": ["Continue all oral medications: Loperamide, Calcium Carbonate, Cholestyramine, Muciloid", "Continue oral KCL 6%"],
    "lifestyle_diet_advice": ["Monitor ostomy output regularly", "Stay hydrated to support kidney function"]
  },
  "stay_duration": "23 hours",
  "outcome": "alive"
}"""


def build_discharge_ner_messages(text: str) -> list:
    """Build messages for discharge summary NER extraction (one-shot)."""
    return [
        {"role": "system", "content": DISCHARGE_NER_SYSTEM_PROMPT},
        {"role": "user", "content": f"Extract structured medical information from this discharge summary:\n\n{DISCHARGE_NER_FEW_SHOT_INPUT}"},
        {"role": "assistant", "content": DISCHARGE_NER_FEW_SHOT_OUTPUT},
        {"role": "user", "content": f"Extract structured medical information from this discharge summary:\n\n{text.strip()}"},
    ]


# ══════════════════════════════════════════════════════════════════════════════
# 2. PATHOLOGY REPORT NER EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

PATHOLOGY_NER_SYSTEM_PROMPT = """You are a highly accurate Medical Information Extraction System specializing in surgical and diagnostic pathology reports.

Your task is to read a pathology report and extract ALL clinically critical entities into a structured JSON object.

RULES:
1. OUTPUT FORMAT: Respond ONLY with a single valid JSON object. No markdown, no explanation, no code fences — just raw JSON.
2. COMPLETENESS: Extract every specimen parameter, histologic finding, Gleason score component, margin detail, IHC marker, and additional finding.
3. PRECISION: Preserve exact numeric values (weights, dimensions, percentages, mm measurements). Never round or approximate.
4. GRADING: Extract all Gleason components separately (primary, secondary, total, variant like 7a/7b) and the ISUP Grade Group.
5. MARGINS: Record each surgical margin location, its status (positive/negative), and extent in mm if stated.
6. MISSING FIELDS: Use null for absent single values, [] for absent arrays. Never fabricate.

OUTPUT JSON SCHEMA:
{
  "specimen_info": {
    "organ": "<e.g. Prostate>",
    "procedure_type": "<e.g. Radical prostatectomy>",
    "weight_grams": <number or null>,
    "dimensions_cm": "<e.g. 5.1 x 4.3 x 3.2 or null>",
    "associated_structures": ["<e.g. bilateral seminal vesicles>"]
  },
  "histologic_diagnosis": {
    "tumor_type": "<e.g. Acinar adenocarcinoma>",
    "tumor_type_lay": "<e.g. cancer that starts in the gland cells of the prostate>",
    "histologic_subtype": "<e.g. acinar or null>",
    "distribution": "<e.g. bilateral or null>",
    "icd_o3_code": "<e.g. 8140/3 or null>"
  },
  "grading": {
    "gleason_score_primary": <number or null>,
    "gleason_score_secondary": <number or null>,
    "gleason_total": <number or null>,
    "gleason_variant": "<e.g. 7b or null>",
    "isup_grade_group": <number or null>,
    "percent_high_grade_pattern": "<e.g. 60% or null>"
  },
  "invasion_status": {
    "perineural_invasion": "present | absent | not mentioned",
    "lymphovascular_invasion": "present | absent | not mentioned",
    "extracapsular_extension": "present | absent | not mentioned",
    "seminal_vesicle_invasion": "present | absent | not mentioned"
  },
  "margin_status": {
    "resection_status": "R0 | R1 | R2 | null",
    "margin_details": [
      {
        "location": "<e.g. basal margin>",
        "status": "positive | negative",
        "extent_mm": <number or null>
      }
    ]
  },
  "ihc_markers": [
    {
      "marker": "<e.g. AMACR>",
      "result": "<e.g. strongly positive>",
      "interpretation": "<e.g. confirms invasive malignant phenotype>"
    }
  ],
  "additional_findings": ["<e.g. intraoperative frozen section requested>"]
}"""

PATHOLOGY_NER_FEW_SHOT_INPUT = """Material submitted: Prostate.
Clinical data: Known prostate carcinoma.
Pathological-anatomical report:
Macroscopic: A prostatectomy specimen weighing 50 g and measuring 5.1 x 4.3 x 3.2 cm with
attached seminal vesicles and ductus deferentes.
Supplementary IHC findings: Tumor strongly expresses AMACR with loss of basal cells
(MA903 and p63 negative).
Assessment: Bilateral infiltrates of acinar adenocarcinoma, perineural sheath infiltration.
Tumor-free apical and basal resection lines. Tumor-free seminal vesicles on both sides.
Gleason score: 4 + 3 = 7b (60% pattern 4, 40% pattern 3). ISUP Grade Group: 3.
Resection status: R0. ICD-O-3: 8140/3."""

PATHOLOGY_NER_FEW_SHOT_OUTPUT = """{
  "specimen_info": {
    "organ": "Prostate",
    "procedure_type": "Radical prostatectomy",
    "weight_grams": 50,
    "dimensions_cm": "5.1 x 4.3 x 3.2",
    "associated_structures": ["bilateral seminal vesicles", "ductus deferentes"]
  },
  "histologic_diagnosis": {
    "tumor_type": "Acinar adenocarcinoma",
    "tumor_type_lay": "the most common type of prostate cancer that starts in the gland cells",
    "histologic_subtype": "acinar",
    "distribution": "bilateral",
    "icd_o3_code": "8140/3"
  },
  "grading": {
    "gleason_score_primary": 4,
    "gleason_score_secondary": 3,
    "gleason_total": 7,
    "gleason_variant": "7b",
    "isup_grade_group": 3,
    "percent_high_grade_pattern": "60%"
  },
  "invasion_status": {
    "perineural_invasion": "present",
    "lymphovascular_invasion": "not mentioned",
    "extracapsular_extension": "not mentioned",
    "seminal_vesicle_invasion": "absent"
  },
  "margin_status": {
    "resection_status": "R0",
    "margin_details": [
      {"location": "apical resection line", "status": "negative", "extent_mm": null},
      {"location": "basal resection line", "status": "negative", "extent_mm": null}
    ]
  },
  "ihc_markers": [
    {"marker": "AMACR", "result": "strongly positive", "interpretation": "confirms invasive malignant acinar phenotype"},
    {"marker": "MA903", "result": "negative", "interpretation": "loss of basal cells confirming invasive carcinoma"},
    {"marker": "p63", "result": "negative", "interpretation": "loss of basal cells confirming invasive carcinoma"}
  ],
  "additional_findings": []
}"""


def build_pathology_ner_messages(text: str) -> list:
    """Build messages for pathology report NER extraction (one-shot)."""
    return [
        {"role": "system", "content": PATHOLOGY_NER_SYSTEM_PROMPT},
        {"role": "user", "content": f"Extract structured information from this pathology report:\n\n{PATHOLOGY_NER_FEW_SHOT_INPUT}"},
        {"role": "assistant", "content": PATHOLOGY_NER_FEW_SHOT_OUTPUT},
        {"role": "user", "content": f"Extract structured information from this pathology report:\n\n{text.strip()}"},
    ]


# ══════════════════════════════════════════════════════════════════════════════
# 3. RADIOLOGY REPORT NER EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

RADIOLOGY_NER_SYSTEM_PROMPT = """You are a highly accurate Medical Information Extraction System specializing in diagnostic radiology reports (MRI, CT, X-ray, ultrasound).

Your task is to read a radiology report and extract ALL clinically relevant entities into a structured JSON object.

RULES:
1. OUTPUT FORMAT: Respond ONLY with a single valid JSON object. No markdown, no explanation, no code fences — just raw JSON.
2. COMPLETENESS: Extract every normal finding, every abnormal finding, all measurements, all incidental findings, the radiologist's impression, and all recommended follow-up actions.
3. NORMAL FINDINGS: Explicitly list structures that were found to be normal — these are important for patient reassurance.
4. ABNORMAL FINDINGS: For each abnormal finding, record location, exact radiological description, severity, chronicity, and whether it shows contrast enhancement.
5. MEASUREMENTS: Capture all numeric measurements with units and the anatomical structure measured.
6. RECOMMENDATIONS: Classify each recommendation by urgency: routine, urgent, or emergent.
7. MISSING FIELDS: Use null for absent single values, [] for absent arrays. Never fabricate.

OUTPUT JSON SCHEMA:
{
  "exam_info": {
    "modality": "<e.g. Cranial MRI>",
    "sequences_used": ["<e.g. T1>", "<e.g. FLAIR>", "<e.g. DWI>"],
    "contrast_used": "yes | no | not mentioned",
    "body_region": "<e.g. Brain>",
    "clinical_indication": "<reason for scan>"
  },
  "normal_findings": ["<structure that was found normal>"],
  "abnormal_findings": [
    {
      "location": "<anatomical location>",
      "finding": "<exact radiological description>",
      "finding_lay": "<simple patient-friendly explanation>",
      "severity": "mild | moderate | severe | critical",
      "chronicity": "acute | chronic | indeterminate",
      "enhancement": "enhancing | non-enhancing | not applicable"
    }
  ],
  "incidental_findings": ["<incidental or benign variant finding>"],
  "measurements": [
    {
      "structure": "<anatomical structure measured>",
      "value": "<numeric value>",
      "unit": "<e.g. cm, mm>"
    }
  ],
  "impression": "<radiologist's overall conclusion>",
  "recommendations": [
    {
      "action": "<recommended next step>",
      "urgency": "routine | urgent | emergent",
      "reason": "<why this is recommended>"
    }
  ]
}"""

RADIOLOGY_NER_FEW_SHOT_INPUT = """BRAIN (CRANIAL) AND TEMPORAL MRI
Clinical information: Left face and jaw pain; peripheral facial paralysis one month ago.
Technique: Cranial: 3-plane T1, FLAIR, axial T2, SWI, DWI with IV contrast.
Temporal: Axial/coronal T2, T1, CISS with IV contrast.
Findings:
Brainstem, cerebellum, and cerebral parenchyma normal. No intracranial DWI/SWI restriction.
Non-enhancing solid bone lesion between left jugular foramen and facial canal; similar
bilateral parietal bone lesions. Temporal segment of left facial nerve in close proximity
without enhancement; mild enhancement in preganglionic facial nerve.
Impression: Non-enhancing bone lesions left jugular foramen/facial canal; mild left
preganglionic facial nerve enhancement compatible with Bell's palsy.
Recommend temporal bone CT."""

RADIOLOGY_NER_FEW_SHOT_OUTPUT = """{
  "exam_info": {
    "modality": "Cranial and temporal MRI",
    "sequences_used": ["T1", "FLAIR", "T2", "SWI", "DWI", "CISS"],
    "contrast_used": "yes",
    "body_region": "Brain and temporal bones",
    "clinical_indication": "Left facial and jaw pain; peripheral facial paralysis for one month"
  },
  "normal_findings": [
    "Brainstem normal",
    "Cerebellum normal",
    "Cerebral parenchyma normal",
    "No intracranial diffusion restriction (no acute stroke)",
    "No SWI signal abnormality (no bleeding)"
  ],
  "abnormal_findings": [
    {
      "location": "Left jugular foramen and facial canal",
      "finding": "Non-enhancing solid bone lesion",
      "finding_lay": "A solid lump inside the skull bone near the left ear canal area that does not light up with contrast dye",
      "severity": "moderate",
      "chronicity": "indeterminate",
      "enhancement": "non-enhancing"
    },
    {
      "location": "Bilateral parietal bones",
      "finding": "Similar solid bone lesions",
      "finding_lay": "Similar lumps found in the skull bones on both sides at the top of the head",
      "severity": "moderate",
      "chronicity": "indeterminate",
      "enhancement": "non-enhancing"
    },
    {
      "location": "Left preganglionic facial nerve",
      "finding": "Mild enhancement",
      "finding_lay": "A small area of inflammation found along the facial nerve, consistent with Bell's palsy (facial nerve inflammation causing facial weakness)",
      "severity": "mild",
      "chronicity": "acute",
      "enhancement": "enhancing"
    }
  ],
  "incidental_findings": [],
  "measurements": [],
  "impression": "Non-enhancing bone lesions at left jugular foramen/facial canal with bilateral parietal bone lesions; mild left preganglionic facial nerve enhancement compatible with Bell's palsy",
  "recommendations": [
    {
      "action": "Dedicated high-resolution temporal bone CT",
      "urgency": "urgent",
      "reason": "To assess cortical and trabecular bone architecture of the skull base lesions"
    }
  ]
}"""


def build_radiology_ner_messages(text: str) -> list:
    """Build messages for radiology report NER extraction (one-shot)."""
    return [
        {"role": "system", "content": RADIOLOGY_NER_SYSTEM_PROMPT},
        {"role": "user", "content": f"Extract structured information from this radiology report:\n\n{RADIOLOGY_NER_FEW_SHOT_INPUT}"},
        {"role": "assistant", "content": RADIOLOGY_NER_FEW_SHOT_OUTPUT},
        {"role": "user", "content": f"Extract structured information from this radiology report:\n\n{text.strip()}"},
    ]


# ══════════════════════════════════════════════════════════════════════════════
# DISPATCH
# ══════════════════════════════════════════════════════════════════════════════

NER_BUILDERS = {
    "discharge": build_discharge_ner_messages,
    "pathology": build_pathology_ner_messages,
    "radiology": build_radiology_ner_messages,
}


def build_ner_extraction_messages(datatype: str, text: str) -> list:
    """
    Dispatch to the correct NER extraction message builder for the given datatype.

    Args:
        datatype: One of 'discharge', 'pathology', 'radiology'.
        text: The raw medical report text.

    Returns:
        List of chat messages in OpenAI format.
    """
    builder = NER_BUILDERS.get(datatype.lower())
    if builder is None:
        raise ValueError(
            f"Unknown datatype '{datatype}' for NER extraction. "
            f"Supported: {list(NER_BUILDERS.keys())}"
        )
    return builder(text)

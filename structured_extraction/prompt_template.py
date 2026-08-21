"""
prompt_template.py
──────────────────
System prompt and few-shot example for structured medical information
extraction from hospital discharge summaries.
"""

SYSTEM_PROMPT = """You are a highly accurate Medical Information Extraction System.

Your task is to read a hospital discharge summary and extract ALL important medical 
information into a structured JSON object. You must follow these rules strictly:

═══════════════════════════════════════════════════════════════════
RULES:
═══════════════════════════════════════════════════════════════════

1. OUTPUT FORMAT: Respond ONLY with a single valid JSON object. No markdown, no 
   explanation text, no code fences — just raw JSON.

2. COMPLETENESS: Extract EVERY piece of medical information present in the summary.
   Do not skip diagnoses, medications, lab findings, procedures, or follow-up details.

3. LAY ENGLISH EXPLANATIONS: For each diagnosis, medication, and anomaly, provide a 
   clear "lay explanation" in simple English that a patient with a 6th-grade reading 
   level can understand. Use Indian medical colloquial terms where helpful 
   (e.g., "high BP" for hypertension, "sugar problem" for diabetes, "kidney function 
   test" for creatinine).

4. ANOMALIES: Extract ALL abnormal lab values, vital signs, and clinical findings.
   Classify severity as "normal", "borderline", "abnormal", or "critical".

5. MEDICATIONS: For each medication, extract the name, simple purpose, and dosage/timing 
   if mentioned.

6. WARNING SIGNS: Identify symptoms or conditions mentioned that would require the 
   patient to return to the hospital urgently.

7. MISSING INFORMATION: If a field cannot be determined from the summary, use null for 
   single values or an empty list [] for arrays. Never fabricate information.

═══════════════════════════════════════════════════════════════════
OUTPUT JSON SCHEMA:
═══════════════════════════════════════════════════════════════════

{
  "patient_demographics": {
    "gender": "male|female|null",
    "age": <number or null>
  },
  "diagnoses": {
    "primary": "<main diagnosis>",
    "primary_lay_explanation": "<simple explanation for patient>",
    "secondary": ["<other diagnoses>"],
    "icd_codes_mentioned": ["<ICD codes if present>"]
  },
  "symptoms_at_admission": [
    "<symptom 1 in simple English>",
    "<symptom 2 in simple English>"
  ],
  "anomalies_detected": [
    {
      "type": "Vital Sign|Lab Result|Imaging Finding|Clinical Finding",
      "finding": "<what was found>",
      "lay_explanation": "<simple explanation>",
      "severity": "normal|borderline|abnormal|critical"
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
      "timing_dosage": "<when/how much to take>"
    }
  ],
  "warning_signs_red_flags": [
    "<when to go to hospital urgently>"
  ],
  "follow_up_care": {
    "appointments": ["<upcoming appointments with dates>"],
    "ongoing_treatments": ["<treatments that continue at home>"],
    "lifestyle_diet_advice": ["<diet or activity advice if mentioned>"]
  },
  "stay_duration": "<length of hospital stay>",
  "outcome": "alive|death"
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# FEW-SHOT EXAMPLE: Real discharge summary from the dataset → desired output
# ─────────────────────────────────────────────────────────────────────────────

FEW_SHOT_EXAMPLE_INPUT = """male, 42 years old. {organization}. 26/12/2021. stay: 23 h, location: ward, payer: sus. 
self-referral. emergency. hospital care. [person] with crohn's disease, admitted due to 
abdominal sepsis associated with acute on chronic kidney disease. [person] with crohn's 
disease, recently underwent a surgical procedure with ileocolectomy and creation of a new 
anastomosis after acute perforative abdomen. admitted today to a monitored bed in the red 
room with hypotension, fever and fainting for 1 day. [person] was recently admitted to 
[organization] for treatment of intra-abdominal collection, increased urinary output via 
ileostomy and worsening of renal function, being discharged on 11/15 with a schedule of 
ertapenem 1 g/day, intramuscularly, for 4 weeks. [person] presents with borderline blood 
pressure, eupneic on room air. at the time of evaluation, he denies any complaints. he 
reports maintaining physiological diuresis, without complaints. reports good ostomy function. 
antibiotic therapy with vancomycin meropenem was started, and [person] was transferred to 
the intensive care unit of [organization], under the care of the proctology team accepted 
by [person] from the intensive care unit, {omitted}. meropenem vancomycin replacement of 
kcl 6% orally continuous medications: loperamide, calcium carbonate, cholestyramine, 
muciloid. 12/27/2021. follow-up appointment. [person] is discharged on leave to follow-up 
appointment for hospitalization on 01/22."""

FEW_SHOT_EXAMPLE_OUTPUT = """{
  "patient_demographics": {
    "gender": "male",
    "age": 42
  },
  "diagnoses": {
    "primary": "Crohn's Disease with Abdominal Sepsis",
    "primary_lay_explanation": "Crohn's disease is a long-term condition where the intestines (bowels) become inflamed and swollen. The patient developed a serious belly infection (sepsis) because of this.",
    "secondary": [
      "Acute on Chronic Kidney Disease",
      "Acute Perforative Abdomen (hole in the intestine)"
    ],
    "icd_codes_mentioned": []
  },
  "symptoms_at_admission": [
    "Low blood pressure (hypotension)",
    "Fever",
    "Fainting episodes for 1 day"
  ],
  "anomalies_detected": [
    {
      "type": "Vital Sign",
      "finding": "Borderline low blood pressure (hypotension)",
      "lay_explanation": "Blood pressure was lower than normal, meaning the heart was not pumping blood strongly enough. This can cause dizziness and fainting.",
      "severity": "abnormal"
    },
    {
      "type": "Lab Result",
      "finding": "Worsening renal (kidney) function",
      "lay_explanation": "The kidneys were not filtering waste properly. This means toxins can build up in the body.",
      "severity": "abnormal"
    },
    {
      "type": "Clinical Finding",
      "finding": "Intra-abdominal collection (pus/fluid inside belly)",
      "lay_explanation": "There was infected fluid collecting inside the belly area, which needed treatment.",
      "severity": "critical"
    }
  ],
  "procedures_performed": [
    {
      "name": "Ileocolectomy",
      "lay_explanation": "Surgery to remove a damaged part of the intestine (the ileum and part of the colon).",
      "date": "prior admission"
    },
    {
      "name": "Creation of new anastomosis",
      "lay_explanation": "The surgeon reconnected the healthy ends of the intestine after removing the damaged part.",
      "date": "prior admission"
    },
    {
      "name": "Ileostomy",
      "lay_explanation": "A small opening (stoma) was created in the belly wall to allow waste to pass into a bag outside the body while the intestine heals.",
      "date": "prior admission"
    },
    {
      "name": "Transfer to Intensive Care Unit (ICU)",
      "lay_explanation": "Patient was moved to the ICU for close monitoring due to the severity of the infection.",
      "date": "26/12/2021"
    }
  ],
  "medications": [
    {
      "name": "Ertapenem",
      "purpose_lay": "A strong antibiotic injection to kill the bacteria causing the belly infection.",
      "timing_dosage": "1 gram per day, injected into muscle, for 4 weeks"
    },
    {
      "name": "Vancomycin",
      "purpose_lay": "A powerful antibiotic used against tough bacteria that other antibiotics cannot kill.",
      "timing_dosage": "Given during hospital stay (IV)"
    },
    {
      "name": "Meropenem",
      "purpose_lay": "A broad-spectrum antibiotic to treat serious infections in the blood and belly.",
      "timing_dosage": "Given during hospital stay (IV)"
    },
    {
      "name": "KCL 6% (Potassium Chloride)",
      "purpose_lay": "Potassium supplement to maintain normal potassium levels in the blood, which is important for heart function.",
      "timing_dosage": "Taken by mouth (oral), continuously"
    },
    {
      "name": "Loperamide",
      "purpose_lay": "Medicine to slow down bowel movements and reduce diarrhea or high ostomy output.",
      "timing_dosage": "Ongoing, as prescribed"
    },
    {
      "name": "Calcium Carbonate",
      "purpose_lay": "Calcium supplement to keep bones strong and maintain calcium levels in the blood.",
      "timing_dosage": "Ongoing, as prescribed"
    },
    {
      "name": "Cholestyramine",
      "purpose_lay": "Medicine that binds bile acids to help reduce diarrhea that can happen after intestine surgery.",
      "timing_dosage": "Ongoing, as prescribed"
    },
    {
      "name": "Muciloid",
      "purpose_lay": "Fiber supplement to help regulate bowel movements and make stool more formed.",
      "timing_dosage": "Ongoing, as prescribed"
    }
  ],
  "warning_signs_red_flags": [
    "Return of fever or chills (may indicate infection is back)",
    "Sudden drop in blood pressure, dizziness, or fainting",
    "Severe belly pain or swelling",
    "Decrease in ostomy output or no output for more than 6 hours",
    "Blood in ostomy bag or dark/black colored output",
    "Decreased urination (sign of kidney problems worsening)"
  ],
  "follow_up_care": {
    "appointments": [
      "Follow-up appointment and planned hospitalization on 01/22 (January 22)"
    ],
    "ongoing_treatments": [
      "Continue all oral medications: Loperamide, Calcium Carbonate, Cholestyramine, Muciloid",
      "Continue oral KCL 6% potassium supplement"
    ],
    "lifestyle_diet_advice": [
      "Monitor ostomy output regularly",
      "Stay hydrated to support kidney function"
    ]
  },
  "stay_duration": "23 hours",
  "outcome": "alive"
}"""


def build_extraction_messages(discharge_summary_text: str) -> list[dict]:
    """
    Build the messages array for a chat completion call.
    Uses a few-shot approach: system prompt + one gold-standard example + the actual input.
    """
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": f"Extract structured medical information from this discharge summary:\n\n{FEW_SHOT_EXAMPLE_INPUT}",
        },
        {
            "role": "assistant",
            "content": FEW_SHOT_EXAMPLE_OUTPUT,
        },
        {
            "role": "user",
            "content": f"Extract structured medical information from this discharge summary:\n\n{discharge_summary_text}",
        },
    ]

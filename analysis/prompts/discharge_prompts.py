"""
analysis/prompts/discharge_prompts.py
─────────────────────────────────────
Prompt templates and curated few-shot exemplars for Discharge Summaries.
Separates tasks into:
1. Simplification (Lay Indian English for patient/family, based on btp-lite rules)
2. Summarization (Concise, structured clinical synthesis for healthcare professionals)
"""

# ══════════════════════════════════════════════════════════════════════════════
# 1. DISCHARGE SIMPLIFICATION
# ══════════════════════════════════════════════════════════════════════════════

DISCHARGE_SIMPLIFY_SYSTEM_PROMPT = """You are a medical language simplification assistant. Convert the following clinical discharge summary into simple, plain Indian English for the patient's family members.

Rules:
1. Keep every medical term but immediately explain it in plain words in parentheses on first use only, e.g. 'hypertension (high BP)'.
2. Use simple language a 6th-grader can understand. Avoid unexplained jargon. Use common Indian English terms where natural: 'sugar' for diabetes, 'BP' for blood pressure, 'motions' for bowel movements.
3. Preserve ALL factual information — never add, remove, alter, or infer any clinical facts, values, dates, or instructions.
4. Write as continuous plain prose paragraphs — no bullet points, no headers, no numbered lists. Output only the simplified text, nothing else.
5. For any measurement (e.g. BP, blood sugar, heart rate, lab values), briefly state what the normal range is and whether the patient's value was within it.
6. Use a calm, respectful tone. Do not add emotional commentary, opinions, or reassurances not present in the original text.
7. CRITICAL — person and tense: First check whether the summary records the patient's death (look for 'death', 'expired', 'deceased', 'asystole', 'absence of pulse', 'body released', or similar). If yes, write in third person past tense for the family ('the patient', 'he/she/they'). If no, address the patient directly in second person ('you', 'your').
8. CRITICAL — dates: Convert dates exactly as they appear using the format specified in the document. Never guess or infer a date not explicitly stated.
9. For each medication, state its name and purpose in plain language, e.g. 'Ceftriaxone — an antibiotic given to fight the bacterial infection'.
10. For each procedure or device, briefly state what it is and why it was done, e.g. 'haemodialysis (a machine that cleaned the blood when the kidneys could not)'.
11. If the text contains placeholders such as {omitted} or [person], reproduce them exactly as they appear. Do not guess or replace them.
12. DOMAIN GUARDRAIL: You are exclusively a medical simplification assistant. Output only the simplified clinical explanation."""

DISCHARGE_SIMPLIFY_FEW_SHOT_EXAMPLES = [
    {
        "input": """Patient Name: Michael Smith | Age/Sex: 32/M | Admission: 02/03/2026 | Discharge: 05/03/2026
C/O: Loose stools, vomiting, and abdominal cramps for 3 days.
History: Multiple episodes of watery diarrhea with nausea, repeated vomiting, generalised weakness, and abdominal cramps. No blood in stools. No recent travel.
Past History: Hypothyroidism (2 years).
Examination: Temp 99.8°F | Pulse 112 bpm | BP 100/70 mmHg | RR 20/min | SpO₂ 98%.
Investigations: CBC — mild leukocytosis. Serum Electrolytes — hyponatremia. Stool — no blood/parasites. RFT — mildly elevated creatinine due to dehydration.""",
        "output": """Michael Smith, a 32-year-old man, was admitted on 2nd March 2026 and sent home on 5th March 2026. He came in with 3 days of loose watery stools (loose motions), vomiting, stomach cramps, and weakness. He also has a thyroid problem (hypothyroidism — a condition where the thyroid gland does not make enough hormones, making the body feel slow and tired) for 2 years. On arrival, he had a mild fever (99.8°F; normal is 98.6°F), fast heartbeat (112 beats per minute; normal is 60–100), and low blood pressure (100/70 mmHg; normal is around 120/80). His blood oxygen level was normal at 98%. Blood tests showed a mild rise in infection-fighting white cells (leukocytosis) and low sodium (an important salt in the blood called hyponatremia), which can happen when too much fluid is lost from the body. Stool test showed no blood or infection-causing parasites. His kidney test showed mildly raised creatinine (a marker for kidney function) because of dehydration (lack of enough water in the body). He was treated with fluids and medicines and recovered well before being sent home."""
    },
    {
        "input": """Patient Name: Robert Brown | Age/Sex: 58/M | Admission: 25/03/2026 | Discharge: 30/03/2026
C/O: Chest pain and sweating for 6 hours.
History: Sudden onset retrosternal chest pain radiating to the left arm, sweating, mild breathlessness.
Past History: Type 2 Diabetes Mellitus (8 years). Hypertension (10 years). Dyslipidemia.
Examination: Temp 98.4°F | Pulse 96 bpm | BP 160/100 mmHg | RR 22/min | SpO₂ 95%.
Investigations: ECG — ST depression in anterior leads. Troponin-I — elevated. 2D Echo — mild left ventricular dysfunction. Lipid Profile — elevated LDL cholesterol.""",
        "output": """Robert Brown, a 58-year-old man, was admitted on 25th March 2026 and sent home on 30th March 2026. He has a history of type 2 diabetes mellitus (sugar disease — a condition where the body cannot properly use or control sugar in the blood) for 8 years, high BP (hypertension) for 10 years, and dyslipidemia (high fat levels in the blood). He came in after 6 hours of sudden chest pain behind the breastbone, which was spreading to his left arm, along with sweating and mild difficulty in breathing. On admission, his blood pressure was high at 160/100 mmHg (normal is 120/80), heartbeat was 96 per minute, and blood oxygen level was 95% (slightly low; should be above 95%). An ECG (a heart tracing test that records electrical signals of the heart) showed ST depression in the front heart leads — a sign of reduced blood supply to the heart muscle. Troponin-I (a protein that leaks into the blood when the heart muscle is damaged) was elevated, confirming a mild heart attack called NSTEMI (Non-ST Elevation Myocardial Infarction — a type of heart attack where one of the heart's blood vessels is partially blocked). A 2D Echo (an ultrasound scan of the heart) showed mild weakness in the left pumping chamber of the heart (left ventricular dysfunction). Blood tests showed high LDL cholesterol (bad cholesterol; normal should be below 100 mg/dL in high-risk patients like him). He was carefully monitored and treated with heart medicines before being sent home."""
    }
]


# ══════════════════════════════════════════════════════════════════════════════
# 2. DISCHARGE SUMMARIZATION (Clinical Provider Perspective)
# ══════════════════════════════════════════════════════════════════════════════

DISCHARGE_SUMMARIZE_SYSTEM_PROMPT = """You are an expert clinical summarization specialist. Synthesize the following inpatient discharge summary into a concise, high-density clinical summary for healthcare providers.

Rules:
1. Maintain strict clinical precision and formal medical terminology. Do NOT simplify terms into lay analogies.
2. Preserve all factual data: exact diagnoses, ICD codes (if present), surgical procedures, vital sign abnormalities, laboratory anomalies, drug regimens, and dates.
3. Structure the summary into five clear sections:
   - ENCOUNTER OVERVIEW: Patient demographics, dates of stay, admitting complaint.
   - CLINICAL & DIAGNOSTIC FINDINGS: Key physical exam findings, abnormal lab values, and diagnostic imaging/cultures.
   - HOSPITAL COURSE & INTERVENTIONS: Surgeries, acute interventions, device insertions, and clinical progression.
   - FINAL DIAGNOSES: Primary condition and pertinent secondary comorbidities.
   - DISCHARGE PLAN & ACTION ITEMS: Current medication regimen, critical precautions, and follow-up plan.
4. If the patient expired (death/óbito), clearly state the immediate cause of death and terminal events.
5. Be concise, objective, and dense. Avoid unnecessary filler words or meta-commentary."""

DISCHARGE_SUMMARIZE_FEW_SHOT_EXAMPLES = [
    {
        "input": """Patient Name: Michael Smith | Age/Sex: 32/M | Admission: 02/03/2026 | Discharge: 05/03/2026
C/O: Loose stools, vomiting, and abdominal cramps for 3 days.
History: Multiple episodes of watery diarrhea with nausea, repeated vomiting, generalised weakness, and abdominal cramps. No blood in stools. No recent travel.
Past History: Hypothyroidism (2 years).
Examination: Temp 99.8°F | Pulse 112 bpm | BP 100/70 mmHg | RR 20/min | SpO₂ 98%.
Investigations: CBC — mild leukocytosis. Serum Electrolytes — hyponatremia. Stool — no blood/parasites. RFT — mildly elevated creatinine due to dehydration.
Course: Rehydrated with IV crystalloids, antiemetics, and electrolyte correction.
Discharge: Stable, tolerating oral intake.""",
        "output": """ENCOUNTER OVERVIEW: 32-year-old male admitted 02/03/2026 to 05/03/2026 (LOS: 3 days) presenting with acute watery diarrhea, emesis, and abdominal cramps for 3 days. Past history significant for hypothyroidism.

CLINICAL & DIAGNOSTIC FINDINGS: On admission: febrile (99.8°F), tachycardic (pulse 112 bpm), hypotensive (BP 100/70 mmHg). Labs demonstrated mild leukocytosis, hyponatremia, and prerenal azotemia with elevated creatinine secondary to volume depletion. Stool microscopy negative for blood/ova/parasites.

HOSPITAL COURSE & INTERVENTIONS: Successfully resuscitated with IV isotonic crystalloids, symptom control via antiemetics, and electrolyte replenishment. Renal parameters normalized.

FINAL DIAGNOSES: Acute gastroenteritis with moderate dehydration; prerenal acute kidney injury (resolved); chronic hypothyroidism.

DISCHARGE PLAN & ACTION ITEMS: Discharged hemodynamically stable on oral rehydration therapy and regular levothyroxine; follow-up in primary care clinic in 1 week."""
    }
]

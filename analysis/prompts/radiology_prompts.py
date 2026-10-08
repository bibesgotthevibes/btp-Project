"""
analysis/prompts/radiology_prompts.py
─────────────────────────────────────
Prompt templates and curated few-shot exemplars for Diagnostic Radiology Reports (MRI, CT, X-Ray).
Separates tasks into:
1. Simplification (Lay Indian English for patient/family explaining imaging findings and impressions)
2. Summarization (Concise, structured imaging synthesis for referring clinicians)
"""

# ══════════════════════════════════════════════════════════════════════════════
# 1. RADIOLOGY SIMPLIFICATION
# ══════════════════════════════════════════════════════════════════════════════

RADIOLOGY_SIMPLIFY_SYSTEM_PROMPT = """You are a medical radiology simplification assistant. Convert the following diagnostic radiology imaging report into simple, plain English that the patient and their family can clearly understand (at a 6th-grade reading level).

Rules:
1. Start with one short sentence naming the scan and why it was done (e.g. 'You had an MRI scan of your brain because of dizziness.'). Do not explain how the scan works or list technical details such as sequences, contrast or radiation.
2. Keep essential anatomical and medical terms but immediately explain each in parentheses on first use, e.g. 'cerebellum (the part of the brain that controls balance and coordination)'.
3. Clearly state what was found to be NORMAL first, providing reassurance about unaffected areas.
4. For any ABNORMAL findings (such as lesions, abscesses, ischemia, inflammation, or fractures):
   - Explain what the finding means in plain words without causing unnecessary panic.
   - Explain common terms simply: e.g. 'ischemic-gliotic lesions (tiny microscopic scar spots in the brain caused by reduced blood flow in the past, often seen with aging or high BP)'.
   - Clarify whether the finding is new, chronic, or requires further evaluation.
5. If the radiologist recommends further tests (e.g. follow-up CT, contrast scan, or consultation), state this clearly.
6. Write as continuous plain prose paragraphs without bullet points or headers.
7. Preserve all factual observations; never guess, infer, or fabricate findings not in the report.
8. Output only the simplified text, nothing else."""

RADIOLOGY_SIMPLIFY_FEW_SHOT_EXAMPLES = [
    {
        "input": """BRAIN (CRANIAL) MRI
Clinical: Dizziness.
Technique: Three-plane T1-weighted, FLAIR; axial T2-weighted, SWI, and DWI.
Findings:
The brainstem and cerebellum, fourth ventricle, and posterior fossa cisterns are normal.
The bilateral basal ganglia, internal capsules, and corpus callosum are normal.
Except for physiologic cystic perivascular enlargement in the left parietal region, the cerebral parenchyma is normal.
Intracranial DWI and SWI sections are normal.
Impression: Cranial MRI findings within normal limits.""",
        "output": """You had an MRI scan of your brain because of dizziness. The results of the scan are completely normal and reassuring (findings within normal limits). All major parts of your brain — including the brainstem (which controls basic functions like breathing and heartbeat), the cerebellum (the balance and walking center), and the fluid-filled spaces in the head (ventricles) — are in healthy condition. The deep nerve pathways (basal ganglia and internal capsule) look normal. There is a tiny natural fluid space (physiologic cystic perivascular enlargement — a harmless, normal widening around a tiny blood vessel that is present from birth) in the upper left side of the brain, which is completely normal and not a cause for concern. There is no evidence of stroke, bleeding, infection, or tumor. Overall, your brain scan is healthy and normal."""
    }
]


# ══════════════════════════════════════════════════════════════════════════════
# 2. RADIOLOGY SUMMARIZATION (Clinical & Diagnostic Perspective)
# ══════════════════════════════════════════════════════════════════════════════

RADIOLOGY_SUMMARIZE_SYSTEM_PROMPT = """You are an expert diagnostic radiologist summarization specialist. Synthesize the following radiology imaging report into a concise, high-density structured summary for referring physicians.

Rules:
1. Maintain formal radiological terminology, anatomical precision, and sequence descriptions.
2. Structure the summary into four clear sections:
   - EXAM & CLINICAL INDICATION: Imaging modality, sequences, contrast status, and reason for study.
   - ACUTE & CRITICAL FINDINGS: Primary intracranial/thoracic abnormalities, acute hemorrhage, infarction, mass effect, herniation, or infectious foci.
   - SECONDARY & INCIDENTAL FINDINGS: Chronic microvascular changes, prior surgical changes, inflammatory mucosal disease, or benign anatomic variants.
   - IMPRESSION & ACTIONABLE RECOMMENDATIONS: Bottom-line diagnostic conclusion and recommended follow-up imaging or clinical correlation.
3. If the scan is negative or within normal limits, explicitly state normal status across key compartments.
4. Be dense, objective, and concise. Avoid redundant descriptions."""

RADIOLOGY_SUMMARIZE_FEW_SHOT_EXAMPLES = [
    {
        "input": """BRAIN (CRANIAL) AND TEMPORAL MRI
Clinical information: Left face and jaw pain; peripheral facial paralysis one month ago.
Technique: Cranial: 3-plane T1, FLAIR, axial T2, SWI, DWI with IV contrast. Temporal: Axial/coronal T2, T1, CISS with IV contrast.
Findings: Brainstem, cerebellum, and cerebral parenchyma normal. No intracranial DWI/SWI restriction. Non-enhancing solid bone lesion between left jugular foramen and facial canal; similar bilateral parietal bone lesions. Temporal segment of left facial nerve in close proximity without enhancement; mild enhancement in preganglionic facial nerve.
Impression: Non-enhancing bone lesions left jugular foramen/facial canal; mild left preganglionic facial nerve enhancement compatible with Bell's palsy. Recommend temporal bone CT.""",
        "output": """EXAM & CLINICAL INDICATION: Multi-parametric cranial and high-resolution temporal MRI with IV contrast for 1-month history of left facial/jaw pain and peripheral facial nerve palsy.

ACUTE & CRITICAL FINDINGS: No acute intracranial territorial infarction, hemorrhage, or mass effect on DWI/SWI. Presence of a non-enhancing solid osseous lesion centered between the left jugular foramen and facial canal, alongside bilateral parietal bone lesions, concerning for infiltrative marrow process.

SECONDARY & INCIDENTAL FINDINGS: Mild abnormal enhancement involving the left preganglionic facial nerve segment without gross nerve thickening; brain parenchyma and ventricular system otherwise unremarkable.

IMPRESSION & ACTIONABLE RECOMMENDATIONS: 1. Solid osseous lesion at left skull base/jugular foramen adjacent to facial canal; recommend dedicated high-resolution temporal bone CT to assess cortical and trabecular architecture. 2. Left facial nerve preganglionic enhancement concordant with clinical Bell's palsy."""
    }
]


# ══════════════════════════════════════════════════════════════════════════════
# 3. RADIOLOGY NER-GUIDED SIMPLIFICATION
# ══════════════════════════════════════════════════════════════════════════════

RADIOLOGY_NER_GUIDED_SIMPLIFY_SYSTEM_PROMPT = """You are a medical radiology simplification assistant. Convert the following diagnostic radiology imaging report into simple, plain English that the patient and their family can clearly understand (at a 6th-grade reading level).

{ner_retention_block}

Rules:
1. Start with one short sentence naming the scan and why it was done (e.g. 'You had an MRI scan of your brain because of dizziness.'). Do not explain how the scan works or list technical details such as sequences, contrast or radiation.
2. Keep essential anatomical and medical terms but immediately explain each in parentheses on first use, e.g. 'cerebellum (the part of the brain that controls balance and coordination)'.
3. Clearly state what was found to be NORMAL first, providing reassurance about unaffected areas.
4. For any ABNORMAL findings (such as lesions, abscesses, ischemia, inflammation, or fractures):
   - Explain what the finding means in plain words without causing unnecessary panic.
   - Explain common terms simply: e.g. 'ischemic-gliotic lesions (tiny microscopic scar spots in the brain caused by reduced blood flow in the past, often seen with aging or high BP)'.
   - Clarify whether the finding is new, chronic, or requires further evaluation.
5. If the radiologist recommends further tests (e.g. follow-up CT, contrast scan, or consultation), state this clearly.
6. Write as continuous plain prose paragraphs without bullet points or headers.
7. Preserve all factual observations; never guess, infer, or fabricate findings not in the report.
8. Output only the simplified text, nothing else.
9. CRITICAL — ENTITY RETENTION: Every entity listed in the extracted entities block above MUST appear in your simplified output — including the scan type, every normal structure listed, every abnormal finding with its location and severity, all measurements with units, the radiologist's overall impression, and every recommended follow-up action. Do not omit any of them."""


# ══════════════════════════════════════════════════════════════════════════════
# 4. CHEST X-RAY SIMPLIFICATION (Open-i / LaymanRRG benchmark variant)
# ══════════════════════════════════════════════════════════════════════════════
# Same goal as RADIOLOGY_SIMPLIFY_*, adapted to short chest X-ray reports and to the
# sentence-by-sentence style of the LaymanRRG references. Few-shot pairs come from the
# Open-i TRAIN split (benchmark runs on validation), so there is no test leakage.

RADIOLOGY_CXR_SIMPLIFY_SYSTEM_PROMPT = """You are a medical radiology simplification assistant. Rewrite the following chest X-ray report in simple, plain English that a patient with no medical training can understand (6th-grade reading level).

Rules:
1. Rewrite the report sentence by sentence, in the same order. Use one short sentence per finding.
2. Replace every medical term with everyday words (e.g. 'pleural effusion' -> 'fluid around the lungs', 'pneumothorax' -> 'air outside the lungs', 'cardiomediastinal silhouette' -> 'the heart and the area around it'). Keep a medical term only if there is no simple word for it.
3. Keep every negative finding as a negative: 'No pneumothorax' must stay 'There is no air outside the lungs'. Never drop the word 'no'.
4. Keep every positive finding, measurement, side (left/right) and comparison with earlier exams ('stable', 'increased', 'unchanged').
5. Do not add explanations, reassurance, advice or anything that is not in the report.
6. Write plain sentences only: no headings, bullet points or brackets.
7. Output only the rewritten text, nothing else."""

RADIOLOGY_CXR_SIMPLIFY_FEW_SHOT_EXAMPLES = [
    {   # Open-i 3242.xml (train)
        "input": "The heart and cardiomediastinal silhouette are normal in size and contour. There is no focal air space opacity, pleural effusion, or pneumothorax. There are multilevel degenerative changes in the thoracic spine. No acute cardiopulmonary finding.",
        "output": "The heart and the area around it look normal in size and shape. There is no sign of pneumonia, fluid around the lungs, or air outside the lungs. There are several levels of wear and tear in the spine. No sudden heart or lung problem is found.",
    },
    {   # Open-i 3697.xml (train)
        "input": "The cardiomediastinal silhouette is stable in appearance. There are extensive fibrotic changes in the right lung with rightward shift of the trachea, similar to the previous exam. The left lung is well-aerated without focal airspace consolidation, pleural effusions or pneumothorax. There is left apical pleural-parenchymal scarring. No acute bony findings. 1. No acute cardiopulmonary findings. 2. Extensive fibrotic changes of the right lung, similar to the previous exam.",
        "output": "The heart and middle part of the chest look the same as before. The right lung has a lot of scar tissue, which is causing the windpipe to shift to the right, just like the last time it was checked. The left lung is well-inflated and doesn't have any specific areas of lung collapse, fluid around the lungs, or air outside the lungs. There is some scarring at the top of the left lung. There are no new bone issues. 1. There are no new heart or lung problems. 2. The right lung has a lot of scar tissue, just like it did before.",
    },
    {   # Open-i 3694.xml (train)
        "input": "Interval removal of left-sided chest tube. Small residual left apical pneumothorax has increased slightly in size the prior exam, now measuring approximately 0.9 cm from the thoracic apex. Stable cardiomediastinal silhouette. No focal airspace consolidation. No pleural effusion. No acute cardiopulmonary abnormality.",
        "output": "The chest tube on the left side was removed. There's a small amount of air leakage around the lung on the left side, which has gotten a little bigger since the last check, now about 0.9 cm from the top of the chest. The heart and middle part of the chest look the same as before. There's no sign of a specific lung infection. No fluid is seen around the lungs. There are no urgent heart or lung issues.",
    },
]

# NER-guided variant of the chest X-ray prompt: identical rules plus the Stage 1 entity
# block and a retention rule, so a direct-vs-NER comparison changes only the entities.
RADIOLOGY_CXR_NER_GUIDED_SIMPLIFY_SYSTEM_PROMPT = RADIOLOGY_CXR_SIMPLIFY_SYSTEM_PROMPT.replace(
    "\n\nRules:", "\n\n{ner_retention_block}\n\nRules:", 1
) + """
8. Every finding in the extracted entities block above must appear in your rewrite with the same meaning, including every negative ('no ...') finding."""

# ── Improved NER variants (Open-i benchmark) ──────────────────────────────────
# Stage 1 for both: list every finding as a plain-English sentence (not a medical-term
# schema), so the checklist doesn't pull jargon back into the rewrite.

RADIOLOGY_CXR_FINDINGS_EXTRACTION_PROMPT = """You extract findings from chest X-ray reports. List EVERY finding in the report, including normal findings, negative findings ('no ...'), comparisons with earlier exams, devices, and measurements.

For each finding give:
- "finding": the finding as written in the report
- "status": "present", "absent" (the report says it is not there) or "uncertain"
- "plain": one short plain-English sentence a patient understands, stating the finding exactly as the report does (keep 'no' for absent findings, keep sides, sizes and comparisons)

Return only JSON: {"findings": [{"finding": "...", "status": "...", "plain": "..."}]}"""

RADIOLOGY_CXR_FINDINGS_EXAMPLE = {  # Open-i 3242.xml (train)
    "input": "The heart and cardiomediastinal silhouette are normal in size and contour. There is no focal air space opacity, pleural effusion, or pneumothorax. There are multilevel degenerative changes in the thoracic spine. No acute cardiopulmonary finding.",
    "output": """{"findings": [
  {"finding": "heart and cardiomediastinal silhouette normal in size and contour", "status": "present", "plain": "The heart and the area around it are normal in size and shape."},
  {"finding": "focal air space opacity", "status": "absent", "plain": "There is no sign of pneumonia."},
  {"finding": "pleural effusion", "status": "absent", "plain": "There is no fluid around the lungs."},
  {"finding": "pneumothorax", "status": "absent", "plain": "There is no air outside the lungs."},
  {"finding": "multilevel degenerative changes in the thoracic spine", "status": "present", "plain": "There is wear and tear in several parts of the upper spine."},
  {"finding": "acute cardiopulmonary finding", "status": "absent", "plain": "There is no sudden heart or lung problem."}
]}""",
}

# Variant A: few-shot chest X-ray prompt + plain-language checklist.
RADIOLOGY_CXR_CHECKLIST_SIMPLIFY_SYSTEM_PROMPT = RADIOLOGY_CXR_SIMPLIFY_SYSTEM_PROMPT.replace(
    "\n\nRules:", "\n\nChecklist of every finding in this report:\n{checklist}\n\nRules:", 1
) + """
8. Make sure every checklist item is covered with the same meaning. You may reword them, but keep every 'no'."""

# Variant B: write the normal few-shot rewrite first, then check it against the checklist
# and repair only what is missing or wrong.
RADIOLOGY_CXR_REPAIR_SYSTEM_PROMPT = """You check a plain-language rewrite of a chest X-ray report. You are given the original report, a checklist of every finding in it, and a draft rewrite.

If the draft covers every checklist item with the correct meaning (including every 'no', side, size and comparison), output the draft exactly as it is.

Otherwise, fix only what is missing or wrong: add or correct those sentences in the same plain style and keep every other sentence unchanged. Do not add anything that is not in the report.

Output only the final text, nothing else."""

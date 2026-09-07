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
1. Explain the type of imaging scan conducted in simple words (e.g. 'cranial MRI (a detailed brain scan using magnetic fields and radio waves, without any radiation)').
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
        "output": """You had a cranial MRI (a detailed magnetic brain scan that takes pictures of brain tissue without using radiation) because of dizziness. The results of the scan are completely normal and reassuring (findings within normal limits). All major parts of your brain — including the brainstem (which controls basic functions like breathing and heartbeat), the cerebellum (the balance and walking center), and the fluid-filled spaces in the head (ventricles) — are in healthy condition. The deep nerve pathways (basal ganglia and internal capsule) look normal. There is a tiny natural fluid space (physiologic cystic perivascular enlargement — a harmless, normal widening around a tiny blood vessel that is present from birth) in the upper left side of the brain, which is completely normal and not a cause for concern. There is no evidence of stroke, bleeding, infection, or tumor. Overall, your brain scan is healthy and normal."""
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

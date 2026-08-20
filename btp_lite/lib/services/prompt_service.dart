/// Prompt building logic — ported directly from backend/app.py
/// All 11 rules + 4 few-shot examples preserved exactly, with enhanced clinical guardrails.
library;

const String kSystemPrompt =
    "You are a medical language simplification assistant. Convert the following "
    "clinical discharge summary into simple, plain Indian English for the patient's "
    "family members.\n\n"
    "Rules:\n"
    "1. Keep every medical term but immediately explain it in plain words in "
    "parentheses on first use only, e.g. 'hypertension (high BP)'.\n"
    "2. Use simple language a 6th-grader can understand. Avoid jargon. Use "
    "common Indian English terms where natural: 'sugar' for diabetes, 'BP' "
    "for blood pressure, 'motions' for bowel movements.\n"
    "3. Preserve ALL factual information — never add, remove, alter, or infer "
    "any clinical facts, values, dates, or instructions.\n"
    "4. Write as continuous plain prose paragraphs — no bullet points, no "
    "headers, no numbered lists. Output only the simplified text, nothing else.\n"
    "5. For any measurement (e.g. BP, blood sugar, heart rate), briefly state "
    "what the normal range is and whether the patient's value was within it.\n"
    "6. Use a calm, respectful tone. Do not add emotional commentary, opinions, "
    "or reassurances not present in the original text.\n"
    "7. CRITICAL — person and tense: First check whether the summary records "
    "the patient's death (look for 'death', 'expired', 'deceased', 'asystole', "
    "'absence of pulse', 'body released', or similar). If yes, write in third "
    "person past tense for the family ('the patient', 'he/she/they'). If no, "
    "address the patient directly in second person ('you', 'your').\n"
    "8. CRITICAL — dates: Convert dates exactly as they appear using the format "
    "specified in the document. If no format is specified, treat as MM/DD. "
    "Never guess or infer a date not explicitly stated.\n"
    "9. For each medication, state its name and purpose in plain language, "
    "e.g. 'Ceftriaxone — an antibiotic given to fight the bacterial infection'.\n"
    "10. For each procedure or device, briefly state what it is and why it was "
    "done, e.g. 'haemodialysis (a machine that cleaned the blood when the "
    "kidneys could not)'.\n"
    "11. If the text contains placeholders such as {omitted} or [person], "
    "reproduce them exactly as they appear. Do not guess or replace them.\n"
    "12. DOMAIN GUARDRAIL: You are exclusively a medical simplification assistant. "
    "If the input is not a medical discharge summary, clinical case report, or health record, "
    "do not generate non-medical content; instead respond solely with "
    "'Please provide a valid medical discharge summary or clinical report.'\n";

/// 4 curated discharge summary → Indian Lay English pairs
const List<(String, String)> kFewShotExamples = [
  (
    // Example 1 — Acute Gastroenteritis
    """Patient Name: Michael Smith | Age/Sex: 32/M | Admission: 02/03/2026 | Discharge: 05/03/2026
C/O: Loose stools, vomiting, and abdominal cramps for 3 days.
History: Multiple episodes of watery diarrhea with nausea, repeated vomiting, generalised weakness, and abdominal cramps. No blood in stools. No recent travel.
Past History: Hypothyroidism (2 years).
Examination: Temp 99.8°F | Pulse 112 bpm | BP 100/70 mmHg | RR 20/min | SpO₂ 98%.
Investigations: CBC — mild leukocytosis. Serum Electrolytes — hyponatremia. Stool — no blood/parasites. RFT — mildly elevated creatinine due to dehydration.""",
    """Michael Smith, a 32-year-old man, was admitted on 2nd March 2026 and sent home on 5th March 2026. He came in with 3 days of loose watery stools (loose motions), vomiting, stomach cramps, and weakness. He also has a thyroid problem (hypothyroidism — a condition where the thyroid gland does not make enough hormones, making the body feel slow and tired) for 2 years. On arrival, he had a mild fever (99.8°F; normal is 98.6°F), fast heartbeat (112 beats per minute; normal is 60–100), and low blood pressure (100/70 mmHg; normal is around 120/80). His blood oxygen level was normal at 98%. Blood tests showed a mild rise in infection-fighting white cells (leukocytosis) and low sodium (an important salt in the blood called hyponatremia), which can happen when too much fluid is lost from the body. Stool test showed no blood or infection-causing parasites. His kidney test showed mildly raised creatinine (a marker for kidney function) because of dehydration (lack of enough water in the body). He was treated with fluids and medicines and recovered well before being sent home."""
  ),
  (
    // Example 2 — Acute Exacerbation of Bronchial Asthma
    """Patient Name: Sarah Williams | Age/Sex: 28/F | Admission: 18/02/2026 | Discharge: 21/02/2026
C/O: Wheezing, chest tightness, and breathlessness for 2 days.
History: Worsening shortness of breath, wheezing, and dry cough after dust exposure. Home inhaler not relieving symptoms. No fever or chest pain.
Past History: Bronchial Asthma since childhood. Allergic Rhinitis.
Examination: Temp 98.6°F | Pulse 108 bpm | BP 130/84 mmHg | RR 28/min | SpO₂ 90%.
Investigations: CBC — mild eosinophilia. Chest X-ray — hyperinflation. PEFR — reduced. ABG — mild hypoxemia.""",
    """Sarah Williams, a 28-year-old woman, was admitted on 18th February 2026 and sent home on 21st February 2026. She has had asthma (a long-term condition where the breathing tubes become narrow and make breathing very difficult) since childhood and also has allergic rhinitis (nose allergy). She was brought in with 2 days of wheezing (a whistling sound while breathing), chest tightness, and difficulty in breathing after being exposed to dust. Her home inhaler was not helping enough. On admission, her breathing rate was fast (28 breaths per minute; normal is 12–20) and her blood oxygen level was low at 90% (normal should be above 95%), which means her body was not getting enough oxygen. Blood tests showed a mild rise in allergy cells (eosinophilia — a sign the body is reacting to something). A chest X-ray showed the lungs were over-inflated (hyperinflation — the lungs hold more air than normal during an asthma attack). A breathing speed test (Peak Expiratory Flow Rate) was reduced, confirming the airways were blocked. A blood gas test also confirmed mild low oxygen levels (hypoxemia). She was treated with breathing medicines and nebulisation (medicine given through a breathing mask) and recovered well before discharge."""
  ),
  (
    // Example 3 — UTI with Pyelonephritis
    """Patient Name: Emily Johnson | Age/Sex: 40/F | Admission: 12/01/2026 | Discharge: 16/01/2026
C/O: Fever, burning micturition, and flank pain for 4 days.
History: High-grade fever with chills, painful and frequent urination, right-sided flank pain. No kidney stones or hematuria.
Past History: Recurrent UTIs. Iron Deficiency Anemia.
Examination: Temp 101.5°F | Pulse 102 bpm | BP 118/76 mmHg | RR 18/min | SpO₂ 99%.
Investigations: Urine Routine — pus cells and bacteria. Urine Culture — E. coli. CBC — elevated WBC. Ultrasound Abdomen — mild right renal pelvic inflammation.""",
    """Emily Johnson, a 40-year-old woman, was admitted on 12th January 2026 and sent home on 16th January 2026. She has a history of recurrent UTIs (urinary tract infections — infections in the tube that carries urine out of the body) and iron deficiency anemia (low blood due to lack of iron). She came in with 4 days of high fever with chills, pain and burning while passing urine (micturition), passing urine much more often than usual, and pain on the right side of her back near the kidney area (flank pain). On admission she had a high temperature of 101.5°F (normal is 98.6°F), fast heartbeat (102 per minute), and normal blood pressure. Urine test showed pus cells and bacteria, confirming an active infection. Urine culture (a test where urine is kept in a lab to see which germs grow) showed E. coli bacteria (a common germ that causes urinary infections). Blood test showed a high white blood cell count, which is a sign the body was fighting a serious infection. An ultrasound scan (a painless scan using sound waves) showed mild swelling and inflammation in the tube leading out of the right kidney (renal pelvis). She was treated with antibiotics (infection-fighting medicines) through a drip and improved well."""
  ),
  (
    // Example 4 — ACS / NSTEMI [used as ONE-SHOT example]
    """Patient Name: Robert Brown | Age/Sex: 58/M | Admission: 25/03/2026 | Discharge: 30/03/2026
C/O: Chest pain and sweating for 6 hours.
History: Sudden onset retrosternal chest pain radiating to the left arm, sweating, mild breathlessness. No syncope or trauma.
Past History: Type 2 Diabetes Mellitus (8 years). Hypertension (10 years). Dyslipidemia.
Examination: Temp 98.4°F | Pulse 96 bpm | BP 160/100 mmHg | RR 22/min | SpO₂ 95%.
Investigations: ECG — ST depression in anterior leads. Troponin-I — elevated. 2D Echo — mild left ventricular dysfunction. Lipid Profile — elevated LDL cholesterol.""",
    """Robert Brown, a 58-year-old man, was admitted on 25th March 2026 and sent home on 30th March 2026. He has a history of type 2 diabetes mellitus (sugar disease — a condition where the body cannot properly use or control sugar in the blood) for 8 years, high BP (hypertension) for 10 years, and dyslipidemia (high fat levels in the blood). He came in after 6 hours of sudden chest pain behind the breastbone, which was spreading to his left arm, along with sweating and mild difficulty in breathing. On admission, his blood pressure was high at 160/100 mmHg (normal is 120/80), heartbeat was 96 per minute, and blood oxygen level was 95% (slightly low; should be above 95%). An ECG (a heart tracing test that records electrical signals of the heart) showed ST depression in the front heart leads — a sign of reduced blood supply to the heart muscle. Troponin-I (a protein that leaks into the blood when the heart muscle is damaged) was elevated, confirming a mild heart attack called NSTEMI (Non-ST Elevation Myocardial Infarction — a type of heart attack where one of the heart's blood vessels is partially blocked). A 2D Echo (an ultrasound scan of the heart) showed mild weakness in the left pumping chamber of the heart (left ventricular dysfunction). Blood tests showed high LDL cholesterol (bad cholesterol; normal should be below 100 mg/dL in high-risk patients like him). He was carefully monitored and treated with heart medicines before being sent home."""
  ),
];

/// Indian Lay English term substitution dictionary (longest-match, sorted)
const Map<String, String> kIndianLayDict = {
  'hypertension': 'high BP',
  'diabetes mellitus': 'sugar disease (diabetes)',
  'myocardial infarction': 'heart attack',
  'acute renal failure': 'sudden kidney failure',
  'chronic renal failure': 'long-term kidney problem',
  'septicemia': 'blood infection (sepsis)',
  'sepsis': 'serious blood infection',
  'pneumonia': 'lung infection',
  'tuberculosis': 'TB (tuberculosis)',
  'pneumothorax': 'air trapped in chest',
  'endocarditis': 'infection of heart valves',
  'spondylodiscitis': 'spine bone infection',
  'hypotension': 'low BP',
  'pyrexia': 'fever',
  'dyspnea': 'difficulty in breathing',
  'edema': 'swelling',
  'abscess': 'pus-filled swelling',
  "crohn's disease": "long-term bowel disease (Crohn's)",
  'renal failure': 'kidney failure',
  'cerebrovascular accident': 'brain stroke',
  'anemia': 'low blood (anemia)',
  'tachycardia': 'fast heartbeat',
  'bradycardia': 'slow heartbeat',
  'atrial fibrillation': 'irregular heartbeat',
  'hemodialysis': 'kidney dialysis',
  'tracheostomy': 'breathing tube in neck',
  'thoracotomy': 'chest surgery',
  'pneumonectomy': 'removal of a lung',
  'ileocolectomy': 'removal of part of bowel',
  'anastomosis': 'surgical joining of bowel ends',
  'debridement': 'surgical wound cleaning',
  'arteriovenous fistula': 'dialysis access point on arm',
  'intramuscular': 'given as a muscle injection',
  'intravenous': 'given through a vein (drip)',
  'percutaneous': 'through the skin',
  'antibiotic therapy': 'antibiotic treatment',
  'antibiotic': 'infection-fighting medicine',
  'blood culture': 'blood test to find infection',
  'procalcitonin': 'blood marker for infection',
  'hemoglobin': 'blood count (Hb)',
  'creatinine': 'kidney function marker',
  'bilirubin': 'liver function marker',
  'saturation': 'oxygen level in blood',
  'afebrile': 'no fever',
  'eupneic': 'breathing normally',
  'acyanotic': 'no bluish discoloration',
  'anicteric': 'no yellowing of skin/eyes',
  'vesicular breath sounds': 'normal breathing sounds',
  'discharge': 'sent home from hospital',
  'outpatient clinic': 'OPD (Out Patient Department)',
  'follow-up': 'return visit to doctor',
  'ward': 'general hospital room',
  'intensive care unit': 'ICU (serious care room)',
  'sus': 'government health scheme',
  'orally': 'by mouth',
  'administer': 'give',
};

/// Preprocess medical text with dictionary substitution (longest-match first)
String preprocessMedicalText(String text) {
  var result = text.trim().toLowerCase().replaceAll(RegExp(r'\s+'), ' ');
  final sortedKeys = kIndianLayDict.keys.toList()
    ..sort((a, b) => b.length.compareTo(a.length));
  for (final key in sortedKeys) {
    result = result.replaceAll(key, kIndianLayDict[key]!);
  }
  return result;
}

/// Build the full prompt string for the given strategy.
/// strategy: 'zero-shot' | 'one-shot' | 'few-shot'
String buildPromptString(String strategy, String text) {
  final buffer = StringBuffer();
  buffer.write(kSystemPrompt);
  buffer.write('\n\n');

  if (strategy == 'one-shot') {
    final (orig, simp) = kFewShotExamples[3]; // Example 4 (NSTEMI)
    buffer.write('Here is an example of what I expect:\n\n');
    buffer.write('--- Example ---\n');
    buffer.write('Original Medical Text:\n$orig\n\n');
    buffer.write('Simplified:\n$simp\n\n');
  } else if (strategy == 'few-shot') {
    buffer.write('Here are some examples of what I expect:\n\n');
    for (int i = 0; i < kFewShotExamples.length; i++) {
      final (orig, simp) = kFewShotExamples[i];
      buffer.write('--- Example ${i + 1} ---\n');
      buffer.write('Original Medical Text:\n$orig\n\n');
      buffer.write('Simplified:\n$simp\n\n');
    }
  }

  buffer.write('--- Your Task ---\n');
  buffer.write(
      'Please simplify the following discharge summary into Indian Lay English:\n\n');
  buffer.write('Original Medical Text:\n$text\n\n');
  buffer.write('Simplified:\n');
  return buffer.toString();
}

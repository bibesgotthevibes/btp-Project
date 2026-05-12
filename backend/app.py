"""
backend/app.py — MedSimplify Flask REST API
============================================
Run:
    cd backend
    pip install -r requirements.txt
    flask run --port 5000
"""

import os
import requests
import re
import csv
import random
from datetime import timedelta

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

# Load .env from repo root (one level up) or local backend/.env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()  # also pick up backend/.env if present

try:
    from cerebras.cloud.sdk import Cerebras
except ImportError:
    Cerebras = None

try:
    from google import genai as genai_client
    from google.genai import types as genai_types
except ImportError:
    genai_client = None
    genai_types = None

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForCausalLM
except ImportError:
    torch = None

from db import db
from auth import auth_bp
from chunking_logic import generate_scifive_chunked, generate_biobart_chunked, generate_biogpt_chunked

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)

CORS(
    app,
    resources={r"/api/*": {
        "origins": [
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
            "http://localhost:3000",
        ]
    }},
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    supports_credentials=True,
)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/medsimplify"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "change-me-in-production-please")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=7)

db.init_app(app)
JWTManager(app)
app.register_blueprint(auth_bp)

with app.app_context():
    db.create_all()

# ── AI model catalogue ────────────────────────────────────────────────────────
# accessible=True  → works with standard API key
# accessible=False → exists but usually requires premium key logic
MODELS = [
    # ── Local models ──────────────────────────────────────────────────────────
    {"id": "scifive-local",         "name": "SciFive (Local T5)",          "accessible": True, "api_provider": "local"},
    {"id": "biobart-local",         "name": "BioBART (Local)",              "accessible": True, "api_provider": "local"},
    {"id": "biogpt-local",          "name": "BioGPT (Local)",               "accessible": True, "api_provider": "local"},
    # ── Cerebras ──────────────────────────────────────────────────────────────
    {"id": "llama3.1-8b",           "name": "Llama 3.1 8B",                 "accessible": True, "api_provider": "cerebras"},
    # ── Google Gemini ─────────────────────────────────────────────────────────
    {"id": "gemini-2.5-flash",      "name": "Gemini 2.5 Flash",             "accessible": True, "api_provider": "gemini"},
    # ── Groq ──────────────────────────────────────────────────────────────────
    {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B (Groq)",      "accessible": True, "api_provider": "groq"},
    {"id": "llama-3.1-8b-instant",  "name": "Llama 3.1 8B Instant (Groq)", "accessible": True, "api_provider": "groq"},
]

SYSTEM_PROMPT = (
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
)

# ── SciFive Local Model Cache ─────────────────────────────────────────────────
SCIFIVE_MODEL = None
SCIFIVE_TOKENIZER = None
BIOBART_MODEL = None
BIOBART_TOKENIZER = None
BIOGPT_MODEL = None
BIOGPT_TOKENIZER = None

def load_scifive():
    """Load SciFive model and tokenizer once, cache in memory."""
    global SCIFIVE_MODEL, SCIFIVE_TOKENIZER
    if SCIFIVE_MODEL is not None:
        return SCIFIVE_MODEL, SCIFIVE_TOKENIZER
    
    if torch is None:
        print("[SciFive] torch and transformers are not installed")
        return None, None
    
    model_path = os.path.join(os.path.dirname(__file__), "..", "SciFive", "model")
    hf_fallback = "11Raghav/SciFive"
    
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if os.path.isdir(model_path):
            SCIFIVE_TOKENIZER = AutoTokenizer.from_pretrained(model_path)
            SCIFIVE_MODEL = AutoModelForSeq2SeqLM.from_pretrained(model_path).to(device)
            print(f"[SciFive] Model loaded from local path {model_path} on {device}")
        else:
            print(f"[SciFive] Local path not found. Downloading from HF: {hf_fallback}")
            SCIFIVE_TOKENIZER = AutoTokenizer.from_pretrained(hf_fallback)
            SCIFIVE_MODEL = AutoModelForSeq2SeqLM.from_pretrained(hf_fallback).to(device)
            print(f"[SciFive] Model downloaded from HF {hf_fallback} on {device}")
            
        return SCIFIVE_MODEL, SCIFIVE_TOKENIZER
    except Exception as e:
        print(f"[SciFive] Failed to load model: {str(e)}")
        return None, None


def _resolve_biobart_model_path():
    """Find a usable BioBART model directory from extracted files."""
    base_path = os.path.join(os.path.dirname(__file__), "..", "BioBART", "model")
    candidates = [base_path]

    # Prefer newest checkpoint if top-level model files are unavailable.
    for checkpoint in ["checkpoint-5625", "checkpoint-4500"]:
        candidates.append(os.path.join(base_path, checkpoint))

    for path in candidates:
        if os.path.isdir(path):
            has_model = os.path.isfile(os.path.join(path, "model.safetensors"))
            has_tokenizer = os.path.isfile(os.path.join(path, "tokenizer.json"))
            if has_model and has_tokenizer:
                return path

    return None

def load_biobart():
    """Load BioBART model and tokenizer once, cache in memory."""
    global BIOBART_MODEL, BIOBART_TOKENIZER
    if BIOBART_MODEL is not None:
        return BIOBART_MODEL, BIOBART_TOKENIZER

    if torch is None:
        print("[BioBART] torch and transformers are not installed")
        return None, None

    model_path = _resolve_biobart_model_path()
    hf_fallback = "11Raghav/BioBART"

    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if model_path:
            BIOBART_TOKENIZER = AutoTokenizer.from_pretrained(model_path)
            BIOBART_MODEL = AutoModelForSeq2SeqLM.from_pretrained(model_path).to(device)
            print(f"[BioBART] Model loaded from local path {model_path} on {device}")
        else:
            print(f"[BioBART] Local path not found. Downloading from HF: {hf_fallback}")
            BIOBART_TOKENIZER = AutoTokenizer.from_pretrained(hf_fallback)
            BIOBART_MODEL = AutoModelForSeq2SeqLM.from_pretrained(hf_fallback).to(device)
            print(f"[BioBART] Model downloaded from HF {hf_fallback} on {device}")
            
        return BIOBART_MODEL, BIOBART_TOKENIZER
    except Exception as e:
        print(f"[BioBART] Failed to load model: {str(e)}")
        return None, None

def _resolve_biogpt_model_path():
    """Find a usable BioGPT model directory from extracted files."""
    base_path = os.path.join(os.path.dirname(__file__), "..", "BioGPT", "model")
    candidates = [base_path]

    for checkpoint in ["checkpoint-11250", "checkpoint-4500"]:
        candidates.append(os.path.join(base_path, checkpoint))

    for path in candidates:
        if os.path.isdir(path):
            has_model = os.path.isfile(os.path.join(path, "model.safetensors"))
            has_tokenizer = os.path.isfile(os.path.join(path, "tokenizer_config.json")) or os.path.isfile(os.path.join(path, "vocab.json"))
            if has_model and has_tokenizer:
                return path

    return None

def load_biogpt():
    """Load BioGPT model and tokenizer once, cache in memory."""
    global BIOGPT_MODEL, BIOGPT_TOKENIZER
    if BIOGPT_MODEL is not None:
        return BIOGPT_MODEL, BIOGPT_TOKENIZER

    if torch is None:
        print("[BioGPT] torch and transformers are not installed")
        return None, None

    model_path = _resolve_biogpt_model_path()
    hf_fallback = "11Raghav/BioGPT"

    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if model_path:
            BIOGPT_TOKENIZER = AutoTokenizer.from_pretrained(model_path)
            BIOGPT_MODEL = AutoModelForCausalLM.from_pretrained(model_path).to(device)
            print(f"[BioGPT] Model loaded from local path {model_path} on {device}")
        else:
            print(f"[BioGPT] Local path not found. Downloading from HF: {hf_fallback}")
            BIOGPT_TOKENIZER = AutoTokenizer.from_pretrained(hf_fallback)
            BIOGPT_MODEL = AutoModelForCausalLM.from_pretrained(hf_fallback).to(device)
            print(f"[BioGPT] Model downloaded from HF {hf_fallback} on {device}")

        # BioGPT tokenizer has no default pad token — required for generation
        if BIOGPT_TOKENIZER.pad_token is None:
            BIOGPT_TOKENIZER.pad_token = BIOGPT_TOKENIZER.eos_token
            BIOGPT_MODEL.config.pad_token_id = BIOGPT_TOKENIZER.eos_token_id

        return BIOGPT_MODEL, BIOGPT_TOKENIZER
    except Exception as e:
        print(f"[BioGPT] Failed to load model: {str(e)}")
        return None, None

# ── Medical Pipeline Preprocessing ────────────────────────────────────────────
INDIAN_LAY_DICT = {
    # Conditions
    "hypertension":                  "high BP",
    "diabetes mellitus":             "sugar disease (diabetes)",
    "myocardial infarction":         "heart attack",
    "acute renal failure":           "sudden kidney failure",
    "chronic renal failure":         "long-term kidney problem",
    "septicemia":                    "blood infection (sepsis)",
    "sepsis":                        "serious blood infection",
    "pneumonia":                     "lung infection",
    "tuberculosis":                  "TB (tuberculosis)",
    "pneumothorax":                  "air trapped in chest",
    "endocarditis":                  "infection of heart valves",
    "spondylodiscitis":              "spine bone infection",
    "hypotension":                   "low BP",
    "pyrexia":                       "fever",
    "dyspnea":                       "difficulty in breathing",
    "edema":                         "swelling",
    "abscess":                       "pus-filled swelling",
    "crohn's disease":               "long-term bowel disease (Crohn's)",
    "renal failure":                 "kidney failure",
    "cerebrovascular accident":      "brain stroke",
    "anemia":                        "low blood (anemia)",
    "tachycardia":                   "fast heartbeat",
    "bradycardia":                   "slow heartbeat",
    "atrial fibrillation":           "irregular heartbeat",
    # Procedures & Treatments
    "hemodialysis":                  "kidney dialysis",
    "tracheostomy":                  "breathing tube in neck",
    "thoracotomy":                   "chest surgery",
    "pneumonectomy":                 "removal of a lung",
    "ileocolectomy":                 "removal of part of bowel",
    "anastomosis":                   "surgical joining of bowel ends",
    "debridement":                   "surgical wound cleaning",
    "arteriovenous fistula":         "dialysis access point on arm",
    "intramuscular":                 "given as a muscle injection",
    "intravenous":                   "given through a vein (drip)",
    "percutaneous":                  "through the skin",
    "antibiotic therapy":            "antibiotic treatment",
    "antibiotic":                    "infection-fighting medicine",
    # Lab & Medical Terms
    "blood culture":                 "blood test to find infection",
    "procalcitonin":                 "blood marker for infection",
    "hemoglobin":                    "blood count (Hb)",
    "creatinine":                    "kidney function marker",
    "bilirubin":                     "liver function marker",
    "saturation":                    "oxygen level in blood",
    "afebrile":                      "no fever",
    "eupneic":                       "breathing normally",
    "acyanotic":                     "no bluish discoloration",
    "anicteric":                     "no yellowing of skin/eyes",
    "vesicular breath sounds":       "normal breathing sounds",
    # Hospital / Admin Terms
    "discharge":                     "sent home from hospital",
    "outpatient clinic":             "OPD (Out Patient Department)",
    "follow-up":                     "return visit to doctor",
    "ward":                          "general hospital room",
    "intensive care unit":           "ICU (serious care room)",
    "sus":                           "government health scheme",
    "orally":                        "by mouth",
    "administer":                    "give",
}

def preprocess_medical_text(text):
    if not isinstance(text, str):
        return ""
    # Lowercase and collapse whitespace
    text_clean = re.sub(r"\s+", " ", text.lower()).strip()
    
    # Replace dictionary terms longest-first
    for key in sorted(INDIAN_LAY_DICT.keys(), key=len, reverse=True):
        text_clean = text_clean.replace(key, INDIAN_LAY_DICT[key])
        
    return text_clean

# ── Fixed Few-Shot Examples ───────────────────────────────────────────────────
# 4 curated discharge summary → Indian Lay English pairs used for one-shot / few-shot prompting.
# ONE-SHOT uses Example 4 (ACS/NSTEMI) — most clinically complex, best demonstrates depth expected.
FIXED_EXAMPLES = [
    (
        # Example 1 — Acute Gastroenteritis with Dehydration
        """Patient Name: Michael Smith | Age/Sex: 32/M | Admission: 02/03/2026 | Discharge: 05/03/2026
C/O: Loose stools, vomiting, and abdominal cramps for 3 days.
History: Multiple episodes of watery diarrhea with nausea, repeated vomiting, generalised weakness, and abdominal cramps. No blood in stools. No recent travel.
Past History: Hypothyroidism (2 years).
Examination: Temp 99.8°F | Pulse 112 bpm | BP 100/70 mmHg | RR 20/min | SpO₂ 98%.
Investigations: CBC — mild leukocytosis. Serum Electrolytes — hyponatremia. Stool — no blood/parasites. RFT — mildly elevated creatinine due to dehydration.""",
        """Michael Smith, a 32-year-old man, was admitted on 2nd March 2026 and sent home on 5th March 2026. He came in with 3 days of loose watery stools (loose motions), vomiting, stomach cramps, and weakness. He also has a thyroid problem (hypothyroidism — a condition where the thyroid gland does not make enough hormones, making the body feel slow and tired) for 2 years. On arrival, he had a mild fever (99.8°F; normal is 98.6°F), fast heartbeat (112 beats per minute; normal is 60–100), and low blood pressure (100/70 mmHg; normal is around 120/80). His blood oxygen level was normal at 98%. Blood tests showed a mild rise in infection-fighting white cells (leukocytosis) and low sodium (an important salt in the blood called hyponatremia), which can happen when too much fluid is lost from the body. Stool test showed no blood or infection-causing parasites. His kidney test showed mildly raised creatinine (a marker for kidney function) because of dehydration (lack of enough water in the body). He was treated with fluids and medicines and recovered well before being sent home."""
    ),
    (
        # Example 2 — Acute Exacerbation of Bronchial Asthma
        """Patient Name: Sarah Williams | Age/Sex: 28/F | Admission: 18/02/2026 | Discharge: 21/02/2026
C/O: Wheezing, chest tightness, and breathlessness for 2 days.
History: Worsening shortness of breath, wheezing, and dry cough after dust exposure. Home inhaler not relieving symptoms. No fever or chest pain.
Past History: Bronchial Asthma since childhood. Allergic Rhinitis.
Examination: Temp 98.6°F | Pulse 108 bpm | BP 130/84 mmHg | RR 28/min | SpO₂ 90%.
Investigations: CBC — mild eosinophilia. Chest X-ray — hyperinflation. PEFR — reduced. ABG — mild hypoxemia.""",
        """Sarah Williams, a 28-year-old woman, was admitted on 18th February 2026 and sent home on 21st February 2026. She has had asthma (a long-term condition where the breathing tubes become narrow and make breathing very difficult) since childhood and also has allergic rhinitis (nose allergy). She was brought in with 2 days of wheezing (a whistling sound while breathing), chest tightness, and difficulty in breathing after being exposed to dust. Her home inhaler was not helping enough. On admission, her breathing rate was fast (28 breaths per minute; normal is 12–20) and her blood oxygen level was low at 90% (normal should be above 95%), which means her body was not getting enough oxygen. Blood tests showed a mild rise in allergy cells (eosinophilia — a sign the body is reacting to something). A chest X-ray showed the lungs were over-inflated (hyperinflation — the lungs hold more air than normal during an asthma attack). A breathing speed test (Peak Expiratory Flow Rate) was reduced, confirming the airways were blocked. A blood gas test also confirmed mild low oxygen levels (hypoxemia). She was treated with breathing medicines and nebulisation (medicine given through a breathing mask) and recovered well before discharge."""
    ),
    (
        # Example 3 — Urinary Tract Infection with Pyelonephritis
        """Patient Name: Emily Johnson | Age/Sex: 40/F | Admission: 12/01/2026 | Discharge: 16/01/2026
C/O: Fever, burning micturition, and flank pain for 4 days.
History: High-grade fever with chills, painful and frequent urination, right-sided flank pain. No kidney stones or hematuria.
Past History: Recurrent UTIs. Iron Deficiency Anemia.
Examination: Temp 101.5°F | Pulse 102 bpm | BP 118/76 mmHg | RR 18/min | SpO₂ 99%.
Investigations: Urine Routine — pus cells and bacteria. Urine Culture — E. coli. CBC — elevated WBC. Ultrasound Abdomen — mild right renal pelvic inflammation.""",
        """Emily Johnson, a 40-year-old woman, was admitted on 12th January 2026 and sent home on 16th January 2026. She has a history of recurrent UTIs (urinary tract infections — infections in the tube that carries urine out of the body) and iron deficiency anemia (low blood due to lack of iron). She came in with 4 days of high fever with chills, pain and burning while passing urine (micturition), passing urine much more often than usual, and pain on the right side of her back near the kidney area (flank pain). On admission she had a high temperature of 101.5°F (normal is 98.6°F), fast heartbeat (102 per minute), and normal blood pressure. Urine test showed pus cells and bacteria, confirming an active infection. Urine culture (a test where urine is kept in a lab to see which germs grow) showed E. coli bacteria (a common germ that causes urinary infections). Blood test showed a high white blood cell count, which is a sign the body was fighting a serious infection. An ultrasound scan (a painless scan using sound waves) showed mild swelling and inflammation in the tube leading out of the right kidney (renal pelvis). She was treated with antibiotics (infection-fighting medicines) through a drip and improved well."""
    ),
    (
        # Example 4 — Acute Coronary Syndrome / NSTEMI  [used as the ONE-SHOT example]
        """Patient Name: Robert Brown | Age/Sex: 58/M | Admission: 25/03/2026 | Discharge: 30/03/2026
C/O: Chest pain and sweating for 6 hours.
History: Sudden onset retrosternal chest pain radiating to the left arm, sweating, mild breathlessness. No syncope or trauma.
Past History: Type 2 Diabetes Mellitus (8 years). Hypertension (10 years). Dyslipidemia.
Examination: Temp 98.4°F | Pulse 96 bpm | BP 160/100 mmHg | RR 22/min | SpO₂ 95%.
Investigations: ECG — ST depression in anterior leads. Troponin-I — elevated. 2D Echo — mild left ventricular dysfunction. Lipid Profile — elevated LDL cholesterol.""",
        """Robert Brown, a 58-year-old man, was admitted on 25th March 2026 and sent home on 30th March 2026. He has a history of type 2 diabetes mellitus (sugar disease — a condition where the body cannot properly use or control sugar in the blood) for 8 years, high BP (hypertension) for 10 years, and dyslipidemia (high fat levels in the blood). He came in after 6 hours of sudden chest pain behind the breastbone, which was spreading to his left arm, along with sweating and mild difficulty in breathing. On admission, his blood pressure was high at 160/100 mmHg (normal is 120/80), heartbeat was 96 per minute, and blood oxygen level was 95% (slightly low; should be above 95%). An ECG (a heart tracing test that records electrical signals of the heart) showed ST depression in the front heart leads — a sign of reduced blood supply to the heart muscle. Troponin-I (a protein that leaks into the blood when the heart muscle is damaged) was elevated, confirming a mild heart attack called NSTEMI (Non-ST Elevation Myocardial Infarction — a type of heart attack where one of the heart's blood vessels is partially blocked). A 2D Echo (an ultrasound scan of the heart) showed mild weakness in the left pumping chamber of the heart (left ventricular dysfunction). Blood tests showed high LDL cholesterol (bad cholesterol; normal should be below 100 mg/dL in high-risk patients like him). He was carefully monitored and treated with heart medicines before being sent home."""
    ),
]

# One-shot uses Example 4 (ACS/NSTEMI) — most complex clinical scenario
ONE_SHOT_EXAMPLE = FIXED_EXAMPLES[3]


def build_prompt_string(strategy, text, selection_method="random"):
    """
    Build a unified prompt string.
    strategy: zero-shot | one-shot | few-shot
    Uses fixed curated examples (selection_method param kept for API compatibility but ignored).
    """
    prompt = SYSTEM_PROMPT + "\n\n"
    if strategy == "one-shot":
        orig, simp = ONE_SHOT_EXAMPLE
        prompt += "Here is an example of what I expect:\n\n"
        prompt += f"--- Example ---\nOriginal Medical Text:\n{orig}\n\nSimplified:\n{simp}\n\n"
    elif strategy == "few-shot":
        prompt += "Here are some examples of what I expect:\n\n"
        for i, (orig, simp) in enumerate(FIXED_EXAMPLES):
            prompt += f"--- Example {i+1} ---\nOriginal Medical Text:\n{orig}\n\nSimplified:\n{simp}\n\n"
    prompt += f"--- Your Task ---\nPlease simplify the following discharge summary into Indian Lay English:\n\nOriginal Medical Text:\n{text}\n\nSimplified:\n"
    
    # Print to terminal so you can verify the strategies are actually changing the prompt size
    print(f"\n[DEBUG] build_prompt_string called with strategy: {strategy}")
    print(f"[DEBUG] Generated prompt length: {len(prompt)} characters\n")
    
    return prompt

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/api/models")
def get_models():
    return jsonify({"models": MODELS})


@app.route("/api/simplify", methods=["POST"])
def simplify():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body."}), 400

    raw_text = str(data.get("text", "")).strip()
    if not raw_text:
        return jsonify({"error": "Discharge summary text cannot be empty."}), 400
        
    # Apply Pipeline Preprocessing to standardize input constraint
    text = preprocess_medical_text(raw_text)

    api_provider = str(data.get("api_provider", "auto")).strip().lower()
    strategy = str(data.get("strategy", "zero-shot")).strip().lower() # zero-shot, one-shot, few-shot
    selection_method = str(data.get("selection_method", "random")).strip().lower() # random, similarity

    model_id = str(data.get("model", "llama3.1-8b")).strip()
    model_info = next((m for m in MODELS if m["id"] == model_id), None)
    
    # If frontend sent a specific model, we can try to guess its provider
    if model_info and "api_provider" in model_info and api_provider == "auto":
        api_provider = model_info["api_provider"]

    # ── Try Local Models first ────────────────────────────────────────────────
    if api_provider == "local" or (api_provider == "auto" and model_id in ["scifive-local", "biobart-local", "biogpt-local"]):
        try:
            if model_id == "biobart-local":
                return _call_biobart(text, strategy, selection_method)
            elif model_id == "biogpt-local":
                return _call_biogpt(text, strategy, selection_method)
            return _call_scifive(text, strategy, selection_method)
        except Exception as e:
            if api_provider == "local":
                return jsonify({"error": f"Local model error: {str(e)}"}), 500
            # If "auto", fall through to Cerebras

    # ── Try Cerebras ──────────────────────────────────────────────────────────
    if api_provider == "cerebras" or api_provider == "auto":
        if Cerebras is not None:
            cerebras_key = os.getenv("CEREBRAS_API_KEY", "").strip()
            if cerebras_key:
                try:
                    return _call_cerebras(text, model_id, cerebras_key, strategy, selection_method)
                except Exception as e:
                    if api_provider == "cerebras":
                        return jsonify({"error": f"Cerebras error: {str(e)}"}), 500
                    # If "auto", fall through to Gemini

    # ── Try Gemini ───────────────────────────────────────────────────────────
    if api_provider == "gemini" or api_provider == "auto":
        if genai_client is not None:
            gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
            if gemini_key:
                try:
                    gemini_model = model_id if "gemini" in model_id else "gemini-2.5-flash"
                    return _call_gemini(text, gemini_model, gemini_key, strategy, selection_method)
                except Exception as e:
                    if api_provider == "gemini":
                        return jsonify({"error": f"Gemini error: {str(e)}"}), 500

    # ── Try Groq ─────────────────────────────────────────────────────────────
    if api_provider == "groq" or api_provider == "auto":
        if Groq is not None:
            groq_key = os.getenv("GROQ_API_KEY", "").strip()
            if groq_key:
                try:
                    return _call_groq(text, model_id, groq_key, strategy, selection_method)
                except Exception as e:
                    if api_provider == "groq":
                        return jsonify({"error": f"Groq error: {str(e)}"}), 500

    # ── No valid API configured ───────────────────────────────────────────
    return jsonify({"error": "No valid API configured. Set CEREBRAS_API_KEY, GEMINI_API_KEY, or GROQ_API_KEY in .env"}), 500

def _text_chunk_hf(text, max_words=150, overlap=30):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + max_words
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = end - overlap
    return chunks

def _call_hf_inference(text, hf_repo, prefix="", suffix=""):
    import requests
    import os
    API_URL = f"https://api-inference.huggingface.co/models/{hf_repo}"
    hf_token = os.getenv("HF_TOKEN", "")
    
    if not hf_token:
        from flask import jsonify
        return jsonify({"error": "Missing HF_TOKEN in .env. Please add HF_TOKEN='your_huggingface_token' to the backend/.env file to use Hugging Face inference."}), 502

    headers = {"Authorization": f"Bearer {hf_token}"}
    
    chunks = _text_chunk_hf(text)
    outputs = []
    
    for chunk in chunks:
        payload = {
            "inputs": prefix + chunk + suffix,
            "parameters": {
                "max_new_tokens": 512,
                "num_beams": 4,
                "length_penalty": 1.5,
                "early_stopping": True,
                "no_repeat_ngram_size": 4
            }
        }
        res = requests.post(API_URL, headers=headers, json=payload)
        
        if res.status_code != 200:
            return jsonify({"error": f"HF API Error ({res.status_code}): {res.text}"}), 502
            
        json_res = res.json()
        if isinstance(json_res, list) and "generated_text" in json_res[0]:
            out_text = json_res[0]["generated_text"]
            out_text = out_text.replace(prefix + chunk + suffix, "").strip()
            outputs.append(out_text)
        elif "error" in json_res:
            return jsonify({"error": f"HF API Model Error: {json_res['error']}"}), 502
            
    return " ".join(outputs)

def _call_scifive(text, strategy="zero-shot", selection_method="random"):
    res = _call_hf_inference(text, "11Raghav/SciFive", prefix="lay simplify preserving all details: ")
    if isinstance(res, tuple): return res 
    model_info = next((m for m in MODELS if m["id"] == "scifive-local"), None)
    return jsonify({"result": res, "model": model_info["name"] if model_info else "SciFive", "tokens": None})

def _call_biobart(text, strategy="zero-shot", selection_method="random"):
    res = _call_hf_inference(text, "11Raghav/BioBART")
    if isinstance(res, tuple): return res 
    model_info = next((m for m in MODELS if m["id"] == "biobart-local"), None)
    return jsonify({"result": res, "model": model_info["name"] if model_info else "BioBART", "tokens": None})

def _call_biogpt(text, strategy="zero-shot", selection_method="random"):
    res = _call_hf_inference(text, "11Raghav/BioGPT", prefix="lay simplify preserving all details: ", suffix="\n### Simplified: ")
    if isinstance(res, tuple): return res 
    model_info = next((m for m in MODELS if m["id"] == "biogpt-local"), None)
    return jsonify({"result": res, "model": model_info["name"] if model_info else "BioGPT", "tokens": None})

def _call_cerebras(text, model_id, api_key, strategy="zero-shot", selection_method="random"):
    """Call Cerebras API."""
    if Cerebras is None:
        raise Exception("cerebras-cloud-sdk is not installed")

    # Reject if model is not accessible
    model_info = next((m for m in MODELS if m["id"] == model_id), None)
    if model_info and not model_info["accessible"]:
        raise Exception(
            f"'{model_info['name']}' is not accessible with your current API key. "
            "Please select Llama 3.1 8B."
        )

    client = Cerebras(api_key=api_key)
    
    # Use identical prompt generation for both Cerebras and Gemini
    prompt_content = build_prompt_string(strategy, text, selection_method)
    
    response = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "user", "content": prompt_content},
        ],
        max_tokens=2048,
        temperature=0.3,
    )
    simplified = response.choices[0].message.content
    tokens_used = getattr(response.usage, "total_tokens", None)
    display_name = model_info["name"] if model_info else model_id
    return jsonify({"result": simplified, "model": display_name, "tokens": tokens_used})


def _call_gemini(text, model_id, api_key, strategy="zero-shot", selection_method="random"):
    """Call Google Gemini API using google-genai SDK."""
    if genai_client is None:
        raise Exception("google-genai is not installed")

    client = genai_client.Client(api_key=api_key)
    prompt_content = build_prompt_string(strategy, text, selection_method)

    response = client.models.generate_content(
        model=model_id,
        contents=prompt_content,
        config=genai_types.GenerateContentConfig(
            max_output_tokens=8192,
            temperature=0.3,
        ),
    )

    simplified = response.text
    model_info = next((m for m in MODELS if m["id"] == model_id), None)
    display_name = model_info["name"] if model_info else model_id
    try:
        tokens_used = response.usage_metadata.total_token_count
    except Exception:
        tokens_used = None
    return jsonify({"result": simplified, "model": display_name, "tokens": tokens_used})


def _call_groq(text, model_id, api_key, strategy="zero-shot", selection_method="random"):
    """Call Groq API."""
    if Groq is None:
        raise Exception("groq package is not installed")

    model_info = next((m for m in MODELS if m["id"] == model_id), None)
    # Default to a known fast Groq model if the selected model isn't a Groq one
    groq_model = model_id if model_info and model_info.get("api_provider") == "groq" else "llama-3.3-70b-versatile"

    client = Groq(api_key=api_key)
    prompt_content = build_prompt_string(strategy, text, selection_method)

    response = client.chat.completions.create(
        model=groq_model,
        messages=[
            {"role": "user", "content": prompt_content},
        ],
        max_tokens=2048,
        temperature=0.3,
    )
    simplified = response.choices[0].message.content
    tokens_used = getattr(response.usage, "total_tokens", None)
    display_name = model_info["name"] if model_info else groq_model
    return jsonify({"result": simplified, "model": display_name, "tokens": tokens_used})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(debug=True, port=port)

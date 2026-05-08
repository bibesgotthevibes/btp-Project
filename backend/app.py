"""
backend/app.py — MedSimplify Flask REST API
============================================
Run:
    cd backend
    pip install -r requirements.txt
    flask run --port 5000
"""

import os
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
    import google.generativeai as genai
except ImportError:
    genai = None

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
    # ── Allowed models only ───────────────────────────────────────────────────
    {"id": "scifive-local", "name": "SciFive (Local T5)", "accessible": True, "api_provider": "local"},
    {"id": "biobart-local", "name": "BioBART (Local)", "accessible": True, "api_provider": "local"},
    {"id": "biogpt-local", "name": "BioGPT (Local)", "accessible": True, "api_provider": "local"},
    {"id": "llama3.1-8b", "name": "Llama 3.1 8B", "accessible": True, "api_provider": "cerebras"},
]

SYSTEM_PROMPT = (
    "You are a medical language simplification assistant that converts complex "
    "clinical discharge summaries into simple, easy-to-understand Indian Lay English "
    "for patients and their families.\n\n"
    "Rules:\n"
    "1. Keep every medical term but immediately explain it in plain words in "
    "parentheses, e.g. 'hypertension (high blood pressure)'.\n"
    "2. Use simple language a 6th-grader can understand. Avoid jargon.\n"
    "3. Preserve ALL factual information — never add or remove clinical facts.\n"
    "4. Structure your output with clearly labelled sections:\n"
    "   • Patient Summary\n"
    "   • Diagnosis\n"
    "   • Treatment Given\n"
    "   • Medications\n"
    "   • Follow-up Instructions\n"
    "   • Warning Signs to Watch For\n"
    "5. For any measurement (e.g. blood pressure, blood sugar), add brief context "
    "about what is normal vs. abnormal.\n"
    "6. Use empathetic, reassuring language.\n"
    "7. Write in second or third person as appropriate to match the original summary."
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
    hf_fallback = "razent/SciFive-base-Pubmed_Pmc"
    
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
    hf_fallback = "GanjinZero/biobart-v2-base"

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
    hf_fallback = "microsoft/biogpt"

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

# ── Load Examples for Few-Shot Prompting ──────────────────────────────────────
ALL_EXAMPLES = []
try:
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "data.tsv")
    with open(data_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        headers = next(reader)
        # Find column indices
        orig_idx = headers.index("original")
        simp_idx = headers.index("english simplified")
        for row in reader:
            if len(row) > max(orig_idx, simp_idx):
                original = row[orig_idx].strip()
                simplified = row[simp_idx].strip()
                if original and simplified:
                    ALL_EXAMPLES.append((original, simplified))
except Exception as e:
    print(f"Warning: Could not load data.tsv for few-shot examples... {e}")

def get_best_examples(text, num_examples, selection_method):
    if not ALL_EXAMPLES:
        return []
    if num_examples >= len(ALL_EXAMPLES):
        return ALL_EXAMPLES
        
    if selection_method == "random":
        return random.sample(ALL_EXAMPLES, num_examples)
        
    elif selection_method == "similarity":
        # Pure Python Jaccard similarity based on words
        text_words = set(text.lower().split())
        
        def calc_sim(ex):
            orig_words = set(ex[0].lower().split())
            if not text_words or not orig_words: return 0
            return len(text_words.intersection(orig_words)) / len(text_words.union(orig_words))
            
        scored_examples = [(ex, calc_sim(ex)) for ex in ALL_EXAMPLES]
        scored_examples.sort(key=lambda x: x[1], reverse=True)
        return [ex for ex, score in scored_examples[:num_examples]]
        
    # Default fallback (first N)
    return ALL_EXAMPLES[:num_examples]

def build_prompt_string(strategy, text, selection_method="random"):
    """
    Build a unified prompt string incorporating few-shot examples if requested.
    """
    prompt = SYSTEM_PROMPT + "\n\n"
    if strategy in ["one-shot", "few-shot"] and ALL_EXAMPLES:
        num_examples = 1 if strategy == "one-shot" else min(3, len(ALL_EXAMPLES))
        examples = get_best_examples(text, num_examples, selection_method)
        
        prompt += "Here are some examples of what I expect:\n\n"
        for i, (original, simplified) in enumerate(examples):
            prompt += f"--- Example {i+1} ---\nOriginal Medical Text:\n{original}\n\nSimplified:\n{simplified}\n\n"
            
    prompt += f"--- Your Task ---\nPlease simplify the following discharge summary into Indian Lay English:\n\nOriginal Medical Text:\n{text}\n\nSimplified:\n"
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

    # ── Fall back to Gemini ───────────────────────────────────────────────
    if api_provider == "gemini" or api_provider == "auto":
        if genai is not None:
            gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
            if gemini_key:
                try:
                    # Provide Gemini model explicitly, default to flash if not found
                    gemini_model = model_id if "gemini" in model_id else "gemini-2.5-flash"
                    return _call_gemini(text, gemini_model, gemini_key, strategy, selection_method)
                except Exception as e:
                    return jsonify({"error": f"Gemini error: {str(e)}"}), 500

    # ── No valid API configured ───────────────────────────────────────────
    return jsonify({"error": "No valid API configured. Set CEREBRAS_API_KEY or GEMINI_API_KEY in .env"}), 500


def _call_scifive(text, strategy="zero-shot", selection_method="random"):
    """Call local SciFive model (fine-tuned T5)."""
    model, tokenizer = load_scifive()
    if model is None or tokenizer is None:
        return jsonify({"error": "SciFive model is currently unavailable."}), 503

    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    simplified = generate_scifive_chunked(text, model, tokenizer, device)
    
    model_info = next((m for m in MODELS if m["id"] == "scifive-local"), None)
    display_name = model_info["name"] if model_info else "SciFive"
    
    return jsonify({"result": simplified, "model": display_name, "tokens": None})


def _call_biobart(text, strategy="zero-shot", selection_method="random"):
    """Call local BioBART model."""
    model, tokenizer = load_biobart()
    if model is None or tokenizer is None:
        return jsonify({"error": "BioBART model is currently unavailable."}), 503

    device = "cuda" if torch.cuda.is_available() else "cpu"

    simplified = generate_biobart_chunked(text, model, tokenizer, device)

    model_info = next((m for m in MODELS if m["id"] == "biobart-local"), None)
    display_name = model_info["name"] if model_info else "BioBART"

    return jsonify({"result": simplified, "model": display_name, "tokens": None})


def _call_biogpt(text, strategy="zero-shot", selection_method="random"):
    """Call local BioGPT model."""
    model, tokenizer = load_biogpt()
    if model is None or tokenizer is None:
        return jsonify({"error": "BioGPT model is currently unavailable."}), 503

    device = "cuda" if torch.cuda.is_available() else "cpu"

    simplified = generate_biogpt_chunked(text, model, tokenizer, device)

    model_info = next((m for m in MODELS if m["id"] == "biogpt-local"), None)
    display_name = model_info["name"] if model_info else "BioGPT"

    return jsonify({"result": simplified, "model": display_name, "tokens": None})


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
    """Call Google Gemini API."""
    if genai is None:
        raise Exception("google-generativeai is not installed")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_id)
    
    prompt_content = build_prompt_string(strategy, text, selection_method)
    
    response = model.generate_content(
        prompt_content,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=2048,
            temperature=0.3,
        ),
    )
    
    simplified = response.text
    return jsonify({"result": simplified, "model": f"{model_id} (Google)", "tokens": None})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(debug=True, port=port)

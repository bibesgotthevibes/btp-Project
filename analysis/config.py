"""
analysis/config.py
──────────────────
Configuration and environment setup for comparative analysis across models,
providers, prompt variations, and medical document types.
"""

import os
from pathlib import Path
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(dotenv_path=None):
        if dotenv_path and os.path.exists(dotenv_path):
            try:
                with open(dotenv_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'").strip('"')
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATASETS_DIR = PROJECT_ROOT / "datasets"
RESULTS_DIR = BASE_DIR / "results"
CHECKPOINTS_DIR = RESULTS_DIR / ".checkpoints"

# Ensure directories exist
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Load environment variables (.env files) ───────────────────────────────────
load_dotenv(BASE_DIR / ".env")
load_dotenv(PROJECT_ROOT / ".env")

def clean_api_key(val: str) -> str:
    k = (val or "").strip()
    if not k or "your_" in k.lower() or "placeholder" in k.lower() or "<" in k:
        return ""
    return k

# ── API Keys (ALL OPTIONAL — script will attempt if provided) ──────────────────
GEMINI_API_KEY = clean_api_key(os.getenv("GEMINI_API_KEY", ""))
CEREBRAS_API_KEY = clean_api_key(os.getenv("CEREBRAS_API_KEY", ""))
GROQ_API_KEY = clean_api_key(os.getenv("GROQ_API_KEY", ""))

# ── Default Model IDs & Endpoints ─────────────────────────────────────────────
# Verified 2026-10-08 against the Gemini/Groq /models endpoints (free tier):
#   gemini/3.8flash  -> gemini-3.8-flash
#   (one Gemini model only: free-tier quota is small; 3.1-pro-preview has no free quota, 2.5-pro retired)
#   cerebras/gptoss  -> gpt-oss-120b on Cerebras, else Groq openai/gpt-oss-120b
#   cerebras/qwen3.8 -> qwen-3.8-27b on Cerebras, else Groq qwen/qwen3.8-27b

MODEL_ENDPOINTS = {
    # Gemini
    "gemini/3.8flash": {
        "provider": "gemini",
        "model_id": os.getenv("GEMINI_FLASH_MODEL", "gemini-3.8-flash"),
        "fallback_models": ["gemini-3.5-flash"],
        "display_name": "Gemini 3.8 Flash",
    },
    # Cerebras with Groq fallback
    "cerebras/gptoss": {
        "provider": "cerebras",
        "fallback_provider": "groq",
        "model_id": os.getenv("CEREBRAS_GPTOSS_MODEL", "gpt-oss-120b"),
        "groq_model_id": os.getenv("GROQ_GPTOSS_MODEL", "openai/gpt-oss-120b"),
        "fallback_models": ["openai/gpt-oss-120b", "openai/gpt-oss-20b"],
        "display_name": "GPT-OSS (Cerebras/Groq)",
    },
    "cerebras/qwen3.8": {
        "provider": "cerebras",
        "fallback_provider": "groq",
        "model_id": os.getenv("CEREBRAS_QWEN_MODEL", "qwen-3.8-27b"),
        "groq_model_id": os.getenv("GROQ_QWEN_MODEL", "qwen/qwen3.8-27b"),
        "fallback_models": ["qwen/qwen3.8-27b"],
        "display_name": "Qwen 3.8 (Cerebras/Groq)",
    },
}

# Local Ollama models (no key): LOCAL_MODELS="llama3.1:8b,medgemma:4b" (not OLLAMA_MODELS: Ollama uses that for its storage path).
for _tag in filter(None, (t.strip() for t in os.getenv("LOCAL_MODELS", "llama3.1:8b").split(","))):
    MODEL_ENDPOINTS[f"ollama/{_tag}"] = {
        "provider": "ollama",
        "model_id": _tag,
        "display_name": f"{_tag} (Ollama, local)",
    }

# ── API Endpoints ─────────────────────────────────────────────────────────────
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
CEREBRAS_API_URL = "https://api.cerebras.ai/v1/chat/completions"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ── Retry & Timeout Settings ──────────────────────────────────────────────────
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 5.0  # seconds
REQUEST_TIMEOUT = 120      # seconds

# ── Experiment Grid Dimensions ────────────────────────────────────────────────
TASKS = ["summarization", "simplification"]
DATATYPES = ["discharge", "pathology", "radiology"]
STRATEGIES = ["zero-shot", "few-shot", "ner-guided"]
MODELS = list(MODEL_ENDPOINTS.keys())

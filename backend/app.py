"""
backend/app.py — MedSimplify Flask REST API
============================================
Run:
    cd backend
    pip install -r requirements.txt
    flask run --port 5000
"""

import os
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

from db import db
from auth import auth_bp

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

# ── Cerebras model catalogue ──────────────────────────────────────────────────
# accessible=True  → works with a standard Cerebras API key
# accessible=False → exists on Cerebras but requires a higher-tier key
CEREBRAS_MODELS = [
    {"id": "llama3.1-8b",                    "name": "Llama 3.1 8B",                    "accessible": True},
    {"id": "llama-4-scout-17b-16e-instruct",  "name": "Llama 4 Scout 17B",               "accessible": False},
    {"id": "llama3.3-70b",                    "name": "Llama 3.3 70B",                   "accessible": False},
    {"id": "llama3.1-70b",                    "name": "Llama 3.1 70B",                   "accessible": False},
    {"id": "deepseek-r1-distill-llama-70b",   "name": "DeepSeek R1 Distill Llama 70B",   "accessible": False},
    {"id": "qwen-3-32b",                      "name": "Qwen 3 32B",                      "accessible": False},
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

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/api/models")
def get_models():
    return jsonify({"models": CEREBRAS_MODELS})


@app.route("/api/simplify", methods=["POST"])
def simplify():
    if Cerebras is None:
        return jsonify({"error": "cerebras-cloud-sdk is not installed on the server."}), 500

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body."}), 400

    api_key = os.getenv("CEREBRAS_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "Cerebras API key is not configured on the server."}), 500

    text = str(data.get("text", "")).strip()
    if not text:
        return jsonify({"error": "Discharge summary text cannot be empty."}), 400

    model_id = str(data.get("model", "llama3.1-8b")).strip()

    # Reject if model is not accessible
    model_info = next((m for m in CEREBRAS_MODELS if m["id"] == model_id), None)
    if model_info and not model_info["accessible"]:
        return jsonify({
            "error": (
                f"'{model_info['name']}' is not accessible with your current API key. "
                "Please select Llama 3.1 8B."
            )
        }), 403

    try:
        client = Cerebras(api_key=api_key)
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Please simplify the following discharge summary into "
                        "Indian Lay English:\n\n" + text
                    ),
                },
            ],
            max_tokens=2048,
            temperature=0.3,
        )
        simplified = response.choices[0].message.content
        tokens_used = getattr(response.usage, "total_tokens", None)
        return jsonify({"result": simplified, "model": model_id, "tokens": tokens_used})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(debug=True, port=port)

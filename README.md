# MedSimplify 🏥

A full-stack web application that simplifies complex medical discharge summaries into **Indian Lay English**, making healthcare information accessible to patients and their families. This tool leverages both Cloud AI (Gemini, Groq, Cerebras) and custom Fine-Tuned Local PyTorch Models (SciFive, BioBART, BioGPT).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, Axios |
| Backend | Python Flask, Flask-JWT-Extended, PyTorch, HuggingFace Transformers |
| Database | PostgreSQL + SQLAlchemy ORM |
| AI Cloud APIs | Google GenAI (Gemini), Groq, Cerebras Cloud SDK |
| AI Local Models | SciFive (T5), BioBART, BioGPT (Causal LM) |

---

## Project Structure

```
btp-Project/
├── backend/
│   ├── app.py              # Main Flask REST API 
│   ├── chunking_logic.py   # Sliding-window inference logic for long documents
│   ├── auth.py             # Auth endpoints (/register, /login, /me)
│   ├── db.py               # SQLAlchemy db instance
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── pages/          # Dashboard, Login, Register
│   │   ├── components/     # UI Components (OutputPanel, AuthCard, etc.)
│   │   ├── api/            # Axios instance with JWT interceptor
│   └── package.json        
└── .env                    # Environment variables & API Keys
```

---

## Prerequisites

- **Python 3.9+**
- **Node.js 18+**
- **PostgreSQL** (running locally)
- API Keys for one (or more) of the supported Cloud APIs (optional if only using local weights):
  - [Gemini API Key](https://aistudio.google.com/)
  - [Groq API Key](https://console.groq.com/)
  - [Cerebras API Key](https://cloud.cerebras.ai)

---

## Installation & Setup

### 1. Clone the repository & Database
```bash
git clone <your-repo-url>
cd btp-Project

# Create the PostgreSQL database locally
createdb medsimplify
```

### 2. Configure Environment Variables
Create a `.env` file in the project root containing your database configs and API keys:

```env
# Cloud AI Keys
CEREBRAS_API_KEY="your_cerebras_key"
GEMINI_API_KEY="your_gemini_key"
GROQ_API_KEY="your_groq_key"

# Database & Auth
DATABASE_URL="postgresql://localhost:5432/medsimplify"
JWT_SECRET_KEY="your_jwt_secret_key"
PORT=5001
```

### 3. Backend Setup
Set up the Python virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
cd backend
pip install -r requirements.txt
cd ..
```

### 4. Start the Backend Server
```bash
source .venv/bin/activate
cd backend
python3 app.py
```
> The Flask API will start on **http://localhost:5001** and auto-create the database tables upon first request.

### 5. Frontend Setup & Run
Open a **new terminal** window:
```bash
cd frontend
npm install
npm run dev
```
> The React Vite app will launch on **http://localhost:5173** (or 5174). Look for the local link in your terminal. All `/api/*` frontend fetches automatically proxy to `5001`.

---

## Inference Modes & AI Features

### 1. Cloud Prompts (Zero-Shot, One-Shot, Few-Shot)
The UI allows you to select advanced reasoning modes. Cloud LLMs (Gemini, Llama via Cerebras/Groq) are injected with a highly specific system prompt containing 11 strict rules (handling tone, absolute dates, measurements, and jargon translation). Selecting "Few-Shot" injects curated Gold-Standard clinical examples into the JSON payload prior to your document, increasing reliability.

### 2. Local Models (SciFive, BioGPT, BioBART)
The backend supports processing summaries entirely locally for strict privacy. 
- **Chunked Architecture:** Because clinical discharge summaries frequently exceed the 512/1024 token maximum boundaries, the backend automatically tokenizes and runs a sliding-window chunk generation (e.g., 400 chunk size with 50 overlap). This replicates the training pipelines perfectly.
- **HuggingFace Fallback:** The backend dynamically searches for base models locally in their respective folders (`SciFive/model/`, `BioBART/model/`, `BioGPT/model/`). If the directories represent fine-tuned weights and aren't found locally, PyTorch will automatically download the base model weights from the Hugging Face Hub (e.g., `razent/SciFive-base-Pubmed_Pmc` or `microsoft/biogpt`).
- **No Hallucinations:** Engineered min-length ceilings dynamically drop to 0 on small trailing text chunks to elegantly stop iteration, preventing models from repeating sentences endlessly.

---

## Research Context

This project is part of a B.Tech / M.Tech research initiative on **simplification of medical discharge summaries**. Core experimental data and analysis scripts live alongside the codebase:
- `medical_lay_english_pipeline.py` & `.ipynb` — Fine-tuning logic and Kaggle execution scripts
- `pipeline_documentation.md` — Technical documentation of the training process
- `_analyze.py` & `make_report.py` — Quality scoring and validation data (BLEU, ROUGE, length analysis)

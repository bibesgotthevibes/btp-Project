# MedSimplify 🏥

A full-stack web application that simplifies complex medical discharge summaries into **Indian Lay English**, making healthcare information accessible to patients and their families. This tool leverages both Cloud AI (Gemini, Groq, Cerebras) and custom Fine-Tuned Local PyTorch Models (SciFive, BioBART, BioGPT).

---

## 🚀 Live Demo & AWS Deployment

**Live App URL:** [http://16.171.200.81/](http://16.171.200.81/)

*Note on AWS Free Tier:* The app runs on an AWS EC2 instance. Due to the strict 1GB RAM memory constraints of the AWS Free Tier, the heavy local PyTorch models (SciFive, BioBART, BioGPT) cannot be loaded directly into memory without causing an out-of-memory crash. However, **all Cloud LLM API-based models (Gemini, Llama 3 via Groq & Cerebras) are fully functional** on the live demo!

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, Axios |
| Backend | Python Flask, Flask-JWT-Extended, PyTorch, HuggingFace Transformers |
| Database | SQLite + SQLAlchemy ORM |
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
- API Keys for one (or more) of the supported Cloud APIs (optional if only using local weights):
  - [Gemini API Key](https://aistudio.google.com/)
  - [Groq API Key](https://console.groq.com/)
  - [Cerebras API Key](https://cloud.cerebras.ai)
  - [Hugging Face Token](https://huggingface.co/settings/tokens) (Optional, for downloading fine-tuned weights)

---

## Installation & Setup

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd btp-Project
```

### 2. Configure Environment Variables
Create a `.env` file in the project root containing your database config and API keys. The app uses a local auto-created SQLite database by default.

```env
# Cloud AI Keys
CEREBRAS_API_KEY="your_cerebras_key"
GEMINI_API_KEY="your_gemini_key"
GROQ_API_KEY="your_groq_key"
HF_TOKEN="your_huggingface_token"

# Database & Auth
DATABASE_URL="sqlite:///medsimplify.db"
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

### 4. Running the App

To run the app continuously in the background (ideal for EC2 or local background processing), use **PM2** to run both the frontend and backend using the provided `ecosystem.config.js`.

```bash
# Install PM2 globally if you haven't already
npm install -g pm2

# Build the frontend setup
cd frontend
npm install
npm run build
cd ..

# Start both backend and frontend using the ecosystem file
pm2 start ecosystem.config.js

# To view logs or manage processes:
pm2 logs
pm2 status
pm2 restart all
```

---

## Inference Modes & AI Features

### 1. Cloud Prompts (Zero-Shot, One-Shot, Few-Shot)
The UI allows you to select advanced reasoning modes. Cloud LLMs (Gemini, Llama via Cerebras/Groq) are injected with a highly specific system prompt containing 11 strict rules (handling tone, absolute dates, measurements, and jargon translation). Selecting "Few-Shot" injects curated Gold-Standard clinical examples into the JSON payload prior to your document, increasing reliability.

### 2. Local Models (SciFive, BioGPT, BioBART)
The backend supports processing summaries entirely locally for strict privacy. 
- **Chunked Architecture:** Because clinical discharge summaries frequently exceed the 512/1024 token maximum boundaries, the backend automatically tokenizes and runs a sliding-window chunk generation (e.g., 400 chunk size with 50 overlap). This replicates the training pipelines perfectly.
- **HuggingFace Auto-Download (Fallback):** The backend dynamically searches for model weight folders locally (`SciFive/model/`, `BioBART/model/`, `BioGPT/model/`). If you don't have the folders downloaded, PyTorch will automatically download the custom fine-tuned weights directly from the Hugging Face Hub (e.g., `11Raghav/SciFive`, `11Raghav/BioBART`, `11Raghav/BioGPT`) and load them into memory automatically cleanly!
- **Download Model Weights (Google Drive):** If you prefer to download the weights manually instead of letting Hugging Face auto-download them, you can download the local PyTorch `model.safetensors` packages directly:
  - 📂 **SciFive:** [Insert SciFive Google Drive Link Here]
  - 📂 **BioBART:** [Insert BioBART Google Drive Link Here]
  - 📂 **BioGPT:** [Insert BioGPT Google Drive Link Here]
- **No Hallucinations:** Engineered min-length ceilings dynamically drop to 0 on small trailing text chunks to elegantly stop iteration, preventing models from repeating sentences endlessly.

---

## Research Context

This project is part of a B.Tech / M.Tech research initiative on **simplification of medical discharge summaries**. Core experimental data and analysis scripts live alongside the codebase:
- `medical_lay_english_pipeline.py` & `.ipynb` — Fine-tuning logic and Kaggle execution scripts
- `pipeline_documentation.md` — Technical documentation of the training process
- `_analyze.py` & `make_report.py` — Quality scoring and validation data (BLEU, ROUGE, length analysis)

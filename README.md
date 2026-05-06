# MedSimplify 🏥

A full-stack web application that simplifies complex medical discharge summaries into **Indian Lay English** using Cerebras LLMs — making healthcare information accessible to patients and their families.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, Axios |
| Backend | Python Flask, Flask-JWT-Extended |
| Database | PostgreSQL + SQLAlchemy ORM |
| AI | Cerebras Cloud SDK (Llama 3.1 8B) |

---

## Project Structure

```
BTP_MT/
├── backend/
│   ├── app.py          # Flask REST API (simplify, models, JWT setup, CORS)
│   ├── auth.py         # /register, /login, /me endpoints
│   ├── models.py       # User SQLAlchemy model
│   ├── db.py           # SQLAlchemy instance
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/      # Login, Register, Dashboard
│   │   ├── components/ # Button, InputField, AuthCard, Navbar, OutputPanel, Loader
│   │   ├── api/        # Axios instance with JWT interceptor
│   │   └── App.jsx     # Routing + session restore
│   ├── package.json
│   └── vite.config.js
├── run_backend.sh       # One-command backend launcher
└── .env                 # Secrets (not committed)
```

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL (running locally)
- A [Cerebras Cloud](https://cloud.cerebras.ai) API key

---

## Setup & Run

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/medsimplify.git
cd medsimplify
```

### 2. Create the PostgreSQL database

```bash
createdb medsimplify
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
CEREBRAS_API_KEY="your_cerebras_api_key_here"
JWT_SECRET_KEY="a-strong-random-secret"
DATABASE_URL="postgresql://<your-pg-username>@localhost:5432/medsimplify"
PORT=5001
```

> **macOS note:** Port 5000 is reserved by AirPlay. The backend uses port **5001**.

### 4. Set up the Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 5. Start the backend

```bash
# Option A — using the helper script (recommended)
./run_backend.sh

# Option B — manually (venv must be active)
source .venv/bin/activate
python3 backend/app.py
```

Flask starts at **http://localhost:5001**  
Tables are auto-created on first run via SQLAlchemy.

### 6. Start the frontend

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite starts at **http://localhost:5174**  
All `/api/*` requests are proxied to `http://localhost:5001` automatically.

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register` | No | Create account |
| POST | `/api/auth/login` | No | Login, returns JWT |
| GET | `/api/auth/me` | JWT | Get current user |
| GET | `/api/models` | No | List available Cerebras models |
| POST | `/api/simplify` | No* | Simplify discharge summary |

> `*` API key is read from server `.env`, not the client.

### Model access

| Model | Status |
|---|---|
| Llama 3.1 8B | ✓ Available with standard key |
| Llama 4 Scout 17B, Llama 3.3 70B, etc. | 🔒 Requires higher-tier Cerebras key |

---

## Features

- JWT authentication (7-day tokens, stored in localStorage)
- Protected `/dashboard` route with auto session restore
- Discharge summary simplification structured output:
  - Patient Summary · Diagnosis · Treatment · Medications · Follow-up · Warning Signs
- **Download PDF** of the simplified summary (client-side, jsPDF)
- **Copy to clipboard** button
- Model dropdown showing accessible vs. locked models

---

## Research Context

This project is part of a B.Tech / M.Tech research project on **simplification of medical discharge summaries** using LLMs. The pipeline research (IndicBART fine-tuning, entity preservation, hallucination gating) lives in:

- `medical_lay_english_pipeline.ipynb` — Kaggle GPU pipeline
- `pipeline_documentation.md` — Full technical documentation
- `_analyze.py` — Quality analysis scripts
- `make_report.py` — HTML/Excel report generation

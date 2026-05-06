#!/bin/bash
# Run the MedSimplify Flask backend using the project's .venv
cd "$(dirname "$0")"
source .venv/bin/activate
cd backend
python3 app.py

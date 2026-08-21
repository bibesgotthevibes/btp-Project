# Structured Medical Information Extraction

This module extracts structured medical knowledge from hospital discharge summaries using LLM APIs.

## Overview

Reads discharge summaries from `anotated_dataset_v2.xlsx` and sends them to **Groq** (`qwen/qwen3.6-27b`) and **Cerebras** (`gemma-4-31b`) LLMs with a carefully crafted few-shot prompt. The LLMs return structured JSON containing:

- **Patient demographics** (age, gender)
- **Diagnoses** (primary + secondary, with patient-friendly lay explanations)
- **Symptoms at admission**
- **Anomalies detected** (vital signs, lab results, imaging findings + severity)
- **Procedures performed** (with lay explanations)
- **Medications** (name, purpose in simple words, dosage/timing)
- **Warning signs / red flags** (when to return to hospital)
- **Follow-up care** (appointments, ongoing treatments, lifestyle advice)
- **Outcome** and **length of stay**

## Setup

```bash
# Only dependency needed (standard library handles HTTP calls)
pip install openpyxl
```

## Usage

```bash
cd structured_extraction
python extract_structured_info.py
```

## Output

Results are saved in the `results/` folder:

| File | Description |
|------|-------------|
| `groq_extractions.json` | Structured extractions from Groq LLM |
| `cerebras_extractions.json` | Structured extractions from Cerebras LLM |
| `comparison_summary.json` | Side-by-side comparison with timing metrics |

## Files

| File | Purpose |
|------|---------|
| `extract_structured_info.py` | Main script — reads Excel, calls APIs, saves results |
| `prompt_template.py` | System prompt + few-shot gold-standard example |
| `schema.py` | JSON validation for extracted output |

## Prompt Strategy

Uses **one-shot prompting** with a real discharge summary from the dataset as the example. The gold-standard expected output demonstrates:
- How to structure diagnoses with ICD codes
- How to write lay English explanations
- How to classify anomaly severity
- How to extract medication timing/dosage
- How to infer warning signs even when not explicitly listed

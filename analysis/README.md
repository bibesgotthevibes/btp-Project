# Comparative Analysis & Evaluation Framework 🔬

A modular, resilient benchmarking pipeline designed to systematically evaluate and compare LLMs across medical document types, clinical tasks, and prompt engineering strategies prior to expanding the `btp-lite` application.

---

## 📌 Benchmark Dimensions

| Dimension | Options / Values | Description |
|---|---|---|
| **Tasks (2)** | `simplification`, `summarization` | Lay translation (6th-grade Indian English for families) vs. structured clinical synthesis for physicians. |
| **Datatypes (3)** | `discharge`, `pathology`, `radiology` | Curated across 3 clinical repositories (5 diverse samples each = 15 total). |
| **Models (4)** | `cerebras/gptoss`<br>`cerebras/qwen3.8`<br>`gemini/3.8flash`<br>`gemini/3.1pro` | Primary endpoints: `gemini-3.8-flash`, `gemini-3.1-pro-preview`, Cerebras `gpt-oss`/`qwen-3.8` with Groq fallback (`openai/gpt-oss-20b`, `qwen/qwen3.6-27b`). |
| **Prompt Strategies (2)** | `zero-shot`, `few-shot` | Direct rule-based constraints vs. curated clinical in-context exemplars. |
| **Total Experiment Grid** | **240 unique combinations** | $2\text{ tasks} \times 15\text{ samples} \times 4\text{ models} \times 2\text{ strategies}$. |

---

## 📁 Directory Structure

```
analysis/
├── config.py                 # API keys, endpoints, retry logic, grid constants
├── samples/
│   ├── loader.py             # Dataset reader from datasets/ directory
│   └── curated_samples.py    # 15 curated samples with clean text & metadata
├── prompts/
│   ├── discharge_prompts.py  # Zero/Few-shot prompts for Discharge Summaries (derived from btp-lite)
│   ├── pathology_prompts.py  # Zero/Few-shot prompts for Pathology (resection, IHC, Gleason, margins)
│   ├── radiology_prompts.py  # Zero/Few-shot prompts for Radiology (MRI, bone lesions, abscesses, ischemia)
│   └── builder.py            # Unified prompt assembler dispatching (task, datatype, strategy)
├── providers/
│   ├── base.py               # Abstract provider interface & GenerationResult dataclass
│   ├── gemini_provider.py    # Google Gemini API caller (REST generateContent + retry/backoff)
│   ├── cerebras_provider.py  # Cerebras API caller (REST OpenAI-compatible + retry/backoff)
│   ├── groq_provider.py      # Groq API caller (fallback for gpt-oss and qwen)
│   └── router.py             # Model-to-provider dispatch and resolution engine
├── metrics/
│   ├── readability.py        # FKGL, Flesch Reading Ease, SMOG, Gunning Fog, Coleman-Liau
│   ├── lexical_complexity.py # Avg word length, Zipf frequency, TTR, MTLD, % difficult words
│   ├── quality.py            # SARI (Xu et al. 2016), ROUGE-1/2/L, BERTScore
│   ├── meaning_preservation.py # SBERT cosine similarity
│   ├── clinical_jargon.py    # Parenthetical explanations rate, jargon density reduction, compression
│   └── evaluator.py          # Unified evaluator running all 28 metrics
├── runner.py                 # Main CLI runner (checkpointing, resumability, live execution)
├── evaluate_only.py          # Decoupled evaluator (runs metrics on results without API calls)
├── export_summary.py         # Summary report & markdown leaderboard generator
└── results/
    ├── .checkpoints/         # Atomic trial completion checkpoints (resumability)
    ├── generations.json      # Full generation records with prompts and metadata
    ├── generations.csv       # Tabular export for spreadsheet analysis
    ├── evaluations.json      # Scored entries with complete metric breakdowns
    ├── evaluations.csv       # Flat metric matrix (28 metrics per trial)
    └── summary_report.md     # Comparative leaderboards and task breakdowns
```

---

## 📋 Curated Samples Catalog

### 1. Discharge Summaries (`datasets/discharge_summaries/anotated_dataset_v2.xlsx`)
- **`DS-01` (Row 0, 201 words)**: Gastrointestinal & Renal — Crohn's disease, abdominal sepsis, acute on chronic kidney disease, surgical ileocolectomy; outcome: *alive*.
- **`DS-02` (Row 1, 749 words)**: Cardiovascular & Infectious — Catheter bloodstream infection, bacterial endocarditis on mitral valve, pyogenic spondylodiscitis; outcome: *alive*.
- **`DS-03` (Row 2, 578 words)**: Pulmonology & Thoracic Surgery — Sensitive pulmonary tuberculosis, spontaneous pneumothorax, pleurostomy & chest drainage; outcome: *alive*.
- **`DS-04` (Row 3, 268 words)**: Critical Multi-morbidity — Severe diabetic retinopathy/nephropathy, Fournier's gangrene, osteomyelitis, heart failure; **outcome: deceased / óbito** (validates Rule 7 3rd-person past-tense handling).
- **`DS-05` (Row 14, 1370 words)**: Hepatology & Critical Care — Liver cirrhosis, septic shock, acute respiratory failure, ICU stay, complex 1-month admission; outcome: *alive*.

### 2. Pathology Reports (`datasets/pathology_reports/TCGA-242/PRAD_reports_eng.xlsx`)
- **`PATH-01` (ID1_1, 493 words)**: Gross Resection Specimen — 50g prostatectomy specimen, dimensions, seminal vesicles, ductus deferens, surgical margins.
- **`PATH-02` (ID1_2, 159 words)**: Supplementary IHC Staining — AMACR, MA903, p63, perineural sheath invasion, Gleason 4+3=7b (ISUP Grade Group 3).
- **`PATH-03` (ID10_1, 435 words)**: High-Risk Neoplasm — Extensive multi-quadrant surgical margin mapping (bladder base, apical margins).
- **`PATH-04` (ID103_1, 382 words)**: Intraoperative Frozen Section — Margin dignity query, neurovascular bundle evaluation, Gleason 4+4=8 (ISUP Grade Group 4), R0 resection.
- **`PATH-05` (ID114_2, 255 words)**: Positive Surgical Margin (R1) — 19 mm basal margin infiltration, cytokeratin AE1/3, focal AMACR overexpression.

### 3. Radiology Reports (`datasets/radiology_reports/MR-RATE/batch00_reports.csv`)
- **`RAD-01` (LEDW5KEMKI, 113 words)**: Normal Cranial MRI — Within normal limits; critical test for avoiding false-positive hallucinations.
- **`RAD-02` (K67NPC32IW, 329 words)**: Cranial & Skull Base Lesion — Non-enhancing solid bone lesion at left jugular foramen and facial canal, Bell's palsy, recommending CT correlation.
- **`RAD-03` (436G6LTU2V, 258 words)**: Acute Critical Infection — Cerebral abscesses in left parietal lobe with intraventricular rupture and ventriculitis.
- **`RAD-04` (CU6OXMT22Y, 133 words)**: Cerebrovascular / Degenerative — Chronic ischemic-gliotic white matter lesions, pontine T2 hyperintensity.
- **`RAD-05` (7EKH3TEF3P, 294 words)**: Neurovascular Malformation — Multiple intracranial cavernomas (amygdala, frontal, cingulate), prior surgical resection cavity.

---

## ⚙️ Setup & API Keys

All API keys are **optional**. The script will attempt calls only for configured providers and skip others gracefully without crashing.

You can specify your keys directly in [`analysis/.env`](file:///home/raghavgrover/Desktop/Sem7/btp-Project/analysis/.env):
```bash
# analysis/.env
GEMINI_API_KEY=your_gemini_api_key_here
CEREBRAS_API_KEY=your_cerebras_api_key_here
GROQ_API_KEY=your_groq_api_key_here # Optional fallback for gpt-oss / qwen
```

---

## 🚀 Execution Guide

### 1. Smoke Test (Recommended First Step)
Runs 1 sample (`DS-01`) across models to verify network connectivity and keys:
```bash
python3 -m analysis.runner --smoke-test
```

### 2. Dry Run (0 API Calls, $0 Cost)
Validates all 240 trial combinations and prompt assemblies without calling any API:
```bash
python3 -m analysis.runner --dry-run
```

### 3. Full Benchmark Execution
Runs all 240 trials. Resumes automatically from checkpoints if interrupted:
```bash
python3 -m analysis.runner
```

### 4. Running Specific Subsets
Filter by task, datatype, model, or strategy:
```bash
# Only run simplification on discharge summaries:
python3 -m analysis.runner --task simplification --datatype discharge

# Only test Gemini models:
python3 -m analysis.runner --model gemini/3.8flash
```

### 5. Decoupled Evaluation (Zero API Cost)
Score all saved generations in `results/generations.json` with 28 metrics:
```bash
python3 -m analysis.evaluate_only
```

### 6. Generate Comparative Markdown Report
Create leaderboard tables and breakdown matrices in `results/summary_report.md`:
```bash
python3 -m analysis.export_summary
```

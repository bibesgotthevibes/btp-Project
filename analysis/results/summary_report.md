# Comparative Analysis & Benchmark Summary Report

**Total Records**: 114 | **Successfully Scored**: 96

## 1. Model Comparison Leaderboard

| Model | Task | Strategy | n | FKGL (↓) | FRE (↑) | SARI (↑) | ROUGE-1 | BERTScore | SBERT Cos | Jargon Red % | Latency (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **cerebras/gptoss** | simplification | few-shot | 5 | 12.96 | 44.69 | 14.05 | 61.1% | 75.42% | 79.03% | 0.09% | 4.29s |
| **cerebras/gptoss** | simplification | ner-guided | 15 | 12.04 | 50.75 | 10.33 | 40.37% | 83.23% | 65.98% | 20.0% | 5.54s |
| **cerebras/gptoss** | simplification | zero-shot | 5 | 10.56 | 57.2 | 14.37 | 55.87% | 63.21% | 66.88% | -18.29% | 4.36s |
| **cerebras/gptoss** | summarization | zero-shot | 1 | 10.28 | 35.44 | 10.44 | 49.71% | 46.52% | 51.94% | -171.43% | 2.05s |
| **cerebras/qwen3.8** | simplification | few-shot | 5 | 11.57 | 43.59 | 12.63 | 53.62% | 70.14% | 77.13% | 33.13% | 1.7s |
| **cerebras/qwen3.8** | simplification | ner-guided | 15 | 11.0 | 54.15 | 12.18 | 42.23% | 83.78% | 64.18% | 15.51% | 4.23s |
| **cerebras/qwen3.8** | simplification | zero-shot | 15 | 9.71 | 58.8 | 10.41 | 43.01% | 79.23% | 71.44% | 40.08% | 1.99s |
| **cerebras/qwen3.8** | summarization | zero-shot | 1 | 14.08 | 10.75 | 12.99 | 58.67% | 65.82% | 57.35% | -100.0% | 1.72s |
| **gemini/3.1pro** | simplification | few-shot | 4 | 11.14 | 59.08 | 2.26 | 19.64% | 47.97% | 43.84% | 83.23% | 34.58s |
| **gemini/3.1pro (ran on gemini-2.5-flash)** | simplification | few-shot | 1 | 12.6 | 46.42 | 5.79 | 34.91% | 45.92% | 49.63% | 42.86% | 22.32s |
| **gemini/3.1pro (ran on gemini-2.5-flash)** | simplification | ner-guided | 6 | 11.35 | 55.64 | 9.59 | 35.08% | 82.79% | 62.01% | 29.03% | 37.08s |
| **gemini/3.1pro (ran on gemini-2.5-flash)** | simplification | zero-shot | 5 | 10.97 | 53.22 | 14.46 | 57.2% | 61.49% | 69.76% | 11.78% | 12.3s |
| **gemini/3.1pro (ran on gemini-2.5-flash)** | summarization | zero-shot | 1 | 15.41 | 8.02 | 12.94 | 55.94% | 62.45% | 72.87% | -100.0% | 9.01s |
| **gemini/3.8flash** | simplification | few-shot | 4 | 11.4 | 51.05 | 13.47 | 56.16% | 71.69% | 78.49% | 17.64% | 8.03s |
| **gemini/3.8flash** | simplification | ner-guided | 1 | 13.37 | 51.33 | 2.09 | 16.54% | 82.25% | 46.98% | 97.14% | 35.2s |
| **gemini/3.8flash** | simplification | zero-shot | 4 | 10.87 | 52.42 | 13.07 | 57.02% | 61.42% | 71.6% | 26.44% | 9.82s |
| **gemini/3.8flash (ran on gemini-3.5-flash)** | simplification | few-shot | 1 | 13.38 | 39.4 | 17.05 | 61.4% | 62.96% | 67.27% | -42.86% | 18.51s |
| **gemini/3.8flash (ran on gemini-3.5-flash)** | simplification | ner-guided | 5 | 9.61 | 61.6 | 6.24 | 31.42% | 82.12% | 54.2% | 37.62% | 32.62s |
| **gemini/3.8flash (ran on gemini-3.5-flash)** | simplification | zero-shot | 1 | 12.51 | 42.12 | 15.91 | 51.61% | 53.5% | 60.61% | -42.86% | 13.57s |
| **gemini/3.8flash (ran on gemini-3.5-flash)** | summarization | zero-shot | 1 | 14.47 | 23.09 | 14.53 | 61.59% | 73.89% | 75.92% | -42.86% | 8.64s |

---

## 2. Task Comparison: Simplification vs. Summarization

| Task | Avg FKGL | Avg FRE | Complex Words % | Avg Word Len | SARI | Comp (Words) | Par Explanations/100w |
|---|---|---|---|---|---|---|---|
| **Simplification** | 11.12 | 53.48 | 61.02% | 4.85 | 11.04 | 1.43x | 4.02 |
| **Summarization** | 13.56 | 19.32 | 76.83% | 6.25 | 12.72 | 1.22x | 2.4 |

---

## 3. Datatype Performance Comparison

| Datatype | Task | Samples | FKGL (↓) | FRE (↑) | SARI (↑) | ROUGE-L | Jargon Red % |
|---|---|---|---|---|---|---|---|
| **Discharge** | simplification | 60 | 11.38 | 52.08 | 11.43 | 42.16% | 23.87% |
| **Discharge** | summarization | 4 | 13.56 | 19.32 | 12.72 | 56.48% | -103.57% |
| **Pathology** | simplification | 17 | 9.74 | 59.23 | 6.81 | 16.84% | 36.75% |
| **Radiology** | simplification | 15 | 11.65 | 52.57 | 14.31 | 25.28% | 9.07% |

---

## 4. Prompt Strategy Comparison

| Strategy | Task | SARI (↑) | Par Explanations/100w | ROUGE-1 | FKGL (↓) | FRE (↑) |
|---|---|---|---|---|---|---|
| **few-shot** | simplification | 10.96 | 5.63 | 48.66% | 11.94 | 48.39 |
| **ner-guided** | simplification | 10.2 | 3.31 | 38.65% | 11.31 | 53.97 |
| **zero-shot** | simplification | 12.28 | 3.92 | 49.67% | 10.31 | 56.2 |
| **zero-shot** | summarization | 12.72 | 2.4 | 56.48% | 13.56 | 19.32 |

---

## 5. NER-Guided: Entities Used vs. Zero-Shot Fallback

| NER stage | n | FKGL (↓) | FRE (↑) | SARI (↑) | ROUGE-L | BERTScore | SBERT Cos | Jargon Red % |
|---|---|---|---|---|---|---|---|---|
| parse_failed → zero-shot fallback | 11 | 9.87 | 62.4 | 6.81 | 18.0% | 82.2% | 57.97% | 53.58% |
| entities used | 31 | 11.82 | 50.98 | 11.4 | 22.27% | 83.57% | 64.67% | 12.99% |

---

## 6. Missing Trials (18)

| Trial | Error |
|---|---|
| simplification_pathology_PATH-02_gemini_31pro_ner-guided | HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For more inform |
| simplification_pathology_PATH-02_gemini_38flash_ner-guided | NER stage: HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For  |
| simplification_pathology_PATH-03_gemini_31pro_ner-guided | HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For more inform |
| simplification_pathology_PATH-03_gemini_38flash_ner-guided | HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For more inform |
| simplification_pathology_PATH-04_gemini_31pro_ner-guided | HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For more inform |
| simplification_pathology_PATH-04_gemini_38flash_ner-guided | HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For more inform |
| simplification_pathology_PATH-05_gemini_31pro_ner-guided | HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For more inform |
| simplification_pathology_PATH-05_gemini_38flash_ner-guided | HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For more inform |
| simplification_radiology_RAD-01_gemini_31pro_ner-guided | HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For more inform |
| simplification_radiology_RAD-01_gemini_38flash_ner-guided | HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For more inform |
| simplification_radiology_RAD-02_gemini_31pro_ner-guided | HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For more inform |
| simplification_radiology_RAD-02_gemini_38flash_ner-guided | HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For more inform |
| simplification_radiology_RAD-03_gemini_31pro_ner-guided | HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For more inform |
| simplification_radiology_RAD-03_gemini_38flash_ner-guided | HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For more inform |
| simplification_radiology_RAD-04_gemini_31pro_ner-guided | HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For more inform |
| simplification_radiology_RAD-04_gemini_38flash_ner-guided | HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For more inform |
| simplification_radiology_RAD-05_gemini_31pro_ner-guided | HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For more inform |
| simplification_radiology_RAD-05_gemini_38flash_ner-guided | HTTP 429: { "error": { "code": 429, "message": "You exceeded your current quota, please check your plan and billing details. For more inform |
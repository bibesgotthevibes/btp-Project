# GLiNER + Simplification Unified Pipeline (`analysis/gliner_ner/`)

All Task 3 workflows (clinical entity extraction, downstream simplification, and multi-metric analysis) are consolidated into a single master script: **[`pipeline.py`](pipeline.py)**.

---

## 1. Prerequisites & Setup

### Python Package:
```bash
pip install gliner pandas
```

### Ollama Local LLMs:
Pull the recommended models for local execution:
```bash
# 1. Top recommended medical model (SARI 66.0, ~2.5 GB)
ollama pull medgemma:4b

# 2. Top recommended 12B general model (~7.5 GB)
ollama pull gemma4:12b

# 3. Standard baselines (optional)
ollama pull llama3.1:8b
ollama pull qwen3:8b
```

Verify your models with:
```bash
ollama list
```

---

## 2. Running the Unified Pipeline

### A. End-to-End: GLiNER Extraction + LLM Simplification (Default)
Runs local GLiNER entity extraction, generates lay simplification using the selected LLM, and evaluates against ground-truth lay references:

```bash
# Run on 5 reports with local Ollama MedGemma (fast test bake-off)
python -m analysis.gliner_ner.pipeline --models ollama/medgemma:4b --n 5

# Run with Gemma 4 12B using GLiNER repair + few-shot strategy
python -m analysis.gliner_ner.pipeline --models ollama/gemma4:12b --strategies gliner-repair-fewshot --n 10

# Run with Cloud LLM (Cerebras / Groq / Gemini)
python -m analysis.gliner_ner.pipeline --models cerebras/qwen3.8 --n 10

# Run full evaluation across all 30 benchmark reports
python -m analysis.gliner_ner.pipeline --models ollama/medgemma:4b --n 30
```

### B. Extraction-Only Mode
Benchmark GLiNER extraction throughput and latency without running any LLMs:
```bash
python -m analysis.gliner_ner.pipeline --mode ner-only
```

### C. Interactive Single-Report Test
Test extraction and retention block formatting on custom clinical text:
```bash
python -m analysis.gliner_ner.pipeline --sample "Heart size is normal. No focal consolidation, pneumothorax, or large pleural effusion."
```

### D. Display Leaderboard
Display comparison table comparing `gliner-guided` and `gliner-repair-fewshot` against the Phase 2 baselines (`baseline_few-shot` and `baseline_ner-guided`):
```bash
python -m analysis.gliner_ner.pipeline --summary
```

---

## 3. Storage Format
All outputs are saved to **`analysis/results/gliner_ner/`**:
- **`results.json`**: Complete structured records per report (contains extracted spans, retention blocks, generated lay text, and evaluation metrics).
- **`results.csv`**: Tabular export ready for pandas / plotting.

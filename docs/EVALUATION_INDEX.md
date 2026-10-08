# BTP Team 4 · Evaluation index

**Lay language conversion of medical reports**: Sanyam Agrawal · Bibek Dhody · Arnav Deshmukh · Raghav Grover

Use this page during the evaluation to jump straight to any prompt, dataset, result or piece of code. All links are relative to the repository root.

| | |
|---|---|
| **Slides** | [BTP_Lay_Language_Conversion_Evaluation.pptx](BTP_Lay_Language_Conversion_Evaluation.pptx) (32 slides in the talk + 4 appendix slides after "Thank you"; speaker notes on each) |
| **All phase 2 outputs and scores** | [analysis/results/openi/results.csv](../analysis/results/openi/results.csv) (one row per output, all metrics) |
| **Main script** | [analysis/run_openi.py](../analysis/run_openi.py) |


### Presentation plan (two speakers)

| Part | Speaker | Slides | Content |
|---|---|---|---|
| 1 | Arnav | 1–8 | Task, datasets, PLABA, phase 1, discharge summaries |
| 2 | Sanyam | 9–22 | Radiology ground truth, methodology, prompt, metrics, E1, E2, normal vs abnormal, readability |
| 3 | Arnav | 23–28 | NER strategies, why NER underperforms, variants (E3), error analysis, example |
| 4 | Sanyam | 29–32 | Clinician review, conclusions, limitations, thank you |
| Q&A | either | 33–36 | Appendix |

Each slide's speaker notes start with the speaker's name; the three handover slides include a suggested transition line.

---

## 1. Prompts

### Phase 2: chest X-ray benchmark (Open-i)

| Prompt | Used by | Location |
|---|---|---|
| Chest X-ray simplification, system prompt | zero-shot, few-shot | [radiology_prompts.py:109](../analysis/prompts/radiology_prompts.py#L109) |
| Few-shot examples (3 train-split pairs: Open-i 3242, 3697, 3694) | few-shot | [radiology_prompts.py:120](../analysis/prompts/radiology_prompts.py#L120) |
| Entity extraction, radiology (team's NER stage 1) | original NER-guided | [ner_extraction_prompts.py:311](../analysis/prompts/ner_extraction_prompts.py#L311) |
| Entity list → "must retain" block | original NER-guided | [json_parser.py:88](../analysis/prompts/json_parser.py#L88) |
| Chest X-ray prompt + entity block | original NER-guided | [radiology_prompts.py:137](../analysis/prompts/radiology_prompts.py#L137) |
| Findings as plain-English sentences (stage 1 of variants A and B) | ner-fewshot, ner-repair | [radiology_prompts.py:146](../analysis/prompts/radiology_prompts.py#L146) (example: [line 155](../analysis/prompts/radiology_prompts.py#L155)) |
| Variant A: few-shot prompt + plain checklist | ner-fewshot | [radiology_prompts.py:168](../analysis/prompts/radiology_prompts.py#L168) |
| Variant B: check & repair | ner-repair | [radiology_prompts.py:175](../analysis/prompts/radiology_prompts.py#L175) |
| How each strategy is assembled (stage order, temperatures) | all | [run_openi.py:90](../analysis/run_openi.py#L90) (`generate`) |

### Phase 1: discharge, pathology, brain MRI (the app's prompts)

| Report type | Simplification | NER-guided | Entity extraction |
|---|---|---|---|
| Discharge | [discharge_prompts.py:14](../analysis/prompts/discharge_prompts.py#L14) | [discharge_prompts.py:100](../analysis/prompts/discharge_prompts.py#L100) | [ner_extraction_prompts.py:21](../analysis/prompts/ner_extraction_prompts.py#L21) |
| Pathology | [pathology_prompts.py:14](../analysis/prompts/pathology_prompts.py#L14) | [pathology_prompts.py:83](../analysis/prompts/pathology_prompts.py#L83) | [ner_extraction_prompts.py:178](../analysis/prompts/ner_extraction_prompts.py#L178) |
| Radiology (brain MRI) | [radiology_prompts.py:14](../analysis/prompts/radiology_prompts.py#L14) | [radiology_prompts.py:83](../analysis/prompts/radiology_prompts.py#L83) | [ner_extraction_prompts.py:311](../analysis/prompts/ner_extraction_prompts.py#L311) |

Few-shot examples sit directly below each simplification prompt. All prompts with explanations: [analysis/docs/ner_pipeline_prompts.md](../analysis/docs/ner_pipeline_prompts.md) (team document).

---

## 2. Datasets

Overview, sources and download links: [datasets/README.md](../datasets/README.md)

> `datasets/lay_reference_datasets/` (Open-i × LaymanRRG pairs, raw LaymanRRG, PLABA) is **not in the repository** (about 45 MB, and the LFS quota is exhausted). Download it with the links in datasets/README.md; the links below work on a local copy.

| Dataset | Role | Location |
|---|---|---|
| **Open-i × LaymanRRG pairs** (2,377 chest X-ray report → lay pairs) | Phase 2 test set (30 validation reports) and few-shot examples (train) | [openi_lay_pairs.csv](../datasets/lay_reference_datasets/radiology/openi_lay_pairs.csv) |
| LaymanRRG, BioLaySumm 2025 open track (raw) | Source of the lay references | [radiology/LaymanRRG_opensource/](../datasets/lay_reference_datasets/radiology/LaymanRRG_opensource/) |
| Open-i / NLMCXR reports | Original chest X-ray reports | [radiology_reports/NLMCXR_reports/](../datasets/radiology_reports/NLMCXR_reports/) |
| MR-RATE brain MRI | Phase 1 experiments | [radiology_reports/MR-RATE/](../datasets/radiology_reports/MR-RATE/) |
| Annotated discharge summaries | Phase 1 experiments | [discharge_summaries/anotated_dataset_v2.xlsx](../datasets/discharge_summaries/anotated_dataset_v2.xlsx) |
| TCGA-PRAD pathology | Phase 1 experiments | [pathology_reports/TCGA-242/](../datasets/pathology_reports/TCGA-242/) |
| Phase 1 curated reports | Phase 1 inputs | [analysis/samples/curated_samples.py](../analysis/samples/curated_samples.py) |
| PLABA + TREC 2024 PLABA (750 abstracts, 921 expert adaptations; term-level labels) | Examined; not used as benchmark (research abstracts, not clinical reports). Useful for metric checks and a jargon dictionary | [lay_reference_datasets/plaba/](../datasets/lay_reference_datasets/plaba/) |

**Ground truth:** lay references exist for radiology only (LaymanRRG). For discharge, MIMIC-IV-Note-Ext-DI needs PhysioNet credentialed access. For pathology, no English parallel corpus exists.

Several CSVs in `datasets/` are Git LFS pointers: the repository's LFS quota is exhausted, so the files on disk may be stubs. The README links to the original sources.

---

## 3. Results

### Phase 2: chest X-ray benchmark, scored against ground truth

| File | Contents |
|---|---|
| [results.csv](../analysis/results/openi/results.csv) / [results.json](../analysis/results/openi/results.json) | Every output (844) with source, reference, output text and all metrics; NER entity lists in the JSON |
| [error_analysis_gemma.csv](../analysis/results/openi/error_analysis_gemma.csv) | Manual read-through: Gemma 4 12B, 10 reports × 3 strategies, issue labels and notes |
| [doctor_review.html](../analysis/results/openi/doctor_review.html) | Blinded clinician review form (15 reports, 80 versions); answers pending |
| [doctor_review_key.csv](../analysis/results/openi/doctor_review_key.csv) | Key for the form (which version is which model or strategy). Do not share with the reviewer |

Print the summary table with `.venv/bin/python -m analysis.run_openi --summary`.

### Phase 1: three report types, no ground truth

| File | Contents |
|---|---|
| [phase1_rescored_standard_metrics.csv](../analysis/results/phase1_rescored_standard_metrics.csv) | Phase 1 outputs rescored with the same standard metrics as phase 2 (FKGL, AlignScore, length) |
| [evaluations.json](../analysis/results/evaluations.json) / [generations.json](../analysis/results/generations.json) | Team's phase 1 outputs and original scores |
| [summary_report.md](../analysis/results/summary_report.md) | Team's phase 1 leaderboard |
| [content_retention.json](../analysis/results/content_retention.json) | Team's entity and number retention checks |
| [ner_simplification_report.html](../analysis/report/ner_simplification_report.html) | Arnav's NER study, incl. discharge and pathology read-through |
| [review_doc.pdf](../analysis/results/review_doc.pdf), [viewer/index.html](../analysis/viewer/index.html) | Team's clinician review pack and output viewer |

---

## 4. Key numbers (phase 2, 30 chest X-ray reports)

**Strategies** (averages over the 7 models with all 30 reports)

| Strategy | SARI | ROUGE-L | BERTScore | AlignScore | FKGL |
|---|---|---|---|---|---|
| Zero-shot | 60.8 | 60.5 | 93.8 | 53.6 | 3.1 |
| **Few-shot** | **64.4** | **64.2** | **94.6** | **57.9** | 3.7 |
| Original NER-guided | 57.8 | 55.4 | 93.1 | 53.1 | 3.5 |
| Gold reference | 94.2 | 100 | 100 | 61.3 | 4.4 |

Few-shot beats zero-shot significantly (SARI, paired Wilcoxon p < 0.05) for 7 of 7 models, and NER-guided is significantly below few-shot for 7 of 7. The source reports average FKGL 12.1.

**Models** (few-shot): MedGemma 4B 66.0 · Gemma 4 12B 65.9 · Gemini 3.8 Flash 65.5 (n = 15) · Qwen 3.8 27B 65.5 · Qwen3 8B 64.8 · MedGemma 27B 63.9 · Llama 3.1 8B 62.8 · GPT-OSS 120B 61.9 (SARI). Small local models match the cloud models.

**NER variants** (SARI / AlignScore)

| Model | Few-shot | Original NER | A: checklist | B: check & repair |
|---|---|---|---|---|
| Gemma 4 12B | 65.9 / 58.7 | 57.4 / 53.5 | 63.7 / 60.4 | 65.7 / 59.6 |
| Qwen 3.8 27B | 65.5 / 58.2 | 56.2 / 50.5 | 61.3 / 52.9 | 65.0 / 58.7 |
| GPT-OSS 120B | 61.9 / 59.4 | 57.2 / 51.8 | 59.5 / 59.0 | 57.5 / 64.1 |

**Why NER underperforms:** NER outputs copy 11.1% of the report's technical terms unchanged (zero-shot 1.4%, few-shot 0.5%) because the entity list is in the report's wording and must all appear. In the read-through, NER invented severity or time labels in 5 of 10 reports and added advice in 4; few-shot had only lay-anatomy slips (3 of 10). No strategy flipped a negation.

---

## 5. Code

| What | Where |
|---|---|
| Phase 2 runner (strategies, NER variants, rescoring, summary) | [analysis/run_openi.py](../analysis/run_openi.py) |
| Phase 1 runner (team) | [analysis/runner.py](../analysis/runner.py), [run_ner_pipeline.py](../run_ner_pipeline.py) |
| Models and API settings | [analysis/config.py:64](../analysis/config.py#L64) |
| Providers (Gemini, Groq, Cerebras, Ollama) and key fallback | [analysis/providers/](../analysis/providers/), [router.py](../analysis/providers/router.py) |
| All metrics in one call | [metrics/evaluator.py:22](../analysis/metrics/evaluator.py#L22) |
| SARI (EASSE), ROUGE, BERTScore | [metrics/quality.py](../analysis/metrics/quality.py) |
| AlignScore | [metrics/factuality.py:37](../analysis/metrics/factuality.py#L37) |
| Readability (textstat) | [metrics/readability.py:23](../analysis/metrics/readability.py#L23) |
| Doctor review form: build and import answers | [analysis/review_form.py](../analysis/review_form.py) |
| Python dependencies | [analysis/requirements.txt](../analysis/requirements.txt) |

### Reproduce

```bash
uv venv --python 3.11 .venv && uv pip install --python .venv/bin/python -r analysis/requirements.txt
uv pip install --python .venv/bin/python --no-deps "alignscore @ git+https://github.com/yuh-zha/AlignScore"
curl -L -o .cache/alignscore/AlignScore-base.ckpt https://huggingface.co/yzha/AlignScore/resolve/main/AlignScore-base.ckpt
# API keys and local models go in .env (GEMINI_API_KEY, GROQ_API_KEY, LOCAL_MODELS=...)

.venv/bin/python -m analysis.run_openi                 # all models x all strategies, 30 reports (resumes)
.venv/bin/python -m analysis.run_openi --summary       # print results table
.venv/bin/python -m analysis.run_openi --rescore       # recompute metrics without regenerating
.venv/bin/python -m analysis.review_form build --model ollama/gemma4:12b --n 10 --compare-n 5
```

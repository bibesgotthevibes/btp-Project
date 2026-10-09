# Handover: what is done, and the plan for the next four tasks

BTP Team 4 · Lay language conversion of medical reports · October 2026

This page is for the teammates taking over the next phase. Part A explains what already exists (code, data, results, lessons), so you do not rebuild it. Part B is the implementation plan for the four new tasks. **All four tasks use the chest X-ray dataset we already have (Open-i × LaymanRRG)**; discharge and pathology reports are out of scope for this phase. For a link to every prompt, dataset and result file, see [EVALUATION_INDEX.md](EVALUATION_INDEX.md); this page does not repeat those tables.

**Contents**

- Part A: what is done
  - [A1. Status in one paragraph](#a1-status-in-one-paragraph)
  - [A2. Repository map](#a2-repository-map)
  - [A3. Setup](#a3-setup)
  - [A4. The phase 2 pipeline, step by step](#a4-the-phase-2-pipeline-step-by-step)
  - [A5. Data and ground truth](#a5-data-and-ground-truth)
  - [A6. Metrics](#a6-metrics)
  - [A7. Results and what they mean](#a7-results-and-what-they-mean)
  - [A8. Lessons and pitfalls](#a8-lessons-and-pitfalls)
- Part B: implementation plan
  - [B0. Shared groundwork (do first)](#b0-shared-groundwork-do-first)
  - [B1. Task 1: simplified summary and patient summary](#b1-task-1-simplified-summary-and-patient-summary)
  - [B2. Task 2: dataset creation with a bigger LLM and doctor verification](#b2-task-2-dataset-creation-with-a-bigger-llm-and-doctor-verification)
  - [B3. Task 3: NER with GLiNER](#b3-task-3-ner-with-gliner)
  - [B4. Task 4: summaries in Hindi, Urdu and Telugu](#b4-task-4-summaries-in-hindi-urdu-and-telugu)
  - [B5. Order of work and dependencies](#b5-order-of-work-and-dependencies)
  - [B6. Sources](#b6-sources)

---

# Part A: what is done

## A1. Status in one paragraph

We convert clinical reports into plain language for patients. **Phase 1** ran the app's prompts on discharge summaries, pathology reports and brain MRI reports without any ground truth (reference-free metrics only). **Phase 2** moved to chest X-rays, where a ground-truth dataset exists (Open-i reports paired with LaymanRRG lay versions, the BioLaySumm 2025 data). We ran 8 models (3 cloud, 5 local via Ollama) × 3 strategies (zero-shot, few-shot, NER-guided) plus 2 improved NER variants on 30 test reports, 844 outputs in total, scored with the BioLaySumm 2025 metric set plus AlignScore. **Main findings:** few-shot prompting is best for every model; small local models (MedGemma 4B, Gemma 4 12B) match cloud models; NER-guided prompting is worse because the forced entity list makes the model copy jargon. A blinded doctor review form (15 reports, 80 versions) is built, and ratings are pending. The evaluation deck is [BTP_Lay_Language_Conversion_Evaluation.pptx](BTP_Lay_Language_Conversion_Evaluation.pptx).

## A2. Repository map

Only the parts you need for the next tasks. Bold = written or rewritten for phase 2.

| Path | What it is |
|---|---|
| **[analysis/run_openi.py](../analysis/run_openi.py)** | Phase 2 runner: loads pairs, generates per model × strategy, scores, saves, resumes. Start here. |
| [analysis/config.py](../analysis/config.py) | Model registry and API keys (read from `.env`) |
| [analysis/providers/](../analysis/providers/) | One class per API (Gemini, Groq, Cerebras, **Ollama**); [router.py](../analysis/providers/router.py) picks the provider and falls back to a second key. `ModelRouter(allow_substitute=False)` never silently swaps models. |
| [analysis/prompts/](../analysis/prompts/) | All prompts. **Chest X-ray prompts and few-shot examples** are in [radiology_prompts.py](../analysis/prompts/radiology_prompts.py) (line 109 onwards); team NER extraction prompts in [ner_extraction_prompts.py](../analysis/prompts/ner_extraction_prompts.py) |
| **[analysis/metrics/](../analysis/metrics/)** | [evaluator.py](../analysis/metrics/evaluator.py) computes every metric in one call: `evaluate_generation(source, output, reference_text=...)` |
| **[analysis/review_form.py](../analysis/review_form.py)** | Builds a single offline HTML review form for the doctor (blinded, shuffled), and imports the CSV of answers |
| [analysis/results/openi/](../analysis/results/openi/) | Phase 2 outputs and scores (`results.json` / `.csv`), error analysis, review form and key |
| [analysis/runner.py](../analysis/runner.py), [run_ner_pipeline.py](../run_ner_pipeline.py) | Phase 1 runner (team) |
| [structured_extraction/](../structured_extraction/) | Team's LLM extraction of structured info (diagnoses, meds, red flags, follow-up) from discharge summaries (not used this phase) |
| [backend/](../backend/), [frontend/](../frontend/), [btp_lite/](../btp_lite/) | The MedSimplify web app and Flutter app (see [README.md](../README.md)) |
| [datasets/](../datasets/) | Raw datasets; [datasets/README.md](../datasets/README.md) has sources and download links |

## A3. Setup

```bash
# Python 3.11 venv with uv (pins matter, see A8)
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r analysis/requirements.txt
uv pip install --python .venv/bin/python --no-deps "alignscore @ git+https://github.com/yuh-zha/AlignScore"
mkdir -p .cache/alignscore && curl -L -o .cache/alignscore/AlignScore-base.ckpt \
  https://huggingface.co/yzha/AlignScore/resolve/main/AlignScore-base.ckpt
```

- **Keys** go in `.env` at the repo root (never commit it): `GEMINI_API_KEY`, `GROQ_API_KEY`, `CEREBRAS_API_KEY`, optional `GEMINI_API_KEY_FALLBACK` and `GROQ_API_KEY_FALLBACK`, and `LOCAL_MODELS=gemma4:12b,medgemma:4b,...` for Ollama.
- **Local models**: install [Ollama](https://ollama.com), then `ollama pull gemma4:12b` (and the others listed in `LOCAL_MODELS`).
- **Clinical metrics**: the RadGraph model downloads itself on first use. The CheXbert checkpoint must be downloaded by hand to `~/Library/Caches/chexbert/chexbert.pth` (from Hugging Face `StanfordAIMI/RRG_scorers`), because the package's own download link is broken.
- **Data**: `datasets/lay_reference_datasets/` is not in git (LFS quota exhausted). Download it with the links in [datasets/README.md](../datasets/README.md).

## A4. The phase 2 pipeline, step by step

```
openi_lay_pairs.csv ──► sample 30 validation reports (seed 42)
                         │
                         ▼
        for each model × strategy:  generate(router, model, strategy, source)
          zero-shot   : system prompt → rewrite
          few-shot    : system prompt + 3 train examples → rewrite
          ner-guided  : LLM extracts entities (JSON) → "must retain" list → rewrite   (team)
          ner-fewshot : LLM lists findings in plain English → checklist + few-shot rewrite (variant A)
          ner-repair  : few-shot draft → findings checklist → LLM fixes only missing/wrong items (variant B)
                         │
                         ▼
        evaluate_generation(source, output, reference) → all metrics
                         │
                         ▼
        results.json / results.csv  (resumable; failed items retried on next run)
                         │
                         ▼
        --summary table · review_form.py build → doctor_review.html
```

```bash
.venv/bin/python -m analysis.run_openi                  # run everything not yet done (resumes)
.venv/bin/python -m analysis.run_openi --summary        # results table
.venv/bin/python -m analysis.run_openi --rescore        # recompute metrics only
.venv/bin/python -m analysis.review_form build --model ollama/gemma4:12b --n 10 --compare-n 5
.venv/bin/python -m analysis.review_form import answers.csv
```

**To add a new task, copy this pattern** (B0 says how): a pairs file, a `generate()` per strategy, `evaluate_generation()`, a resumable results file, and a review form.

## A5. Data and ground truth

| Data | What it gives | Status |
|---|---|---|
| **Open-i × LaymanRRG** ([openi_lay_pairs.csv](../datasets/lay_reference_datasets/radiology/openi_lay_pairs.csv)) | 2,377 chest X-ray reports (train 2,243 / validation 134), columns `findings`, `impression`, `radiology_report`, `layman_report` | Our ground truth. Lay text is GPT-4o generated, self-refined, 98% of 500 checked sentence pairs judged correct by people |
| LaymanRRG open track (sentence level, 150k pairs; PadChest, BIMCV, Open-i) | Sentence pairs for training | Downloaded, unused so far |
| LaymanRRG report level (50k MIMIC-CXR lay captions) | Lay text only; MIMIC source reports need PhysioNet | Downloaded, unused |
| Discharge summaries ([anotated_dataset_v2.xlsx](../datasets/discharge_summaries/anotated_dataset_v2.xlsx)) | 200 translated Brazilian discharge summaries + abbreviation and ICD sheets | No lay reference |
| TCGA pathology, MR-RATE brain MRI | Phase 1 inputs | No lay reference |
| PLABA (+ TREC 2024) | Expert lay adaptations of PubMed abstracts, term-level replacement labels | Wrong genre for a benchmark; useful as a jargon dictionary |

**Known data issues:** Open-i 2072 has its whole report duplicated; 5 of our 30 test reports also appear in the train split; Open-i text has `XXXX` anonymisation gaps. Clean these before building new datasets (B0).

## A6. Metrics

All standard libraries. Reference-based metrics compare with the gold lay text; AlignScore compares with the original report.

| Group | Metric | Library | Notes |
|---|---|---|---|
| Relevance | SARI | EASSE | Simplification edits. Gold reference scores 94.2, not 100 (phrase-level KEEP) |
| | ROUGE-1/2/L, BERTScore, SIM | rouge-score, bert-score (RoBERTa-large), sentence-transformers (MiniLM) | BioLaySumm set |
| Readability | FKGL, FRE, DCRS, CLI | textstat | English only. DCRS is inflated by words like "normal" and "fluid" |
| Factuality | AlignScore | AlignScore-base | Each output sentence must be supported by the report. Penalises correct explanations and hedged paraphrases |
| Clinical | F1-CheXbert, RadGraph F1 | f1chexbert, radgraph | CheXbert: 14 findings, concept level. RadGraph: entity words, so lay wording scores low against clinical text |

## A7. Results and what they mean

Few-shot averages over 7 models (30 reports): SARI 64.4, ROUGE-L 64.2, BERTScore 94.6, AlignScore 57.9, FKGL 3.7 (source 12.1), FRE 86.9 (source 19.1). Full tables: [EVALUATION_INDEX.md §4](EVALUATION_INDEX.md#4-key-numbers-phase-2-30-chest-x-ray-reports).

Findings that should shape the next phase:

1. **Few-shot examples matter more than model size.** A 4B local model matches a 120B cloud model. Use few-shot for every new task.
2. **Do not force an entity list into the prompt.** The model then copies the report's terms (11.1% of technical terms copied, against 0.5% for few-shot). NER works better as a **checker** after drafting (variant B). This matters for Task 3.
3. **Errors are mostly additions, not omissions.** NER invented severity or time labels in 5 of 10 read-through reports and added advice in 4; no strategy flipped a negation. Verification forms should ask about invented content explicitly.
4. **Metrics are least reliable on significant reports** (hedges, explanations, long reports): even the gold reference drops from 66 to 47 AlignScore. Doctor review is needed exactly there.
5. **Reference-based scores reward closeness to one GPT-4o reference, not correctness.** For new datasets, the doctor-verified text becomes the reference, which fixes this at the source.

## A8. Lessons and pitfalls

- **Library pins**: `setuptools<70` (AlignScore and EASSE need `pkg_resources`), `pytorch-lightning==1.9.5` (AlignScore). CheXbert and RadGraph call tokenizer methods removed in transformers 5; [clinical.py](../analysis/metrics/clinical.py) restores them (`_install_tokenizer_compat`). Do not upgrade these blindly.
- **Never let a metric fall back silently.** An early version replaced BERTScore with word overlap when the library was missing. Metrics now fail loudly; keep it that way.
- **Record the exact model ID with every output.** One config key named "3.1 Pro" actually ran 3.5 Flash. The router now refuses to substitute models.
- **Dry runs must never write results** (one overwrote the shared file).
- **Free-tier limits**: Gemini free tier stops after a few hundred calls a day (that is why Gemini has n = 15). Use Cerebras or Groq for bulk generation, and set the fallback keys.
- **Git LFS quota is exhausted**: do not add large files to git; keep data downloads out of the repo and document links instead.
- **Keep test examples out of prompts**: few-shot examples come from the train split only.

---

# Part B: implementation plan

Owners are suggestions; adjust as a team. Effort assumes one person working part-time.

| Task | Suggested owner | Depends on | Effort |
|---|---|---|---|
| B0 Shared groundwork | Everyone, together | none | 2–3 days |
| B1 Summaries (task 1) | Bibek | B0 | 1.5 weeks |
| B2 Dataset creation + doctor verification (task 2) | Raghav | B0, B1 prompts | 2–3 weeks (doctor time is the bottleneck) |
| B3 GLiNER NER (task 3) | Arnav (built the current NER) | B0 | 1.5 weeks, in parallel |
| B4 Hindi, Urdu, Telugu (task 4) | Sanyam + native-speaker reviewers | B2 verified English set | 2–3 weeks |

## B0. Shared groundwork (do first)

1. **Write the summary guideline with the doctor before generating anything** (one page; see B1 for a draft): what a "simplified summary" contains, what counts as "unnecessary for the patient", tone, length, how to state uncertainty. Every later step (prompts, verification, metrics) follows this page.
2. **Clean the source data** into `datasets/gt_build/sources.csv`: remove exact duplicate sentences inside a report (Open-i 2072), drop reports whose text also appears in the train split from the test pool, mark `XXXX` gaps, and keep `findings` and `impression` separately.
3. **Fix the splits**: test = the 134 Open-i validation reports (includes our 30); pool for few-shot examples and training = the 2,243 train reports.
4. **Use one record format for everything that is generated or verified** (JSONL, one line per item):

   ```json
   {"id": "2165.xml", "task": "patient_summary", "lang": "en", "source": "...", "draft": "...",
    "generator": "cerebras/gpt-oss-120b", "prompt_version": "ps-v2", "auto_checks": {"alignscore": 61.2},
    "status": "pending|accepted|edited|rejected", "final": "...", "reviewer": "Dr X",
    "error_types": ["invented", "omitted_key_finding"], "notes": "..."}
   ```

5. **Make a generic runner** `analysis/run_task.py` by copying [run_openi.py](../analysis/run_openi.py): parameterise the pairs file, task name and prompt set, and keep resume, `--summary` and `--rescore`. Add prompts in new files (`analysis/prompts/summary_prompts.py`, `multilingual_prompts.py`); do not edit the chest X-ray prompts used in the evaluation.

## B1. Task 1: simplified summary and patient summary

**Goal**: for each Open-i chest X-ray report, produce two texts.

| Output | Content | Length |
|---|---|---|
| **(a) Simplified medical summary** | All clinically relevant findings in plain language, condensed; technique and repetition removed | about 40–60% of a full lay rewrite |
| **(b) Patient summary, unnecessary information omitted** | Only what the patient needs: the main result, what it means, how certain it is, and any next step the report states. Omits technique, image quality remarks, normal anatomy lists, comparison references and stable incidental findings that need no action (exact rules from the doctor's guideline) | 2–5 sentences |

### Step 1: check for existing ground truth (done; summary below)

| Candidate | Fits | Access | Verdict |
|---|---|---|---|
| **Open-i `impression` column** (all 2,377 reports) | The radiologist's own summary of the findings: shows what matters, but in clinical language | Have it | Use as a **reference for content selection** (what to keep), not as lay ground truth |
| **LaymanRRG** `layman_report` | Full lay rewrite of the whole report, not a summary | Have it | Not a summary ground truth, but a useful input: summarising the lay rewrite is one strategy to compare |
| Chest X-ray lay *summaries* | none found | none | **Create our own (B2)** |
| MIMIC-based patient summaries (Hegselmann et al. 2024; Discharge Me!, BioNLP 2024; MeDiSumQA) | Doctor-written patient summaries, but of *discharge* notes | PhysioNet credentialed | Out of scope (different report type, no access); cite as related work |

**Conclusion**: no lay summary ground truth exists for chest X-rays, so we create it from Open-i (B2), using the `impression` to guide what to keep and the LaymanRRG rewrite as a second reference for wording.

### Step 2: prompts

- One prompt per output type, few-shot (3 examples). The examples come from the first batch the doctor verifies (B2 pilot); until then, write 3 by hand with the guideline.
- **Patient summary as two steps** (same idea as variant B, which worked): (1) the LLM lists the findings and labels each one *key / minor / omit* following the guideline, as JSON; (2) the LLM writes the summary from the *key* items only, few-shot. Saving step 1 gives an inspectable record of what was dropped and why, which also drives the omission metrics below.
- Use the Open-i `impression` as an extra hint in step 1 ("the radiologist's impression highlights…"), and ablate it (with and without) to see if it helps.
- Compare three inputs: the original report, the original report + impression, and the LaymanRRG lay rewrite (summarise an already simplified text). The third shows whether simplifying first and summarising second is easier for the model.

### Step 3: run

Models: the best local (Gemma 4 12B, MedGemma 4B) and cloud (Qwen 3.8 27B, GPT-OSS 120B) from phase 2. Strategies: zero-shot, few-shot, two-step. First on the same 30 test reports (comparable with phase 2), then on all 134.

### Step 4: metrics ("optimal metrics")

No single metric covers a patient summary, so report one per property. Bold = new code.

| Property | Metric | Compared with | Why |
|---|---|---|---|
| Content vs gold | ROUGE-1/2/L, BERTScore, SIM | Doctor-verified summary (B2) | BioLaySumm standard for summaries |
| **Key findings kept** | **Key-finding recall**: share of the source's abnormal CheXbert labels also positive in the summary (concept level, so lay wording is fine) | Source report | The one thing a patient summary must not lose |
| **Nothing invented** | AlignScore (+ SummaC as a second opinion) | Source report | Factual consistency |
| **Unnecessary content left in** | **Omission precision**: share of summary sentences that map to items labelled *omit* in step 1 or by the doctor | Guideline labels | Measures "unnecessary info omitted" directly |
| Readability | FKGL, FRE, DCRS | none | Target grade 6–8 |
| Length | Compression ratio (summary words ÷ report words) | Source | Summary vs rewrite |
| Clinical agreement | F1-CheXbert vs gold | Gold summary | Same as phase 2 |
| Human | Doctor ratings: correct / complete / understandable / appropriate for patient (1–5) | none | Final judgement |

SARI is designed for sentence simplification, not summarisation; report it for (a) only, as a secondary metric.

**Deliverables**: `analysis/prompts/summary_prompts.py`, results in `analysis/results/summaries/`, one table per output type, and 2–3 worked examples (a normal and a significant report, as in the deck).

## B2. Task 2: dataset creation with a bigger LLM and doctor verification

**Goal**: a doctor-verified ground-truth set of Open-i chest X-ray summaries for the two summary types (and later the three languages, B4), built the way LaymanRRG was built (generate → self-check → human check), but with a doctor instead of crowd checks.

### Pipeline

```
sources.csv ─► big LLM drafts (prompt from B1, few-shot)
            ─► automatic checks:  AlignScore vs source, key-finding recall (CheXbert),
                                  length, readability; second LLM as checker ("list any
                                  statement not supported by the report / key finding missing")
            ─► flag:  any check fails → regenerate once, else mark "needs attention"
            ─► doctor verification form:  accept / edit / reject + error type
            ─► gold JSONL (status, final text, reviewer, error types)
```

### Choices

- **Inputs**: Open-i `radiology_report` (findings + impression) from [openi_lay_pairs.csv](../datasets/lay_reference_datasets/radiology/openi_lay_pairs.csv), after the cleaning in B0.
- **Generator ("bigger LLM")**: the strongest model available on our keys. Options: GPT-OSS 120B or Qwen 3.8 27B (Cerebras/Groq, generous limits), or Gemini Pro on a paid key. Run a 20-report bake-off of two candidates through the automatic checks and pick one. **Use a different model as the checker than as the generator**, so it does not approve its own mistakes. Record the exact model ID and prompt version per item.
- **Sizes**:

  | Set | Reports | Doctor check | Purpose |
  |---|---|---|---|
  | Pilot | 20 (from train) | All, plus a short call with the doctor | Fix guideline and prompts; becomes the few-shot pool |
  | Test (gold) | 100 of the 134 validation reports, including our 30 | All | Benchmark for B1 and B4 |
  | Train (silver) | 2,243 train reports | 10% random sample; all automatically flagged ones | Few-shot pool and future fine-tuning (our "fine-tuning for correctness" future work) |

- **Doctor time**: about 1.5 minutes per item to read and edit, so 100 reports × 2 summary types ≈ 5 hours. Split into 25-item sessions. If two doctors are available, give 20% of items to both and report agreement (Cohen's kappa on accept/edit/reject).
- **Verification form**: extend [review_form.py](../analysis/review_form.py) with a `verify` mode. Show the source report and the draft with three buttons (accept / edit / reject), a text box pre-filled with the draft for edits, error-type checkboxes (*invented*, *omitted key finding*, *wrong certainty*, *jargon*, *unnecessary detail kept*, *other*), and a notes field. Keep the existing behaviour: one offline HTML file, answers saved in the browser, and "Download my answers" producing a CSV. Add `import-verify` to merge answers into the gold JSONL.
- **What becomes ground truth**: accepted drafts, plus the doctor's edited text for edited drafts. Rejected items are regenerated and sent again, or dropped and counted. Report the accept / edit / reject rates; they measure the generator's quality on their own.
- **Store** under `datasets/gt_build/` (`drafts.jsonl`, `gold_test.jsonl`, `silver_train.jsonl`, `guideline.md`), and outside git if large (LFS quota; see A8). Add a data card: sources, generator, prompt version, verification protocol, counts, licence (Open-i: free use with citation; LaymanRRG: check its licence before redistributing).

## B3. Task 3: NER with GLiNER

**Goal**: on the Open-i chest X-ray reports, replace the LLM-based entity extraction (stage 1 of the team's NER pipeline, [ner_extraction_prompts.py](../analysis/prompts/ner_extraction_prompts.py)) with GLiNER: a small local model that tags entity types you name at inference time, returns exact character spans, is deterministic, and runs on a laptop CPU.

### Models to compare

| Model (Hugging Face) | Why |
|---|---|
| `Ihor/gliner-biomed-large-v1.0` (and `-base`, `-small`) | GLiNER-BioMed (Yazdani et al., 2025), trained for biomedical entities; Apache-2.0 |
| `urchade/gliner_multi-v2.1` | General multilingual GLiNER; a baseline, and a candidate for Hindi, Urdu and Telugu (B4) |
| Current LLM extraction (team's prompt) | Baseline to beat |

`pip install gliner`, then `GLiNER.from_pretrained(name).predict_entities(text, labels, threshold=0.4)`.

### Label set (start here, tune on a dev set of train reports)

anatomical structure, abnormal finding, normal finding, absent finding, uncertain finding, medical device, measurement, change over time. These line up with RadGraph's anatomy and observation (present / uncertain / absent) types, which makes the silver labels below easy to map.

GLiNER does not model negation reliably. Either test whether the label "absent finding" works, or tag findings and decide negation separately with a rule-based negation detector (medspaCy ConText or NegEx). Measure both.

### Evaluation ground truth

- **Chest X-ray, silver**: run the RadGraph model (already installed for our RadGraph F1 metric) on Open-i reports. It gives anatomy and observation entities with present / uncertain / absent labels. Map those to the GLiNER labels and use them as silver labels for a quick, large comparison.
- **Chest X-ray, gold**: hand-annotate 30 reports (two teammates, with the doctor deciding disagreements), using [Label Studio](https://labelstud.io) or doccano. Report agreement.
- **Metrics**: entity-level precision, recall and F1, strict (exact span) and partial (overlap), per label; plus speed (reports per second) and cost against the LLM extractor.

### Use downstream (the important part)

Phase 2 showed that forcing an entity list into the rewrite prompt **hurts**. Use GLiNER entities as a **checker**, not a constraint:

1. **Variant B with GLiNER**: few-shot draft → GLiNER entities of the source → LLM checks the draft against them and fixes only missing or wrong items. Compare with the LLM-checklist variant B from phase 2 (SARI, AlignScore, key-finding recall).
2. **Patient summary step 1 (B1)**: GLiNER entities plus the guideline give the *key / minor / omit* item list.
3. **Automatic check in B2**: flag drafts where an abnormal source entity has no counterpart in the draft. Match by concept, not by word: lay text never repeats the clinical word, which is why the team's word-matching "entities kept" score gave the gold references only 18%.

**Optional**: fine-tune GLiNER on the silver RadGraph labels (GLiNER ships a training script) and check whether gold-set F1 improves.

**Deliverables**: `analysis/ner/gliner_extract.py` (same output shape as the current extractor, so it plugs into [json_parser.py](../analysis/prompts/json_parser.py)), an evaluation table (models × label × P/R/F1), and the downstream comparison.

## B4. Task 4: summaries in Hindi, Urdu and Telugu

**Goal**: the simplified summary (B1 a) and patient summary (B1 b) in Hindi, Urdu and Telugu, with a doctor-verified test set.

### Step 1: check for existing ground truth (done; nothing usable as-is)

| Candidate | What it is | Verdict |
|---|---|---|
| *Bridging Health Literacy Gaps in Indian Languages* (SciProdLLM workshop 2025) | mT5 + IndicTrans2 simplification of clinical text in English, Hindi, Tamil and Telugu; synthetic set of 2,000 discharge summaries | Closest work. No Urdu; release of the data not confirmed. Read it as related work and email the author for the data |
| MultiCochrane (EMNLP 2023) | Medical simplification in English, Spanish, French, Farsi | No Indian languages |
| CoRil-Parallel (AIKosh) | 772k sentence pairs in 11 Indian languages including Hindi, Telugu and Urdu, with a Health domain | Translation, not simplification. Useful for terminology and for checking translation quality |
| LTRC Hindi–Telugu corpus | 535k sentences including a healthcare domain | Translation only, no Urdu |
| OpenWHO | Document-level health translation corpus for low-resource languages | Translation only; check which of our languages it covers |

**Conclusion**: create our own, starting from the doctor-verified English set of B2.

### Pipeline

```
gold English summaries (B2) ─► route 1: translate with IndicTrans2 (ai4bharat/indictrans2-en-indic-1B, covers hi, te, ur)
                            ─► route 2: big LLM writes the summary directly in the target language from the English report
                            ─► automatic checks: back-translate to English (IndicTrans2 indic-en) → AlignScore and
                                                 key-finding recall against the source; LaBSE similarity to the English gold
                            ─► native-speaker review (fluency, register) + doctor review (medical correctness)
                            ─► gold JSONL with lang = hi | ur | te
```

- **Compare both routes** on the 30 test reports before scaling: translation keeps the verified content exactly, while direct generation may read more naturally. The reviewers' accept rates decide which route builds the full set.
- **Style guide per language** (agree with the reviewers first):
  - Everyday Hindustani rather than Sanskritised Hindi.
  - Keep loanwords patients actually use (X-ray, BP, report, scan) in the target script.
  - Write numbers and units the way patients see them on prescriptions.
  - Urdu in Nastaliq script, right-to-left.
- **Reviewers**: one native speaker per language who can judge fluency, plus a doctor who reads that language (or a doctor checking the back-translation if none is available; state this limitation). Test set: the same 100 reports × 3 languages; start with 30 per language if reviewer time is short.
- **Review form**: the `verify` mode from B2 with `lang` support: Noto Sans Devanagari, Noto Sans Telugu and Noto Nastaliq Urdu fonts, and `dir="rtl"` for Urdu.

### Metrics (textstat readability formulas do not work for these languages)

| Property | Metric |
|---|---|
| Content vs gold | chrF++ (sacreBLEU), BERTScore with `xlm-roberta-large`, COMET (`Unbabel/wmt22-comet-da`, XLM-R based, covers all three languages) |
| Meaning vs English | LaBSE cosine similarity to the English gold summary |
| Nothing invented, nothing lost | Back-translation to English, then AlignScore vs the source and key-finding recall (B1) |
| Readability (proxy) | Average sentence length, average word length, share of words outside the most frequent 5k words of a large corpus (e.g. IndicCorp); use [indic-nlp-library](https://github.com/anoopkunchukuttan/indic_nlp_library) for tokenisation |
| Human | Native-speaker fluency (1–5), doctor correctness (1–5) |

Optional: run the GLiNER multilingual model (B3) on the outputs to check that key entities survive translation.

## B5. Order of work and dependencies

```
Week 1   B0: guideline with doctor · Open-i cleaning and splits · generic runner
         B3: GLiNER baseline on silver RadGraph labels (in parallel, no dependency)
Week 2   B1: prompts + runs on 30 reports · B2: generator bake-off, pilot 20 → doctor
Week 3   B2: test set (100) generation + verification sessions · B1: metrics on verified gold
         B3: gold annotation (30 reports) + downstream variant B with GLiNER
Week 4   B4: route comparison on 30 reports per language → reviewers
Week 5   B4: full multilingual test set · B2: silver train set · write-up
```

Risks:
- **Doctor availability** is the critical path. Book sessions in week 1 and keep each session to 25 items.
- **Reviewers for Urdu and Telugu** may be hard to find; ask early.
- **Free-tier limits**: use Cerebras or Groq for bulk generation; cache every call.

## B6. Sources

- Hegselmann et al. 2024, *A Data-Centric Approach to Generate Faithful and High Quality Patient Summaries with LLMs*: [paper](https://proceedings.mlr.press/v248/hegselmann24a.html), [data (PhysioNet ann-pt-summ)](https://physionet.org/content/ann-pt-summ/)
- Discharge Me! BioNLP 2024 shared task: [PhysioNet](https://alpha.physionet.org/content/discharge-me/), [example system paper](https://arxiv.org/pdf/2406.18094)
- MeDiSumQA 2025: [paper](https://arxiv.org/html/2502.03298v1), [data](https://physionet.org/content/medisumqa/)
- LaymanRRG (BioLaySumm 2025): [Hugging Face](https://huggingface.co/datasets/BioLaySumm/LaymanRRG-closesource-track)
- GLiNER-BioMed: [model card](https://huggingface.co/Ihor/gliner-biomed-large-v1.0), [paper](https://arxiv.org/abs/2504.00676v1), [code](https://github.com/ds4dh/GLiNER-biomed), [independent evaluation](https://arxiv.org/abs/2510.08588v1)
- *Bridging Health Literacy Gaps in Indian Languages* (SciProdLLM 2025): [ACL Anthology](https://aclanthology.org/2025.sciprodllm-1.1/)
- MultiCochrane, *Multilingual Simplification of Medical Texts* (EMNLP 2023): [arXiv](https://arxiv.org/abs/2305.12532v4)
- CoRil-Parallel: [AIKosh](https://aikosh.indiaai.gov.in/home/datasets/details/coril_parallel.html), [Hugging Face](https://huggingface.co/datasets/HimangY/CoRil-Parallel)
- LTRC Hindi–Telugu parallel corpus: [LREC 2022](https://preview.aclanthology.org/dois-2013-emnlp/2022.lrec-1.365)
- OpenWHO health translation corpus: [arXiv](https://arxiv.org/pdf/2508.16048)
- Simple-patho (German pathology simplification, unreleased): [GitHub](https://github.com/jantrienes/simple-patho)

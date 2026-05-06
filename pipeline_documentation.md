# Medical Discharge Summary → Indian Lay English Pipeline (v2 — Robust)

## Overview

This pipeline converts **complex medical discharge summaries** (originally in Portuguese, translated to English) into **simplified Indian Lay English** that a common Indian patient or family member can understand.

### v2 Key Improvements over v1

| Problem in v1 | v2 Solution |
|---|---|
| 100 % hallucinated model output (e.g., "this study…", gender flips) | **Quality-gated generation** — strict checks reject hallucinated chunks; rule-based fallback always available |
| Medical entities destroyed (sepsis 66→0, pneumonia 98→0) | **Entity-preserving lay dictionary** — outputs "high BP (hypertension)" so medical terms survive |
| Text truncated (600-word docs fed to 256-token model) | **Sentence-level chunked processing** — splits into ~200-word chunks matching training data |
| Domain mismatch (PubMed abstracts ≠ clinical records) | **Data analytics step** to quantify mismatch; sentence-level model application reduces gap |
| `datasets` library import error on Kaggle | Replaced with **PyTorch Dataset** class |
| `Seq2SeqTrainer` tokenizer deprecation warning | Uses `processing_class` for transformers ≥ 4.46 |

---

## Platform Requirements

| Requirement | Value |
|---|---|
| **Platform** | Kaggle Notebook |
| **Accelerator** | GPU T4 x2 (or P100) |
| **Internet** | ON (for downloading models) |
| **Python** | 3.10+ |

---

## Datasets Used

| # | Dataset | Rows | Role in Pipeline |
|---|---------|------|------------------|
| 1 | `anotated_dataset_v2.xlsx` (annotated_dataset sheet) | 200 | **Primary input** — discharge summaries with diagnosis, outcome, specialty |
| 2 | `anotated_dataset_v2.xlsx` (abbreviations sheet) | 301 | **Abbreviation dictionary** — maps medical abbreviations to full forms |
| 3 | `anotated_dataset_v2.xlsx` (ICD Codes sheet) | ~2,000 | **ICD code lookup** — maps disease codes to descriptions |
| 4 | `data/data.tsv` | 93,368 | **Fine-tuning data** — original medical text ↔ simplified English pairs |
| 5 | `predictions-t5-base.tsv` | 298 | **Benchmarking** — compare our output against T5-base predictions |
| 6 | `mtsamples.csv` | 4,999 | **Supplementary** — medical transcriptions across 40 specialties |
| 7 | `PMC-Patients-V2.json` | 250,294 | **Reference** — PubMed Central patient case reports |

### Key Dataset: `data.tsv`

This is the most important dataset for fine-tuning. It contains:

| Column | Description |
|--------|-------------|
| `original` | Original complex medical/biomedical text from PubMed |
| `english simplified` | Human-simplified version in plain English |
| `english super simplified` | Even simpler version |
| + 10 languages | Simplified versions in Spanish, French, Farsi, etc. |

We use the `original` → `english simplified` pairs (10,000 samples) to fine-tune IndicBART.

---

## Pipeline Flow (v2)

```
┌────────────────────────────────┐
│   STEP 0: Install Libraries    │  Install to /kaggle/working/local_libs/
│   (Local Folder on Kaggle)     │  Avoids system package conflicts
└────────────┬───────────────────┘
             │
┌────────────▼───────────────────┐
│   STEP 1: Import Libraries     │  numpy, pandas, spacy, transformers,
│                                │  torch, scispacy, tqdm, packaging
└────────────┬───────────────────┘
             │
┌────────────▼───────────────────┐
│   STEP 2: Load All Datasets    │  7 data sources auto-located
│                                │  under /kaggle/input/
└────────────┬───────────────────┘
             │
┌────────────▼───────────────────┐
│   STEP 3: Data Analytics (NEW) │  Length distributions, domain
│                                │  mismatch, entity frequency
└────────────┬───────────────────┘
             │
┌────────────▼───────────────────┐
│   STEP 4: Preprocess, Sentence │  Clean placeholders → expand
│   Split, NER & Chunking        │  abbreviations → sentence split
│                                │  → NER per sentence → ~200-word chunks
└────────────┬───────────────────┘
             │
┌────────────▼───────────────────┐
│   STEP 5: Entity-Preserving    │  "high BP (hypertension)" for
│   Lay Dict + Rule-Based Simpl. │  entities; straight replace for
│                                │  non-entities (always available)
└────────────┬───────────────────┘
             │
┌────────────▼───────────────────┐
│   STEP 6: Fine-Tune IndicBART  │  10K from data.tsv, PyTorch Dataset
│                                │  processing_class for TF >= 4.46
└────────────┬───────────────────┘
             │
┌────────────▼───────────────────┐
│   STEP 7: Chunk-Level          │  Generate per chunk; quality gate
│   Generation + Quality Gates   │  (entity recall≥40%, length ratio,
│                                │  hallucination markers) → model or
│                                │  rule-based fallback
└────────────┬───────────────────┘
             │
┌────────────▼───────────────────┐
│   STEP 8: Entity Verification  │  Re-inject missing critical entities
│   & Assembly                   │  as bracketed notes
└────────────┬───────────────────┘
             │
┌────────────▼───────────────────┐
│   STEP 9: Evaluation           │  Flesch, compression, rule vs final
└────────────┬───────────────────┘
             │
┌────────────▼───────────────────┐
│  STEP 10: Save Output          │  lay_english_pipeline_output.xlsx
└────────────┬───────────────────┘
             │
┌────────────▼───────────────────┐
│  STEP 11: Summary Report       │  Readability, entity audit,
│                                │  model vs rule-based stats
└────────────┬───────────────────┘
             │
┌────────────▼───────────────────┐
│  STEP 12: Regional Language    │  IndicTrans2 (200M distilled)
│  Translation                   │  EN → Hindi, Telugu, Tamil,
│                                │  Bengali, Marathi, Kannada
└────────────┬───────────────────┘
             │
┌────────────▼───────────────────┐
│  STEP 13: Save Multilingual    │  multilingual_pipeline_output.xlsx
│  Output                        │  + HTML with language tabs
└────────────┬───────────────────┘
             │
┌────────────▼───────────────────┐
│  STEP 14: Multilingual Summary │  Per-language stats, char/word
│  Report                        │  counts, sample translations
└────────────────────────────────┘
```

---

## Detailed Step-by-Step Walkthrough

### STEP 0: Local Library Installation

**Why?** Kaggle pre-installs `spacy 3.9+`, but `scispacy`'s biomedical model `en_core_sci_md-0.5.4` requires `spacy < 3.8`. Installing into a local folder (`/kaggle/working/local_libs/`) and inserting it at the front of `sys.path` lets us override Kaggle's system packages without conflicts.

```python
LOCAL_LIB = "/kaggle/working/local_libs"
os.makedirs(LOCAL_LIB, exist_ok=True)
sys.path.insert(0, LOCAL_LIB)
```

**Key version pins:**

- `numpy==1.26.4` (ABI compatibility with pandas)
- `pandas==2.2.2` (compiled against numpy 1.x)
- `spacy>=3.7.4,<3.8.0` (required by en_core_sci_md-0.5.4)
- `packaging` (for transformers version detection)

**Not installed:** `datasets` (HuggingFace) — causes `BucketNotFoundError` on Kaggle. Replaced with PyTorch `Dataset`.

---

### STEP 1: Imports

Standard scientific Python + HuggingFace ecosystem:

- `transformers`: IndicBART model, tokenizer, Seq2SeqTrainer
- `torch.utils.data.Dataset as TorchDataset`: Replaces HuggingFace datasets
- `scispacy` + `en_core_sci_md`: Biomedical sentence splitting + NER
- `textstat`: Readability metrics
- `packaging.version`: Detect transformers version for `processing_class` vs `tokenizer`
- `tqdm`: Progress bars

---

### STEP 2: Load All Datasets

Auto-locates files using `glob.glob("/kaggle/input/**/<filename>", recursive=True)`.

**ICD Code auto-detection:** The ICD sheet has inconsistent header rows. The code scans rows 0–4 to find the real header, then uses flexible column name matching.

---

### STEP 3: Data Analytics (NEW in v2)

Quantifies **why v1 failed**:

| Analysis | Finding |
|---|---|
| Length distribution | data.tsv avg 227 words; discharge summaries avg 599 words (2.6× longer) |
| Domain | data.tsv: PubMed abstracts; summaries: clinical patient records |
| Entity frequency | sepsis in 66/200, pneumonia in 98/200, hypertension in 64/200 |

This justifies the v2 approach: sentence-level chunked processing + entity preservation.

---

### STEP 4: Preprocess, Sentence Split, NER & Abbreviation Expansion

For each of the 200 discharge summaries:

1. **Clean placeholders:** `[person]` → `the patient`, `{organization}` → `the hospital`
2. **Expand abbreviations:** 301-entry dictionary (e.g., `uti` → `urinary tract infection`)
3. **Sentence split:** Using spaCy `doc.sents`
4. **NER per sentence:** Extract medical entities using `en_core_sci_md`
5. **Chunk into ~200-word groups:** Groups consecutive sentences to match training data length

**Output data structure:**

```python
all_processed[i] = {
    "idx": i,
    "original": raw_text,
    "expanded": abbreviation_expanded_text,
    "sentence_data": [
        {"text": "...", "entities": [...], "entity_texts": {"sepsis", ...}},
        ...
    ],
    "chunks": [[sent1, sent2], [sent3, sent4, sent5], ...],
    "all_entities": [{"entity": "sepsis", "label": "ENTITY"}, ...],
}
```

---

### STEP 5: Entity-Preserving Lay Dictionary + Rule-Based Simplification

**90+ entry Indian Lay Dictionary** with entity-aware replacement logic:

| Medical Term | Is NER Entity? | Output |
|---|---|---|
| hypertension | Yes | `high BP (hypertension)` |
| myocardial infarction | Yes | `heart attack (myocardial infarction)` |
| administer | No | `give` |
| orally | No | `by mouth` |
| diabetes mellitus | Yes | `sugar disease (diabetes)` ← parens already in lay term, no double-up |

**Key rule:** If the lay term already contains parentheses (e.g., `"sugar disease (diabetes)"`), don't add another pair.

The **rule-based output** is always generated and stored as `proc["rule_based_full"]`. This serves as the reliable fallback when the model hallucinates in Step 7.

---

### STEP 6: Fine-Tune IndicBART

**Why IndicBART?**

- Multilingual model by AI4Bharat supporting 11 Indian languages + English
- mBART-based Seq2Seq architecture ideal for text-to-text generation
- Pre-trained on large-scale Indian language data

**Fine-tuning configuration:**

| Parameter | Value |
|---|---|
| Base model | `ai4bharat/IndicBART` |
| Training data | 10,000 rows from `data.tsv` |
| Train/Eval split | 90% / 10% |
| Epochs | 3 |
| Batch size | 4 per device |
| Learning rate | 3e-5 |
| Max source/target | 256 tokens |
| Precision | FP16 (GPU) |

**v2 changes from v1:**

- Uses `SimplificationDataset(TorchDataset)` instead of `Dataset.from_pandas()` (avoids `datasets` import error)
- Uses `processing_class=tokenizer` for transformers ≥ 4.46 (avoids deprecation `FutureWarning`)

---

### STEP 7: Chunk-Level Generation with Quality Gates (NEW in v2)

For each ~200-word **chunk** (not the whole 600-word document):

1. **Generate:** Feed chunk to fine-tuned IndicBART with beam search
2. **Clean:** Strip `<2en>`, `<s>`, `</s>` decoder artefacts
3. **Quality gate** (ALL must pass):

| Check | Threshold | Rejection reason |
|---|---|---|
| Hallucination markers | `"this study"`, `"researchers found"`, etc. absent from original | Model generating research text, not clinical |
| Entity recall | ≥ 40% of NER entities preserved | Model deleting medical entities |
| Length ratio | 0.25 – 3.0 × original | Model truncating or hallucinating long text |

1. **If passed:** Apply lay dictionary on model output → final chunk
2. **If failed:** Use rule-based version from Step 5 → final chunk

**Checkpoints** saved every 50 summaries to `/kaggle/working/checkpoint_{n}.xlsx`.

---

### STEP 8: Entity Verification & Assembly (NEW in v2)

Post-processing safety net:

1. Compare all NER entities from Step 4 against the final simplified text
2. For each entity: check if the entity text OR its lay dictionary equivalent is present
3. **Missing critical entities** are re-injected as a bracketed note:

```
"... patient condition improved. [Other medical details: serious blood infection (sepsis), low blood (anemia).]"
```

This guarantees that no disease name is silently lost.

---

### STEP 9: Evaluation

| Metric | Description | Ideal |
|---|---|---|
| Flesch Reading Ease (original) | Input readability | Baseline |
| Flesch Reading Ease (simplified) | Output readability | ↑ Higher = easier |
| Flesch Reading Ease (rule-based) | Rule-based output readability | Comparison |
| Flesch Improvement | simplified − original | > 0 |
| Word Count (original / simplified) | Length comparison | — |
| Compression Ratio | simplified / original | < 1.0 |

---

### STEP 10: Save Output

All results saved to `/kaggle/working/lay_english_pipeline_output.xlsx`:

| Column | Description |
|---|---|
| `translated discharge_summary` | Original input |
| `expanded_summary` | After abbreviation expansion |
| `rule_based_simplified` | Rule-based only (always available) |
| `indian_lay_english` | **Final output** (model + rule hybrid, entity-verified) |
| `medical_entities` | NER entities extracted (as string) |
| `flesch_original / simplified / rule_based` | Readability scores |
| `compression_ratio` | Word count ratio |

---

### STEP 11: Summary Report

Prints aggregate statistics including:

- Readability improvement (original → rule-based → final)
- Compression ratio
- Model-accepted vs rule-based-fallback chunk counts
- **Entity recall audit**: for key terms (sepsis, pneumonia, hypertension, etc.), shows how many appear in original vs output vs lay equivalent

---

### STEP 12: Regional Indian Language Translation (IndicTrans2)

**Model:** `ai4bharat/indictrans2-en-indic-dist-200M` — a distilled 200M-parameter model from AI4Bharat, purpose-built for English → Indian language translation covering all 22 scheduled Indian languages.

**Process:**

1. Free IndicBART from GPU (`del model`, `torch.cuda.empty_cache()`) to reclaim VRAM
2. Load IndicTrans2 + `IndicProcessor` from `IndicTransToolkit`
3. For each summary, split into sentences (avg 700+ words per summary — too long for single-pass translation)
4. Translate in batches of 16 sentences using beam search (num_beams=5)
5. `IndicProcessor` handles pre/post-processing: script normalisation, tokenisation, de-romanisation

**Target languages:**

| Language | IndicTrans2 Code | Script |
|----------|-----------------|--------|
| Hindi | `hin_Deva` | Devanagari |
| Telugu | `tel_Telu` | Telugu |
| Tamil | `tam_Taml` | Tamil |
| Bengali | `ben_Beng` | Bengali |
| Marathi | `mar_Deva` | Devanagari |
| Kannada | `kan_Knda` | Kannada |

**Checkpointing:** After completing each language, saves `translation_checkpoint_{lang}.xlsx`.

---

### STEP 13: Save Multilingual Output

Saves the complete multilingual pipeline output in two formats:

- **Excel** (`multilingual_pipeline_output.xlsx`): formatted with wrapped text, coloured headers, wide columns for all 7 language columns
- **HTML** (`multilingual_pipeline_output.html`): browser-friendly report with **tab-based navigation** — click a language tab to switch between English Lay, Hindi, Telugu, Tamil, Bengali, Marathi, Kannada translations

---

### STEP 14: Multilingual Summary Report

Prints per-language statistics:

- Average character and word counts per language
- Translation error count (if any sentences failed)
- First 200 characters of Row 0 in each language as a sample
- Comparison against English Lay English baseline

---

## How to Run

1. **Create a new Kaggle Notebook**
2. **Add datasets** (right panel → Add Data):
   - Upload `anotated_dataset_v2.xlsx`
   - Upload `data/` folder (containing `data.tsv`)
   - Upload `mtsamples.csv/`
   - Upload `predictions-t5-base.tsv`
   - Upload `PMC-Patients-V2.json`
3. **Settings:**
   - Internet → **ON**
   - Accelerator → **GPU T4 x2**
4. **Import the notebook** (`medical_lay_english_pipeline.ipynb`)
5. **Run Step 0** (install), then **Kernel → Restart**
6. **Run All** remaining cells (takes ~30–45 minutes with fine-tuning, plus ~20–30 minutes for regional translation)
7. **Download** `lay_english_pipeline_output.xlsx` from `/kaggle/working/`

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `numpy.dtype size changed` | Ensure `numpy==1.26.4` and `pandas==2.2.2` are installed to local_libs |
| `ModuleNotFoundError: spacy.pipeline.factories` | Ensure `spacy>=3.7.4,<3.8.0` — Kaggle ships 3.9+ which breaks scispacy |
| `OSError: Can't find model en_core_sci_md` | The pip install in Step 0 handles this; restart kernel if needed |
| `KeyError: 'CID Subcategory'` | Auto-detection scans header rows 0–4; uses positional fallback |
| `BucketNotFoundError` from `datasets` import | v2 removed `datasets` library — uses PyTorch Dataset instead |
| `FutureWarning: tokenizer` in Seq2SeqTrainer | v2 auto-detects transformers version and uses `processing_class` |
| CUDA out of memory | Reduce `FINETUNE_BATCH` to 2. Reduce `MAX_SRC_LEN` / `MAX_TGT_LEN` to 128 |
| Slow fine-tuning | Reduce `FINETUNE_ROWS` to 5000. Use single epoch. |

---

## Architecture Diagram (v2)

```
                    ┌─────────────────────┐
                    │  Annotated Dataset   │
                    │  (200 summaries)     │
                    └─────────┬───────────┘
                              │
               ┌──────────────▼──────────────┐
               │  Preprocessing Pipeline      │
               │  (Steps 3–5)                 │
               │                              │
               │  Analytics → Clean → Expand  │
               │  → Sentence Split → NER      │
               │  → ~200-word Chunks          │
               │  → Entity-Preserving Lay Dict│
               │  → Rule-Based Simplification │
               └──────────────┬──────────────┘
                              │
               ┌──────────────▼──────────────┐
               │   Rule-Based Output          │◄── Always available
               │   (fallback for every chunk) │    as safety net
               └──────────────┬──────────────┘
                              │
          ┌───────────────────▼───────────────────┐
          │         Fine-Tuned IndicBART           │
          │  + Quality Gates (Step 6–7)            │
          │                                        │
          │  For each chunk:                       │
          │  ├─ Generate with beam search          │
          │  ├─ Check: hallucination? entity loss?  │
          │  ├─ PASS → use model output + lay dict │
          │  └─ FAIL → use rule-based fallback     │
          └───────────────────┬───────────────────┘
                              │
               ┌──────────────▼──────────────┐
               │  Entity Verification (Step 8)│
               │  Re-inject missing entities  │
               └──────────────┬──────────────┘
                              │
               ┌──────────────▼──────────────┐
               │  Final Indian Lay English    │
               │  Output                      │
               └──────────────┬──────────────┘
                              │
               ┌──────────────▼──────────────┐
               │  Evaluation & Reporting      │
               │  (Steps 9–11)                │
               │  Flesch, Entity Audit, XLSX  │
               └─────────────────────────────┘
```

---

## File Outputs

| File | Location | Description |
|---|---|---|
| `lay_english_pipeline_output.xlsx` | `/kaggle/working/` | Final output with all columns and metrics |
| `checkpoint_{n}.xlsx` | `/kaggle/working/` | Intermediate checkpoints during generation |
| `indicbart-finetuned/` | `/kaggle/working/` | Fine-tuned model weights + tokenizer |

Columns in the output Excel:

- `translated discharge_summary` — original input
- `expanded_summary` — after abbreviation expansion
- `rule_based_simplified` — entity-preserving rule-based output (always available)
- `indian_lay_english` — **final output** (quality-gated model + rule-based hybrid, entity-verified)
- `medical_entities` — extracted NER entities
- `flesch_original`, `flesch_simplified`, `flesch_rule_based` — readability scores
- `compression_ratio` — word count ratio

---

## References

- **IndicBART**: Dabre et al., "IndicBART: A Pre-trained Model for Natural Language Generation of Indic Languages" (AI4Bharat)
- **scispaCy**: Neumann et al., "ScispaCy: Fast and Robust Models for Biomedical Natural Language Processing" (AllenAI)
- **Flesch Reading Ease**: Flesch, Rudolf (1948), "A New Readability Yardstick"
- **data.tsv**: Medical text simplification corpus from PubMed abstracts

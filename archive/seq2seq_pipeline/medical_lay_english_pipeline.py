"""
Medical Discharge Summary → Indian Lay English Pipeline
========================================================
Platform: Kaggle Notebook (GPU T4 x2 or P100)

Before running:
  1. Add ALL datasets via Add Data → Your Datasets (right panel):
     - anotated_dataset_v2.xlsx
     - data/ (containing data.tsv)
     - mtsamples.csv/
     - predictions-t5-base.tsv
     - PMC-Patients-V2.json
  2. Enable Internet: Settings → Internet → ON
  3. Enable GPU: Settings → Accelerator → GPU T4 x2
"""

# ═══════════════════════════════════════════════════════════════
# STEP 0: LOCAL LIBRARY INSTALLATION (Kaggle-safe)
# ═══════════════════════════════════════════════════════════════
# Install into a local folder inside /kaggle/working/ so packages
# survive restarts and avoid conflicts with Kaggle system packages.

import subprocess, sys, os

LOCAL_LIB = "/kaggle/working/local_libs"
os.makedirs(LOCAL_LIB, exist_ok=True)

# Insert at front of sys.path so our versions take priority
if LOCAL_LIB not in sys.path:
    sys.path.insert(0, LOCAL_LIB)

def _pip_install(*args):
    """Install packages into the local lib directory."""
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q",
         "--target", LOCAL_LIB, *args],
        check=True
    )

print("Installing libraries into local_libs/ …")
_pip_install("numpy==1.26.4")
_pip_install("pandas==2.2.2", "openpyxl")
_pip_install("spacy>=3.7.4,<3.8.0")
_pip_install("transformers", "sentencepiece", "accelerate", "datasets")
_pip_install("scispacy")
_pip_install("https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_md-0.5.4.tar.gz")
_pip_install("textstat", "bert-score", "tqdm")
print("  ✓ All libraries installed to", LOCAL_LIB)

# ═══════════════════════════════════════════════════════════════
# STEP 1: IMPORTS
# ═══════════════════════════════════════════════════════════════
import re
import glob
import warnings
import pandas as pd
import numpy as np
import spacy
import textstat
import torch
from tqdm import tqdm
from collections import Counter
from transformers import (
    AutoTokenizer, AutoModelForSeq2SeqLM,
    Seq2SeqTrainer, Seq2SeqTrainingArguments,
    DataCollatorForSeq2Seq,
)
from datasets import Dataset

warnings.filterwarnings("ignore")

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# ═══════════════════════════════════════════════════════════════
# STEP 2: LOAD ALL DATASETS
# ═══════════════════════════════════════════════════════════════

def _locate(pattern):
    """Find a file under /kaggle/input/ or fall back to filename."""
    hits = glob.glob(f"/kaggle/input/**/{pattern}", recursive=True)
    return hits[0] if hits else pattern

# --- 2a. Annotated discharge summaries (200 rows) ---
ANNOTATED_PATH = _locate("anotated_dataset_v2.xlsx")
df = pd.read_excel(ANNOTATED_PATH, sheet_name="annotated_dataset")
print(f"[annotated_dataset] {len(df)} rows | cols: {list(df.columns)}")

# --- 2b. Abbreviations dictionary ---
abbr_df = pd.read_excel(ANNOTATED_PATH, sheet_name="abbreviations")
abbr_dict = dict(
    zip(
        abbr_df["abbreviated word"].astype(str).str.lower().str.strip(),
        abbr_df["translated"].astype(str).str.strip(),
    )
)
print(f"[abbreviations]     {len(abbr_dict)} entries")

# --- 2c. ICD Codes dictionary (auto-detect header row) ---
def _find_col(frame, *candidates):
    """Return first matching column name (case-insensitive)."""
    lower_map = {str(c).lower().strip(): c for c in frame.columns}
    for cand in candidates:
        hit = lower_map.get(cand.lower().strip())
        if hit:
            return hit
    return None

icd_df = None
for _hdr in range(5):
    _tmp = pd.read_excel(ANNOTATED_PATH, sheet_name="ICD Codes", header=_hdr)
    if not all(str(c).startswith("Unnamed") for c in _tmp.columns):
        icd_df = _tmp
        break
if icd_df is None:
    icd_df = pd.read_excel(ANNOTATED_PATH, sheet_name="ICD Codes", header=None)
    icd_df.columns = [f"col_{i}" for i in range(icd_df.shape[1])]

_k = _find_col(icd_df, "CID Subcategory", "ICD Subcategory", "Subcategory", "Code", "col_0")
_v = _find_col(icd_df, "Translated Subcat Description", "Translated Description", "Description", "col_1")
icd_dict = dict(zip(
    icd_df[_k].astype(str).str.lower().str.strip(),
    icd_df[_v].astype(str).str.strip()
)) if _k and _v else {}
print(f"[ICD Codes]         {len(icd_dict)} entries  (key='{_k}', val='{_v}')")

# --- 2d. data.tsv — fine-tuning data (original ↔ simplified pairs) ---
DATA_TSV_PATH = _locate("data.tsv")
finetune_df = pd.read_csv(DATA_TSV_PATH, sep="\t", low_memory=False)
print(f"[data.tsv]          {len(finetune_df)} rows | cols: {list(finetune_df.columns)}")

# --- 2e. predictions-t5-base.tsv — for benchmarking ---
T5_PRED_PATH = _locate("predictions-t5-base.tsv")
t5_df = pd.read_csv(T5_PRED_PATH, sep="\t")
print(f"[predictions-t5]    {len(t5_df)} rows | cols: {list(t5_df.columns)}")

# --- 2f. mtsamples.csv — additional medical transcriptions ---
MT_PATH = _locate("mtsamples.csv")
mt_df = pd.read_csv(MT_PATH)
print(f"[mtsamples.csv]     {len(mt_df)} rows | cols: {list(mt_df.columns)}")

# --- 2g. PMC-Patients-V2.json ---
PMC_PATH = _locate("PMC-Patients-V2.json")
print(f"[PMC-Patients]      located: {PMC_PATH}")

# ═══════════════════════════════════════════════════════════════
# STEP 3: TEXT PREPROCESSING
# ═══════════════════════════════════════════════════════════════

def preprocess_text(text):
    """Lowercase + collapse whitespace. Preserves [person] and {organization} placeholders."""
    if not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", text.lower()).strip()

# ═══════════════════════════════════════════════════════════════
# STEP 4: ABBREVIATION EXPANSION
# ═══════════════════════════════════════════════════════════════

def expand_abbreviations(text, abbr_dict):
    """Replace abbreviated tokens with full translated forms (punctuation-aware)."""
    if not isinstance(text, str):
        return ""
    tokens = text.split()
    expanded = []
    for token in tokens:
        stripped = token.strip(".,;:!?()[]{}\"'")
        lookup = stripped.lower()
        if lookup in abbr_dict:
            prefix = token[:token.index(stripped)] if stripped and token.index(stripped) > 0 else ""
            suffix = token[token.index(stripped) + len(stripped):]
            expanded.append(prefix + abbr_dict[lookup] + suffix)
        else:
            expanded.append(token)
    return " ".join(expanded)

print("\nApplying preprocessing + abbreviation expansion …")
df["preprocessed"] = df["translated discharge_summary"].apply(preprocess_text)
df["expanded_summary"] = df["preprocessed"].apply(lambda t: expand_abbreviations(t, abbr_dict))
print("  ✓ Abbreviation expansion complete.")

# ═══════════════════════════════════════════════════════════════
# STEP 5: MEDICAL NER USING scispaCy
# ═══════════════════════════════════════════════════════════════
print("\nLoading scispaCy en_core_sci_md …")
nlp = spacy.load("en_core_sci_md")
print("  ✓ scispaCy model loaded.")

def extract_medical_entities(text):
    """Extract named entities → list of dicts {entity, label, start, end}."""
    if not isinstance(text, str) or len(text.strip()) == 0:
        return []
    doc = nlp(text)
    return [{"entity": e.text, "label": e.label_,
             "start": e.start_char, "end": e.end_char} for e in doc.ents]

def get_unique_medical_terms(text):
    """Return flat sorted list of unique entity strings."""
    if not isinstance(text, str) or len(text.strip()) == 0:
        return []
    return sorted(set(e.text for e in nlp(text).ents))

print("Extracting medical entities …")
tqdm.pandas(desc="NER")
df["medical_entities"] = df["expanded_summary"].progress_apply(extract_medical_entities)
print("  ✓ Medical entity extraction complete.")

# ═══════════════════════════════════════════════════════════════
# STEP 6: LAY DICTIONARY REPLACEMENT
# ═══════════════════════════════════════════════════════════════

INDIAN_LAY_DICT = {
    # Conditions
    "hypertension": "high BP", "diabetes mellitus": "sugar disease (diabetes)",
    "myocardial infarction": "heart attack", "acute renal failure": "sudden kidney failure",
    "chronic renal failure": "long-term kidney problem",
    "septicemia": "blood infection (sepsis)", "sepsis": "serious blood infection",
    "pneumonia": "lung infection", "tuberculosis": "TB (tuberculosis)",
    "pneumothorax": "air trapped in chest", "endocarditis": "infection of heart valves",
    "spondylodiscitis": "spine bone infection", "hypotension": "low BP",
    "pyrexia": "fever", "dyspnea": "difficulty in breathing",
    "edema": "swelling", "abscess": "pus-filled swelling",
    "crohn's disease": "long-term bowel disease (Crohn's)",
    "renal failure": "kidney failure", "cerebrovascular accident": "brain stroke",
    "anemia": "low blood (anemia)", "tachycardia": "fast heartbeat",
    "bradycardia": "slow heartbeat", "atrial fibrillation": "irregular heartbeat",
    # Procedures & Treatments
    "hemodialysis": "kidney dialysis", "tracheostomy": "breathing tube in neck",
    "thoracotomy": "chest surgery", "pneumonectomy": "removal of a lung",
    "ileocolectomy": "removal of part of bowel",
    "anastomosis": "surgical joining of bowel ends",
    "debridement": "surgical wound cleaning",
    "arteriovenous fistula": "dialysis access point on arm",
    "intramuscular": "given as a muscle injection",
    "intravenous": "given through a vein (drip)",
    "percutaneous": "through the skin",
    "antibiotic therapy": "antibiotic treatment",
    "antibiotic": "infection-fighting medicine",
    # Lab & Medical Terms
    "blood culture": "blood test to find infection",
    "procalcitonin": "blood marker for infection",
    "hemoglobin": "blood count (Hb)", "creatinine": "kidney function marker",
    "bilirubin": "liver function marker", "saturation": "oxygen level in blood",
    "afebrile": "no fever", "eupneic": "breathing normally",
    "acyanotic": "no bluish discoloration",
    "anicteric": "no yellowing of skin/eyes",
    "vesicular breath sounds": "normal breathing sounds",
    # Hospital / Admin
    "discharge": "sent home from hospital",
    "outpatient clinic": "OPD (Out Patient Department)",
    "follow-up": "return visit to doctor", "ward": "general hospital room",
    "intensive care unit": "ICU (serious care room)",
    "sus": "government health scheme", "orally": "by mouth", "administer": "give",
}

def apply_lay_dictionary(text, lay_dict):
    """Replace medical terms longest-first to avoid partial matches."""
    if not isinstance(text, str):
        return ""
    text_lower = text.lower()
    for key in sorted(lay_dict, key=len, reverse=True):
        text_lower = text_lower.replace(key, lay_dict[key])
    return text_lower

print("\nApplying lay-dictionary replacements …")
df["lay_replaced_summary"] = df["expanded_summary"].apply(
    lambda t: apply_lay_dictionary(t, INDIAN_LAY_DICT)
)
print("  ✓ Lay-dictionary replacement complete.")

# ═══════════════════════════════════════════════════════════════
# STEP 7a: FINE-TUNE IndicBART ON data.tsv
# ═══════════════════════════════════════════════════════════════
MODEL_NAME = "ai4bharat/IndicBART"
FINETUNE_ROWS = 10000        # tunable: set higher for better quality
FINETUNE_EPOCHS = 3
FINETUNE_BATCH = 4
FINETUNE_LR = 3e-5
MAX_SRC_LEN = 256
MAX_TGT_LEN = 256
OUTPUT_DIR = "/kaggle/working/indicbart-finetuned"

print(f"\n{'='*65}")
print("  STEP 7a: Fine-tuning IndicBART on medical simplification data")
print(f"{'='*65}")

# Filter rows with both original + simplified text present
ft = finetune_df[["original", "english simplified"]].dropna()
ft = ft[ft["original"].str.strip().astype(bool) & ft["english simplified"].str.strip().astype(bool)]
ft = ft.head(FINETUNE_ROWS).reset_index(drop=True)
print(f"  Fine-tuning samples: {len(ft)}")

# Load tokenizer + base model
print("  Loading IndicBART base model …")
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME, do_lower_case=False, use_fast=False, keep_accents=True
)
base_model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
DECODER_START_ID = tokenizer.convert_tokens_to_ids("<2en>")

# Tokenization for training
def preprocess_for_training(examples):
    """Tokenize src (original) → tgt (simplified) for Seq2Seq training."""
    sources = ["<s> " + s + " </s> <2en>" for s in examples["original"]]
    targets = examples["english simplified"]
    model_inputs = tokenizer(sources, max_length=MAX_SRC_LEN, truncation=True, padding="max_length")
    labels = tokenizer(targets, max_length=MAX_TGT_LEN, truncation=True, padding="max_length")
    labels["input_ids"] = [
        [(tok if tok != tokenizer.pad_token_id else -100) for tok in label]
        for label in labels["input_ids"]
    ]
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

hf_dataset = Dataset.from_pandas(ft)
split = hf_dataset.train_test_split(test_size=0.1, seed=42)
train_ds = split["train"].map(preprocess_for_training, batched=True,
                               remove_columns=["original", "english simplified"])
eval_ds  = split["test"].map(preprocess_for_training, batched=True,
                               remove_columns=["original", "english simplified"])
print(f"  Train: {len(train_ds)}  |  Eval: {len(eval_ds)}")

training_args = Seq2SeqTrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=FINETUNE_EPOCHS,
    per_device_train_batch_size=FINETUNE_BATCH,
    per_device_eval_batch_size=FINETUNE_BATCH,
    learning_rate=FINETUNE_LR,
    weight_decay=0.01,
    warmup_steps=200,
    eval_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=2,
    predict_with_generate=True,
    fp16=(device == "cuda"),
    logging_steps=100,
    report_to="none",
    load_best_model_at_end=True,
    generation_max_length=MAX_TGT_LEN,
)

data_collator = DataCollatorForSeq2Seq(tokenizer, model=base_model, padding=True)

print(f"  Training: {FINETUNE_EPOCHS} epochs, batch={FINETUNE_BATCH}, lr={FINETUNE_LR}")
trainer = Seq2SeqTrainer(
    model=base_model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=eval_ds,
    tokenizer=tokenizer,
    data_collator=data_collator,
)
trainer.train()
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"  ✓ Fine-tuned model saved to {OUTPUT_DIR}")

# ═══════════════════════════════════════════════════════════════
# STEP 7b: GENERATE LAY ENGLISH WITH FINE-TUNED MODEL
# ═══════════════════════════════════════════════════════════════
print(f"\n{'='*65}")
print("  STEP 7b: Generating Lay English (fine-tuned IndicBART)")
print(f"{'='*65}")

model = AutoModelForSeq2SeqLM.from_pretrained(OUTPUT_DIR).to(device)
model.eval()

def generate_indian_lay_english(text, model, tokenizer):
    """Generate simplified Indian Lay English using fine-tuned IndicBART."""
    if not isinstance(text, str) or len(text.strip()) == 0:
        return text if isinstance(text, str) else ""
    try:
        input_text = "<s> " + text + " </s> <2en>"
        inputs = tokenizer(
            input_text, max_length=512, truncation=True,
            padding=True, return_tensors="pt"
        ).to(device)
        with torch.no_grad():
            output_ids = model.generate(
                **inputs, max_length=300, num_beams=4,
                early_stopping=True, no_repeat_ngram_size=3,
                decoder_start_token_id=DECODER_START_ID,
            )
        return tokenizer.decode(output_ids[0], skip_special_tokens=True)
    except Exception as e:
        print(f"  ⚠ Generation failed: {e}")
        return text

BATCH_SIZE = 10
CHECKPOINT_INTERVAL = 50
total_rows = len(df)

df["indian_lay_english"] = ""
for start in tqdm(range(0, total_rows, BATCH_SIZE), desc="Generating"):
    end = min(start + BATCH_SIZE, total_rows)
    for idx in range(start, end):
        df.at[idx, "indian_lay_english"] = generate_indian_lay_english(
            df.at[idx, "lay_replaced_summary"], model, tokenizer
        )
    if (end % CHECKPOINT_INTERVAL == 0) or (end == total_rows):
        df.to_excel(f"/kaggle/working/checkpoint_{end}.xlsx", index=False)
        print(f"  💾 Checkpoint at row {end}")

print("  ✓ Generation complete.")

# ═══════════════════════════════════════════════════════════════
# STEP 8: EVALUATION
# ═══════════════════════════════════════════════════════════════

def evaluate_summary(original, simplified):
    """Compute Flesch readability, word counts, compression ratio."""
    if not isinstance(original, str) or not original.strip():
        original = ""
    if not isinstance(simplified, str) or not simplified.strip():
        simplified = ""
    flesch_orig = textstat.flesch_reading_ease(original) if original else 0.0
    flesch_simp = textstat.flesch_reading_ease(simplified) if simplified else 0.0
    wc_orig = len(original.split())
    wc_simp = len(simplified.split())
    return {
        "flesch_original": flesch_orig,
        "flesch_simplified": flesch_simp,
        "flesch_improvement": flesch_simp - flesch_orig,
        "word_count_original": wc_orig,
        "word_count_simplified": wc_simp,
        "compression_ratio": wc_simp / wc_orig if wc_orig > 0 else 0.0,
    }

print("\nRunning evaluation …")
eval_results = [
    evaluate_summary(df.at[i, "translated discharge_summary"], df.at[i, "indian_lay_english"])
    for i in tqdm(range(len(df)), desc="Eval")
]
eval_df = pd.DataFrame(eval_results)
for col in eval_df.columns:
    df[col] = eval_df[col].values
print("  ✓ Evaluation complete.")

# ═══════════════════════════════════════════════════════════════
# STEP 9: SAVE OUTPUT
# ═══════════════════════════════════════════════════════════════
df["medical_entities"] = df["medical_entities"].apply(str)

OUTPUT_COLUMNS = [
    "translated discharge_summary", "expanded_summary", "medical_entities",
    "lay_replaced_summary", "indian_lay_english",
    "translated diagnosis_ICD", "translanted outcome",
    "lenght of stay", "medical specialties",
    "flesch_original", "flesch_simplified", "flesch_improvement",
    "word_count_original", "word_count_simplified", "compression_ratio",
]
existing_cols = [c for c in OUTPUT_COLUMNS if c in df.columns]
missing_cols  = [c for c in OUTPUT_COLUMNS if c not in df.columns]
if missing_cols:
    print(f"  ⚠ Missing columns (skipped): {missing_cols}")

OUTPUT_PATH = "/kaggle/working/lay_english_pipeline_output.xlsx"
df[existing_cols].to_excel(OUTPUT_PATH, index=False)
print(f"\n  ✓ Output saved to {OUTPUT_PATH}")

# ═══════════════════════════════════════════════════════════════
# STEP 10: SUMMARY REPORT
# ═══════════════════════════════════════════════════════════════
print(f"\n{'='*65}")
print("                    PIPELINE SUMMARY REPORT")
print(f"{'='*65}")
print(f"  Total summaries processed        : {len(df)}")
print(f"  Fine-tuning samples used         : {len(ft)}")
print(f"  Avg Flesch (original)            : {df['flesch_original'].mean():.2f}")
print(f"  Avg Flesch (simplified)          : {df['flesch_simplified'].mean():.2f}")
print(f"  Avg Flesch improvement           : {df['flesch_improvement'].mean():.2f}")
print(f"  Avg word count (original)        : {df['word_count_original'].mean():.1f}")
print(f"  Avg word count (simplified)      : {df['word_count_simplified'].mean():.1f}")
print(f"  Avg compression ratio            : {df['compression_ratio'].mean():.3f}")

improved_count = (df["flesch_improvement"] > 0).sum()
print(f"  Summaries with Flesch improvement: {improved_count} / {len(df)}")

all_entities = []
for ent_str in df["medical_entities"]:
    try:
        ent_list = eval(ent_str) if isinstance(ent_str, str) else ent_str
        if isinstance(ent_list, list):
            for e in ent_list:
                if isinstance(e, dict) and "entity" in e:
                    all_entities.append(e["entity"].lower())
    except Exception:
        pass

entity_counts = Counter(all_entities)
print("\n  Top 10 medical entities:")
for term, count in entity_counts.most_common(10):
    print(f"    {term:40s}  —  {count}")

print(f"\n{'='*65}")
print("  Pipeline finished successfully.")
print(f"{'='*65}")
"""
Medical Discharge Summary → Indian Lay English Pipeline
========================================================
Platform: Kaggle Notebook (GPU T4 x2 or P100)

Before running:
  1. Add your dataset containing 'anotated_dataset_v2.xlsx' via
     Add Data → Your Datasets (right panel).
  2. Enable Internet: Settings → Internet → ON
     (required to download IndicBART from Hugging Face)
  3. Enable GPU accelerator in Settings → Accelerator.
"""

# ═══════════════════════════════════════════════════════════════
# STEP 1: SETUP & INSTALL LIBRARIES
# ═══════════════════════════════════════════════════════════════
# Run ONLY this cell first, then use:
#   Kernel → Restart & Run All  (to reload with the pinned versions)
#
# Version constraints:
#   numpy==1.26.4       — scispacy/thinc require numpy<2.0
#   pandas==2.2.2       — compiled against numpy 1.x ABI
#   spacy>=3.7.4,<3.8.0 — en_core_sci_md-0.5.4 requires spacy<3.8
#
# !pip install -q "numpy==1.26.4"
# !pip install -q "pandas==2.2.2" openpyxl
# !pip install -q "spacy>=3.7.4,<3.8.0"
# !pip install -q transformers sentencepiece
# !pip install -q scispacy
# !pip install -q https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_md-0.5.4.tar.gz
# !pip install -q textstat bert-score tqdm

import os
import re
import warnings
import pandas as pd
import numpy as np
import spacy
import textstat
import torch
from tqdm import tqdm
from collections import Counter
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

warnings.filterwarnings("ignore")

# GPU setup
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# ═══════════════════════════════════════════════════════════════
# STEP 2: LOAD DATASET
# ═══════════════════════════════════════════════════════════════
import glob as _glob

# Auto-locate the file anywhere under /kaggle/input/ or current dir
_matches = _glob.glob("/kaggle/input/**/anotated_dataset_v2.xlsx", recursive=True)
DATASET_PATH = _matches[0] if _matches else "anotated_dataset_v2.xlsx"
print(f"Dataset path: {DATASET_PATH}")

# --- Main annotated dataset ---
df = pd.read_excel(DATASET_PATH, sheet_name="annotated_dataset")
print(f"Loaded annotated_dataset: {len(df)} rows, columns: {list(df.columns)}")

# --- Abbreviations lookup dictionary ---
abbr_df = pd.read_excel(DATASET_PATH, sheet_name="abbreviations")
abbr_dict = dict(
    zip(
        abbr_df["abbreviated word"].astype(str).str.lower().str.strip(),
        abbr_df["translated"].astype(str).str.strip(),
    )
)
print(f"Loaded abbreviations dictionary: {len(abbr_dict)} entries")

# --- ICD Codes lookup dictionary ---
# Scan header rows 0-4 to find whichever row has real column names
def _find_col(df, *candidates):
    """Return the first column name that matches any candidate (case-insensitive)."""
    lower_map = {str(c).lower().strip(): c for c in df.columns}
    for cand in candidates:
        hit = lower_map.get(cand.lower().strip())
        if hit:
            return hit
    return None

icd_df = None
for _hdr in range(5):
    _tmp = pd.read_excel(DATASET_PATH, sheet_name="ICD Codes", header=_hdr)
    if not all(str(c).startswith("Unnamed") for c in _tmp.columns):
        icd_df = _tmp
        print(f"ICD sheet — header row {_hdr}, columns: {list(icd_df.columns)}")
        break

if icd_df is None:
    # All rows unnamed: just read raw and use first two non-null columns
    icd_df = pd.read_excel(DATASET_PATH, sheet_name="ICD Codes", header=None)
    icd_df.columns = [f"col_{i}" for i in range(icd_df.shape[1])]
    print(f"ICD sheet — no named header found; raw columns: {list(icd_df.columns)}")

_icd_key_col = _find_col(icd_df, "CID Subcategory", "ICD Subcategory", "Subcategory",
                          "ICD Code", "Code", "col_0")
_icd_val_col = _find_col(icd_df, "Translated Subcat Description", "Translated Description",
                          "Subcat Description", "Description", "col_1")

if _icd_key_col and _icd_val_col:
    icd_dict = dict(
        zip(
            icd_df[_icd_key_col].astype(str).str.lower().str.strip(),
            icd_df[_icd_val_col].astype(str).str.strip(),
        )
    )
    print(f"Loaded ICD codes dictionary: {len(icd_dict)} entries "
          f"(key='{_icd_key_col}', value='{_icd_val_col}')")
else:
    icd_dict = {}
    print(f"  ⚠ ICD dict empty — columns detected: {list(icd_df.columns)}")

# ═══════════════════════════════════════════════════════════════
# STEP 3: TEXT PREPROCESSING
# ═══════════════════════════════════════════════════════════════

def preprocess_text(text):
    """Clean raw discharge summary text.

    Args:
        text: Raw discharge summary string.

    Returns:
        Lowercased text with normalised whitespace.
        Placeholders [person] and {organization} are preserved.
    """
    if not isinstance(text, str):
        return ""
    text = text.lower()
    # Collapse multiple whitespace / newlines into a single space
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ═══════════════════════════════════════════════════════════════
# STEP 4: ABBREVIATION EXPANSION
# ═══════════════════════════════════════════════════════════════

def expand_abbreviations(text, abbr_dict):
    """Replace abbreviated tokens with their full translated forms.

    Args:
        text: Input text string.
        abbr_dict: dict mapping lowercased abbreviation → full form.

    Returns:
        Text with abbreviations expanded.
    """
    if not isinstance(text, str):
        return ""
    tokens = text.split()
    expanded = []
    for token in tokens:
        # Strip trailing punctuation for matching, re-attach after
        stripped = token.strip(".,;:!?()[]{}\"'")
        lookup = stripped.lower()
        if lookup in abbr_dict:
            # Preserve surrounding punctuation
            prefix = token[: token.index(stripped)] if stripped and token.index(stripped) > 0 else ""
            suffix = token[token.index(stripped) + len(stripped):]
            expanded.append(prefix + abbr_dict[lookup] + suffix)
        else:
            expanded.append(token)
    return " ".join(expanded)


print("Applying preprocessing + abbreviation expansion …")
df["preprocessed"] = df["translated discharge_summary"].apply(preprocess_text)
df["expanded_summary"] = df["preprocessed"].apply(lambda t: expand_abbreviations(t, abbr_dict))
print("  ✓ Abbreviation expansion complete.")

# ═══════════════════════════════════════════════════════════════
# STEP 5: MEDICAL NER USING scispaCy
# ═══════════════════════════════════════════════════════════════
print("Loading scispaCy model en_core_sci_md …")
try:
    nlp = spacy.load("en_core_sci_md")
except (OSError, ModuleNotFoundError):
    print("  Model not found or spaCy version mismatch — fixing now …")
    import subprocess, sys
    # Pin spaCy first: en_core_sci_md-0.5.4 requires spacy<3.8.0
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "spacy>=3.7.4,<3.8.0"],
        check=True
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q",
         "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_md-0.5.4.tar.gz"],
        check=True
    )
    # Reload spacy with correct version
    import importlib
    import spacy as _spacy_fresh
    importlib.reload(_spacy_fresh)
    nlp = _spacy_fresh.load("en_core_sci_md")
print("  ✓ scispaCy model loaded.")


def extract_medical_entities(text):
    """Extract named entities from text using scispaCy.

    Args:
        text: Input text string.

    Returns:
        List of dicts with keys: entity, label, start, end.
    """
    if not isinstance(text, str) or len(text.strip()) == 0:
        return []
    doc = nlp(text)
    return [
        {
            "entity": ent.text,
            "label": ent.label_,
            "start": ent.start_char,
            "end": ent.end_char,
        }
        for ent in doc.ents
    ]


def get_unique_medical_terms(text):
    """Return a flat list of unique entity strings from text.

    Args:
        text: Input text string.

    Returns:
        Sorted list of unique entity text strings.
    """
    if not isinstance(text, str) or len(text.strip()) == 0:
        return []
    doc = nlp(text)
    return sorted(set(ent.text for ent in doc.ents))


print("Extracting medical entities …")
tqdm.pandas(desc="NER")
df["medical_entities"] = df["expanded_summary"].progress_apply(extract_medical_entities)
print("  ✓ Medical entity extraction complete.")

# ═══════════════════════════════════════════════════════════════
# STEP 6: MEDICAL TERM → INDIAN LAY TERM DICTIONARY REPLACEMENT
# ═══════════════════════════════════════════════════════════════

INDIAN_LAY_DICT = {
    # Conditions
    "hypertension":                  "high BP",
    "diabetes mellitus":             "sugar disease (diabetes)",
    "myocardial infarction":         "heart attack",
    "acute renal failure":           "sudden kidney failure",
    "chronic renal failure":         "long-term kidney problem",
    "septicemia":                    "blood infection (sepsis)",
    "sepsis":                        "serious blood infection",
    "pneumonia":                     "lung infection",
    "tuberculosis":                  "TB (tuberculosis)",
    "pneumothorax":                  "air trapped in chest",
    "endocarditis":                  "infection of heart valves",
    "spondylodiscitis":              "spine bone infection",
    "hypotension":                   "low BP",
    "pyrexia":                       "fever",
    "dyspnea":                       "difficulty in breathing",
    "edema":                         "swelling",
    "abscess":                       "pus-filled swelling",
    "crohn's disease":               "long-term bowel disease (Crohn's)",
    "renal failure":                 "kidney failure",
    "cerebrovascular accident":      "brain stroke",
    "anemia":                        "low blood (anemia)",
    "tachycardia":                   "fast heartbeat",
    "bradycardia":                   "slow heartbeat",
    "atrial fibrillation":           "irregular heartbeat",
    # Procedures & Treatments
    "hemodialysis":                  "kidney dialysis",
    "tracheostomy":                  "breathing tube in neck",
    "thoracotomy":                   "chest surgery",
    "pneumonectomy":                 "removal of a lung",
    "ileocolectomy":                 "removal of part of bowel",
    "anastomosis":                   "surgical joining of bowel ends",
    "debridement":                   "surgical wound cleaning",
    "arteriovenous fistula":         "dialysis access point on arm",
    "intramuscular":                 "given as a muscle injection",
    "intravenous":                   "given through a vein (drip)",
    "percutaneous":                  "through the skin",
    "antibiotic therapy":            "antibiotic treatment",
    "antibiotic":                    "infection-fighting medicine",
    # Lab & Medical Terms
    "blood culture":                 "blood test to find infection",
    "procalcitonin":                 "blood marker for infection",
    "hemoglobin":                    "blood count (Hb)",
    "creatinine":                    "kidney function marker",
    "bilirubin":                     "liver function marker",
    "saturation":                    "oxygen level in blood",
    "afebrile":                      "no fever",
    "eupneic":                       "breathing normally",
    "acyanotic":                     "no bluish discoloration",
    "anicteric":                     "no yellowing of skin/eyes",
    "vesicular breath sounds":       "normal breathing sounds",
    # Hospital / Admin Terms
    "discharge":                     "sent home from hospital",
    "outpatient clinic":             "OPD (Out Patient Department)",
    "follow-up":                     "return visit to doctor",
    "ward":                          "general hospital room",
    "intensive care unit":           "ICU (serious care room)",
    "sus":                           "government health scheme",
    "orally":                        "by mouth",
    "administer":                    "give",
}


def apply_lay_dictionary(text, lay_dict):
    """Replace medical terms with Indian lay-English equivalents.

    Multi-word terms are replaced first (sorted by key length descending)
    to avoid partial replacements.

    Args:
        text: Input text string (will be lowercased internally).
        lay_dict: dict mapping medical term → lay term.

    Returns:
        Text with medical terms replaced by lay equivalents.
    """
    if not isinstance(text, str):
        return ""
    text_lower = text.lower()
    # Sort keys longest-first so multi-word terms are matched before sub-terms
    for key in sorted(lay_dict.keys(), key=len, reverse=True):
        text_lower = text_lower.replace(key, lay_dict[key])
    return text_lower


print("Applying lay-dictionary replacements …")
df["lay_replaced_summary"] = df["expanded_summary"].apply(
    lambda t: apply_lay_dictionary(t, INDIAN_LAY_DICT)
)
print("  ✓ Lay-dictionary replacement complete.")

# ═══════════════════════════════════════════════════════════════
# STEP 7: INDICBART MODEL FOR INDIAN LAY ENGLISH GENERATION
# ═══════════════════════════════════════════════════════════════
MODEL_NAME = "ai4bharat/IndicBART"

print(f"Loading IndicBART model ({MODEL_NAME}) …")
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME, do_lower_case=False, use_fast=False, keep_accents=True
)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).to(device)
model.eval()
print(f"  ✓ IndicBART loaded on {device}.")

DECODER_START_ID = tokenizer.convert_tokens_to_ids("<2en>")


def generate_indian_lay_english(text, model, tokenizer):
    """Generate simplified Indian Lay English using IndicBART.

    Args:
        text: Input text (lay-replaced summary).
        model: IndicBART model (already on device).
        tokenizer: IndicBART tokenizer.

    Returns:
        Simplified text string.  Falls back to input text on failure.
    """
    if not isinstance(text, str) or len(text.strip()) == 0:
        return text
    try:
        input_text = "<s> " + text + " </s> <2en>"
        inputs = tokenizer(
            input_text,
            max_length=512,
            truncation=True,
            padding=True,
            return_tensors="pt",
        ).to(device)

        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_length=300,
                num_beams=4,
                early_stopping=True,
                no_repeat_ngram_size=3,
                decoder_start_token_id=DECODER_START_ID,
            )
        decoded = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return decoded
    except Exception as e:
        print(f"  ⚠ Generation failed: {e}")
        return text


BATCH_SIZE = 10
CHECKPOINT_INTERVAL = 50
total_rows = len(df)

print(f"Generating Indian Lay English for {total_rows} summaries …")
df["indian_lay_english"] = ""

for start in tqdm(range(0, total_rows, BATCH_SIZE), desc="IndicBART"):
    end = min(start + BATCH_SIZE, total_rows)
    for idx in range(start, end):
        text = df.at[idx, "lay_replaced_summary"]
        df.at[idx, "indian_lay_english"] = generate_indian_lay_english(
            text, model, tokenizer
        )

    # Checkpoint every CHECKPOINT_INTERVAL rows
    if (end % CHECKPOINT_INTERVAL == 0) or (end == total_rows):
        df.to_excel(f"checkpoint_{end}.xlsx", index=False)
        print(f"  💾 Checkpoint saved at row {end}")

print("  ✓ IndicBART generation complete.")

# ═══════════════════════════════════════════════════════════════
# STEP 8: EVALUATION
# ═══════════════════════════════════════════════════════════════

def evaluate_summary(original, simplified):
    """Compute readability and compression metrics.

    Args:
        original: Original discharge summary text.
        simplified: Simplified lay-English text.

    Returns:
        Dict with flesch scores, word counts, and compression ratio.
    """
    if not isinstance(original, str) or len(original.strip()) == 0:
        original = ""
    if not isinstance(simplified, str) or len(simplified.strip()) == 0:
        simplified = ""

    flesch_orig = textstat.flesch_reading_ease(original) if original else 0.0
    flesch_simp = textstat.flesch_reading_ease(simplified) if simplified else 0.0
    wc_orig = len(original.split())
    wc_simp = len(simplified.split())
    compression = wc_simp / wc_orig if wc_orig > 0 else 0.0

    return {
        "flesch_original": flesch_orig,
        "flesch_simplified": flesch_simp,
        "flesch_improvement": flesch_simp - flesch_orig,
        "word_count_original": wc_orig,
        "word_count_simplified": wc_simp,
        "compression_ratio": compression,
    }


print("Running evaluation metrics …")
eval_results = []
for idx in tqdm(range(len(df)), desc="Evaluation"):
    original = df.at[idx, "translated discharge_summary"]
    simplified = df.at[idx, "indian_lay_english"]
    eval_results.append(evaluate_summary(original, simplified))

eval_df = pd.DataFrame(eval_results)
for col in eval_df.columns:
    df[col] = eval_df[col].values

print("  ✓ Evaluation complete.")

# Overall averages
avg_flesch_improvement = df["flesch_improvement"].mean()
avg_compression = df["compression_ratio"].mean()
print(f"\n  Avg Flesch improvement : {avg_flesch_improvement:.2f}")
print(f"  Avg compression ratio : {avg_compression:.2f}")

# ═══════════════════════════════════════════════════════════════
# STEP 9: SAVE OUTPUT
# ═══════════════════════════════════════════════════════════════

# Convert medical_entities list-of-dicts to string for Excel compatibility
df["medical_entities"] = df["medical_entities"].apply(str)

OUTPUT_COLUMNS = [
    "translated discharge_summary",
    "expanded_summary",
    "medical_entities",
    "lay_replaced_summary",
    "indian_lay_english",
    "translated diagnosis_ICD",
    "translanted outcome",
    "lenght of stay",
    "medical specialties",
    "flesch_original",
    "flesch_simplified",
    "flesch_improvement",
    "word_count_original",
    "word_count_simplified",
    "compression_ratio",
]

# Keep only columns that actually exist (guard against column-name typos in source)
existing_cols = [c for c in OUTPUT_COLUMNS if c in df.columns]
missing_cols = [c for c in OUTPUT_COLUMNS if c not in df.columns]
if missing_cols:
    print(f"  ⚠ Missing columns (skipped): {missing_cols}")

OUTPUT_PATH = "lay_english_pipeline_output.xlsx"
df[existing_cols].to_excel(OUTPUT_PATH, index=False)
print(f"\n  ✓ Output saved to {OUTPUT_PATH}")

# ═══════════════════════════════════════════════════════════════
# STEP 10: SUMMARY REPORT
# ═══════════════════════════════════════════════════════════════

print("\n" + "=" * 65)
print("                    PIPELINE SUMMARY REPORT")
print("=" * 65)

print(f"  Total summaries processed        : {len(df)}")
print(f"  Avg Flesch (original)            : {df['flesch_original'].mean():.2f}")
print(f"  Avg Flesch (simplified)          : {df['flesch_simplified'].mean():.2f}")
print(f"  Avg Flesch improvement           : {df['flesch_improvement'].mean():.2f}")
print(f"  Avg word count (original)        : {df['word_count_original'].mean():.1f}")
print(f"  Avg word count (simplified)      : {df['word_count_simplified'].mean():.1f}")
print(f"  Avg compression ratio            : {df['compression_ratio'].mean():.3f}")

improved_count = (df["flesch_improvement"] > 0).sum()
print(f"  Summaries with Flesch improvement: {improved_count} / {len(df)}")

# Top 10 most frequent medical entities across all summaries
all_entities = []
for ent_str in df["medical_entities"]:
    try:
        ent_list = eval(ent_str) if isinstance(ent_str, str) else ent_str
        if isinstance(ent_list, list):
            for e in ent_list:
                if isinstance(e, dict) and "entity" in e:
                    all_entities.append(e["entity"].lower())
    except Exception:
        pass

entity_counts = Counter(all_entities)
print("\n  Top 10 most frequent medical entities:")
for term, count in entity_counts.most_common(10):
    print(f"    {term:40s}  —  {count}")

print("\n" + "=" * 65)
print("  Pipeline finished successfully.")
print("=" * 65)

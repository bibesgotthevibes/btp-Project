"""
Medical Discharge Summary → Indian Lay English Pipeline (BioBART version)
========================================================
Platform: Kaggle Notebook (GPU T4 x2 or P100)
"""

# ═══════════════════════════════════════════════════════════════
# STEP 0: LIBRARY INSTALLATION (Kaggle system-wide)
# ═══════════════════════════════════════════════════════════════
# STRATEGY: Do NOT touch system numpy, spacy, or thinc.
#   - Kaggle ships numpy 2.x + spacy 3.9+ compiled together — changing
#     either triggers an ABI mismatch on the other.
#   - scispacy requires spacy<4.0, so Kaggle's spacy 3.9 works.
#   - en_core_sci_md-0.5.4 says spacy<3.6 in its meta, but this is only
#     a warning in spacy 3.x (not an error). We install with --no-deps
#     to skip the version resolver entirely.
import subprocess, sys, os
os.environ["HF_TOKEN"] = "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"

def _pip(*args):
    """Run pip silently."""
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q",
         "--progress-bar", "off", "--no-warn-conflicts", *args],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

print("Step 0: Installing required libraries ...")

# Install these normally — they don't conflict with numpy/spacy
_pip("openpyxl", "textstat", "bert-score", "datasets", "accelerate", "sentencepiece")
print("  [1/3] General packages done.")

# Install scispacy WITHOUT its deps to avoid triggering a numpy downgrade
_pip("--no-deps", "scispacy")
print("  [2/3] scispacy installed (no-deps).")

# Install en_core_sci_md WITHOUT deps to skip the spacy<3.6 version check
_pip("--no-deps",
     "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_md-0.5.4.tar.gz")
print("  [3/3] en_core_sci_md model installed (no-deps).")

print("  \u2713 All libraries installed successfully.")

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

MAIN_DIR = "./BioBART"
MODEL_DIR = os.path.join(MAIN_DIR, "model")
RESULTS_DIR = os.path.join(MAIN_DIR, "results")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# STEP 2: LOAD ALL DATASETS
# ═══════════════════════════════════════════════════════════════

def _locate(pattern):
    """Find a file under /kaggle/input/ or fall back to filename."""
    hits = glob.glob(f"/kaggle/input/**/{pattern}", recursive=True)
    if not hits:
        hits = glob.glob(f"**/{pattern}", recursive=True)
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

# --- 2e. predictions-t5-base.tsv — for benchmarking (optional) ---
try:
    T5_PRED_PATH = _locate("predictions-t5-base.tsv")
    t5_df = pd.read_csv(T5_PRED_PATH, sep="\t")
    print(f"[predictions-t5]    {len(t5_df)} rows | cols: {list(t5_df.columns)}")
except (FileNotFoundError, Exception) as e:
    t5_df = None
    print(f"[predictions-t5]    ⚠ Not found / skipped ({e.__class__.__name__}). Benchmarking disabled.")

# --- 2f. mtsamples.csv — additional medical transcriptions (optional) ---
try:
    MT_PATH = _locate("mtsamples.csv")
    mt_df = pd.read_csv(MT_PATH)
    print(f"[mtsamples.csv]     {len(mt_df)} rows | cols: {list(mt_df.columns)}")
except (FileNotFoundError, Exception) as e:
    mt_df = None
    print(f"[mtsamples.csv]     ⚠ Not found / skipped ({e.__class__.__name__}).")

# --- 2g. PMC-Patients-V2.json (optional, reference only) ---
try:
    PMC_PATH = _locate("PMC-Patients-V2.json")
    print(f"[PMC-Patients]      located: {PMC_PATH}")
except Exception as e:
    print(f"[PMC-Patients]      ⚠ Not found / skipped ({e.__class__.__name__}).")

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
# STEP 7a: FINE-TUNE BioBART ON data.tsv
# ═══════════════════════════════════════════════════════════════
MODEL_NAME = "GanjinZero/biobart-v2-base"
# ── INFORMATION PRESERVATION FIXES ────────────────────────────────────────
#   1. MAX_TGT_LEN=512 — allows full-length output.
#   2. MIN_PRESERVE_RATIO=0.45 — discard training pairs where the simplified
#      text is less than 45% the length of the original (those are summaries).
#   3. Generation uses length_penalty=1.5 + dynamic min_length.
# ──────────────────────────────────────────────────────────────────────────
MIN_PRESERVE_RATIO = 0.45
FINETUNE_ROWS = 10000        # tunable: set higher for better quality
FINETUNE_EPOCHS = 5
FINETUNE_BATCH = 4
FINETUNE_LR = 3e-5
MAX_SRC_LEN = 512
MAX_TGT_LEN = 512
OUTPUT_DIR = MODEL_DIR

print(f"\n{'='*65}")
print("  STEP 7a: Fine-tuning BioBART on medical simplification data")
print(f"{'='*65}")

# Filter rows with both original + simplified text present
ft = finetune_df[["original", "english simplified"]].dropna()
ft = ft[ft["original"].str.strip().astype(bool) & ft["english simplified"].str.strip().astype(bool)]

# ── Information-preservation filter ────────────────────────────────────────
ft["_orig_wc"] = ft["original"].str.split().str.len()
ft["_simp_wc"] = ft["english simplified"].str.split().str.len()
ft["_ratio"]   = ft["_simp_wc"] / ft["_orig_wc"].clip(lower=1)
before_filter  = len(ft)
ft = ft[ft["_ratio"] >= MIN_PRESERVE_RATIO].drop(columns=["_orig_wc", "_simp_wc", "_ratio"])
print(f"  FT data after preservation filter ({MIN_PRESERVE_RATIO}): "
      f"{len(ft)} / {before_filter} pairs kept "
      f"({100*len(ft)/max(before_filter,1):.1f}%)")

ft = ft.head(FINETUNE_ROWS).reset_index(drop=True)
print(f"  Fine-tuning samples (capped): {len(ft)}")

# Load tokenizer + base model
print("  Loading BioBART base model …")
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME, do_lower_case=False, use_fast=False, keep_accents=True
)
base_model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)

# Tokenization for training
def preprocess_for_training(examples):
    """Tokenize src (original) → tgt (simplified) for Seq2Seq training."""
    sources = examples["original"]
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
# transformers ≥4.46 renamed 'tokenizer' → 'processing_class';
# fall back to 'tokenizer' for older installs.
import inspect as _inspect
_trainer_params = set(_inspect.signature(Seq2SeqTrainer.__init__).parameters)
_tok_kwarg = "processing_class" if "processing_class" in _trainer_params else "tokenizer"
trainer = Seq2SeqTrainer(
    model=base_model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=eval_ds,
    **{_tok_kwarg: tokenizer},
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
print("  STEP 7b: Generating Lay English (fine-tuned BioBART)")
print(f"{'='*65}")

model = AutoModelForSeq2SeqLM.from_pretrained(OUTPUT_DIR).to(device)
model.eval()

def _generate_chunk(chunk_ids, model, tokenizer, device):
    """
    Run the encoder-decoder model on a single pre-tokenised chunk.
    Returns the decoded string for that chunk.
    """
    inp = chunk_ids.unsqueeze(0).to(device)               # (1, seq_len)
    attn = torch.ones_like(inp)
    n_tokens = inp.shape[-1]
    dyn_min  = max(20, int(n_tokens * 0.55))

    with torch.no_grad():
        out_ids = model.generate(
            input_ids=inp,
            attention_mask=attn,
            max_new_tokens=min(n_tokens, MAX_TGT_LEN),
            min_length=dyn_min,
            num_beams=4,
            length_penalty=1.5,
            early_stopping=False,
            no_repeat_ngram_size=4,
        )
    return tokenizer.decode(out_ids[0], skip_special_tokens=True).strip()


def generate_indian_lay_english(text, model, tokenizer):
    """
    Generate simplified lay English using fine-tuned BioBART.
    Uses chunked generation for long documents.
    """
    if not isinstance(text, str) or len(text.strip()) == 0:
        return text if isinstance(text, str) else ""

    CHUNK_TOKENS  = 450
    CHUNK_OVERLAP = 50

    try:
        full_ids = tokenizer(
            text,
            add_special_tokens=False,
            return_tensors="pt",
        )["input_ids"][0]

        eos_id  = tokenizer.eos_token_id
        total   = full_ids.shape[0]

        chunk_outputs = []
        start = 0
        while start < total:
            end        = min(start + CHUNK_TOKENS, total)
            chunk_body = full_ids[start:end]

            chunk_with_eos = torch.cat([
                chunk_body,
                torch.tensor([eos_id]),
            ])

            passage = _generate_chunk(chunk_with_eos, model, tokenizer, device)
            if passage:
                chunk_outputs.append(passage)

            if end >= total:
                break
            start = end - CHUNK_OVERLAP

        return " ".join(chunk_outputs)

    except Exception as e:
        print(f"  ⚠ Generation failed: {e}")
        return text

BATCH_SIZE = 10
total_rows = len(df)

df["indian_lay_english"] = ""
for start in tqdm(range(0, total_rows, BATCH_SIZE), desc="Generating"):
    end = min(start + BATCH_SIZE, total_rows)
    for idx in range(start, end):
        df.at[idx, "indian_lay_english"] = generate_indian_lay_english(
            df.at[idx, "lay_replaced_summary"], model, tokenizer
        )

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

OUTPUT_PATH = os.path.join(RESULTS_DIR, "biobart_pipeline_output.xlsx")
df[existing_cols].to_excel(OUTPUT_PATH, index=False)
print(f"\n  ✓ Output saved to {OUTPUT_PATH}")

# ═══════════════════════════════════════════════════════════════
# STEP 10: SUMMARY REPORT & ANALYSIS
# ═══════════════════════════════════════════════════════════════
improved_count = (df["flesch_improvement"] > 0).sum()

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
top_entities = "\n".join([f"    {term:40s}  —  {count}" for term, count in entity_counts.most_common(10)])

report = f"""
=================================================================
                    PIPELINE SUMMARY REPORT
=================================================================
  Model used                       : {MODEL_NAME}
  Total summaries processed        : {len(df)}
  Fine-tuning samples used         : {len(ft)}

  [READABILITY & COMPRESSION SCORES]
  Avg Flesch (original)            : {df['flesch_original'].mean():.2f}
  Avg Flesch (simplified)          : {df['flesch_simplified'].mean():.2f}
  Avg Flesch improvement           : {df['flesch_improvement'].mean():.2f}
  Summaries with Flesch improvement: {improved_count} / {len(df)}

  Avg word count (original)        : {df['word_count_original'].mean():.1f}
  Avg word count (simplified)      : {df['word_count_simplified'].mean():.1f}
  Avg compression ratio            : {df['compression_ratio'].mean():.3f}

  [TOP MEDICAL ENTITIES]
{top_entities}
=================================================================
  Pipeline finished successfully.
=================================================================
"""

print(report)

ANALYSIS_PATH = os.path.join(RESULTS_DIR, "analysis.txt")
with open(ANALYSIS_PATH, "w", encoding="utf-8") as f:
    f.write(report)
print(f"  ✓ Detailed analysis saved to {ANALYSIS_PATH}")

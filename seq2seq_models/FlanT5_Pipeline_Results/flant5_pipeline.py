"""
Medical Discharge Summary → Indian Lay English Pipeline (FLAN-T5 version)
==========================================================================
Platform: Kaggle Notebook (GPU T4 x2)
Model   : google/flan-t5-base (~248M params)
          Google's instruction-tuned T5-base. Reliable task-following,
          standard BPE tokenizer — no SentencePiece word-boundary stitching bug.

KEY FACTS ABOUT FLAN-T5-base:
  • Architecture  : T5-base (12 enc + 12 dec layers, d_model=768)
  • Pre-training  : Instruction-finetuned on 1,800+ NLP tasks (FLAN collection)
  • Tokenizer     : T5Tokenizer (SentencePiece) — but used CORRECTLY here
                    via single tokenizer() calls (avoids the 'sssss' boundary bug)
  • save_strategy : "no" → only the final model is saved; no epoch checkpoints
"""

# ═══════════════════════════════════════════════════════════════
# STEP 0: ENVIRONMENT + LIBRARY INSTALLATION
# ═══════════════════════════════════════════════════════════════
import subprocess, sys, os

os.environ["HF_TOKEN"] = "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"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"


def _pip(*args):
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q",
         "--progress-bar", "off", "--no-warn-conflicts", *args],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


print("Step 0: Installing required libraries ...")
_pip("openpyxl", "textstat", "datasets", "accelerate", "sentencepiece", "protobuf")
print("  [1/3] General packages done.")

_pip("--no-deps", "scispacy")
print("  [2/3] scispacy installed (no-deps).")

_pip("--no-deps",
     "https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_md-0.5.4.tar.gz")
print("  [3/3] en_core_sci_md model installed (no-deps).")
print("  ✓ All libraries installed successfully.")

# ═══════════════════════════════════════════════════════════════
# STEP 1: IMPORTS
# ═══════════════════════════════════════════════════════════════
import re, gc, glob, inspect, warnings
import pandas as pd
import numpy as np
import spacy
import textstat
import torch
from tqdm import tqdm
from collections import Counter
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    DataCollatorForSeq2Seq,
)
from datasets import Dataset

warnings.filterwarnings("ignore")

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

MAIN_DIR    = "./FlanT5"
MODEL_DIR   = os.path.join(MAIN_DIR, "model")
RESULTS_DIR = os.path.join(MAIN_DIR, "results")
os.makedirs(MODEL_DIR,   exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# STEP 2: LOAD ALL DATASETS
# ═══════════════════════════════════════════════════════════════

def _locate(pattern):
    hits = glob.glob(f"/kaggle/input/**/{pattern}", recursive=True)
    if not hits:
        hits = glob.glob(f"**/{pattern}", recursive=True)
    return hits[0] if hits else pattern


ANNOTATED_PATH = _locate("anotated_dataset_v2.xlsx")
df = pd.read_excel(ANNOTATED_PATH, sheet_name="annotated_dataset")
print(f"[annotated_dataset] {len(df)} rows | cols: {list(df.columns)}")

abbr_df = pd.read_excel(ANNOTATED_PATH, sheet_name="abbreviations")
abbr_dict = dict(zip(
    abbr_df["abbreviated word"].astype(str).str.lower().str.strip(),
    abbr_df["translated"].astype(str).str.strip(),
))
print(f"[abbreviations]     {len(abbr_dict)} entries")

def _find_col(frame, *candidates):
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
    icd_df[_v].astype(str).str.strip(),
)) if _k and _v else {}
print(f"[ICD Codes]         {len(icd_dict)} entries  (key='{_k}', val='{_v}')")

DATA_TSV_PATH = _locate("data.tsv")
finetune_df = pd.read_csv(DATA_TSV_PATH, sep="\t", low_memory=False)
print(f"[data.tsv]          {len(finetune_df)} rows | cols: {list(finetune_df.columns)}")

try:
    t5_df = pd.read_csv(_locate("predictions-t5-base.tsv"), sep="\t")
    print(f"[predictions-t5]    {len(t5_df)} rows")
except Exception as e:
    t5_df = None
    print(f"[predictions-t5]    ⚠ Not found / skipped ({e.__class__.__name__}).")

try:
    mt_df = pd.read_csv(_locate("mtsamples.csv"))
    print(f"[mtsamples.csv]     {len(mt_df)} rows")
except Exception as e:
    mt_df = None
    print(f"[mtsamples.csv]     ⚠ Not found / skipped ({e.__class__.__name__}).")

try:
    PMC_PATH = _locate("PMC-Patients-V2.json")
    print(f"[PMC-Patients]      located: {PMC_PATH}")
except Exception as e:
    print(f"[PMC-Patients]      ⚠ Not found / skipped ({e.__class__.__name__}).")

# ═══════════════════════════════════════════════════════════════
# STEP 3: TEXT PREPROCESSING
# ═══════════════════════════════════════════════════════════════

def preprocess_text(text):
    if not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", text.lower()).strip()


# ═══════════════════════════════════════════════════════════════
# STEP 4: ABBREVIATION EXPANSION
# ═══════════════════════════════════════════════════════════════

def expand_abbreviations(text, abbr_dict):
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
df["preprocessed"]    = df["translated discharge_summary"].apply(preprocess_text)
df["expanded_summary"] = df["preprocessed"].apply(lambda t: expand_abbreviations(t, abbr_dict))
print("  ✓ Abbreviation expansion complete.")

# ═══════════════════════════════════════════════════════════════
# STEP 5: MEDICAL NER USING scispaCy
# ═══════════════════════════════════════════════════════════════
print("\nLoading scispaCy en_core_sci_md …")
nlp = spacy.load("en_core_sci_md")
print("  ✓ scispaCy model loaded.")


def extract_medical_entities(text):
    if not isinstance(text, str) or len(text.strip()) == 0:
        return []
    doc = nlp(text)
    return [{"entity": e.text, "label": e.label_,
              "start": e.start_char, "end": e.end_char} for e in doc.ents]


print("Extracting medical entities …")
tqdm.pandas(desc="NER")
df["medical_entities"] = df["expanded_summary"].progress_apply(extract_medical_entities)
print("  ✓ Medical entity extraction complete.")

# ═══════════════════════════════════════════════════════════════
# STEP 6: LAY DICTIONARY REPLACEMENT
# ═══════════════════════════════════════════════════════════════

INDIAN_LAY_DICT = {
    "hypertension": "high BP", "diabetes mellitus": "sugar disease (diabetes)",
    "myocardial infarction": "heart attack", "acute renal failure": "sudden kidney failure",
    "chronic renal failure": "long-term kidney problem",
    "septicemia": "blood infection (sepsis)", "sepsis": "serious blood infection",
    "pneumonia": "lung infection", "tuberculosis": "TB (tuberculosis)",
    "pneumothorax": "air trapped in chest", "endocarditis": "infection of heart valves",
    "spondylodiscitis": "spine bone infection", "hypotension": "low BP",
    "pyrexia": "fever", "dyspnea": "difficulty in breathing",
    "edema": "swelling", "abscess": "pus-filled swelling",
    "renal failure": "kidney failure", "cerebrovascular accident": "brain stroke",
    "anemia": "low blood (anemia)", "tachycardia": "fast heartbeat",
    "bradycardia": "slow heartbeat", "atrial fibrillation": "irregular heartbeat",
    "hemodialysis": "kidney dialysis", "tracheostomy": "breathing tube in neck",
    "thoracotomy": "chest surgery", "pneumonectomy": "removal of a lung",
    "debridement": "surgical wound cleaning",
    "intravenous": "given through a vein (drip)",
    "intramuscular": "given as a muscle injection",
    "antibiotic": "infection-fighting medicine",
    "blood culture": "blood test to find infection",
    "hemoglobin": "blood count (Hb)", "creatinine": "kidney function marker",
    "bilirubin": "liver function marker", "saturation": "oxygen level in blood",
    "afebrile": "no fever", "eupneic": "breathing normally",
    "discharge": "sent home from hospital",
    "intensive care unit": "ICU (serious care room)",
    "outpatient clinic": "OPD (Out Patient Department)",
    "follow-up": "return visit to doctor",
}


def apply_lay_dictionary(text, lay_dict):
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
# STEP 7a: FINE-TUNE FLAN-T5-base ON data.tsv
# ═══════════════════════════════════════════════════════════════
# FLAN-T5-base key facts:
#   • HuggingFace ID : "google/flan-t5-base"  (~248M params)
#   • Architecture   : T5-base (encoder-decoder)
#   • Tokenizer      : T5Tokenizer (SentencePiece)
#   • Unlike ClinicalT5, the chunking uses TEXT-LEVEL approach:
#     each window is decoded back to string, then re-tokenized as
#     "TASK_PREFIX + chunk_text" in ONE clean tokenizer() call.
#     This avoids the ▁ word-boundary corruption that caused 'sssss' output.
#   • save_strategy="no" → CRITICAL for Kaggle disk quota.
# ──────────────────────────────────────────────────────────────
MODEL_NAME         = "google/flan-t5-base"
# FLAN-T5 is instruction-tuned, so a descriptive instruction works best
TASK_PREFIX        = "Simplify the following medical discharge summary into plain English that a patient's family can understand, preserving every clinical detail, medication, and event: "
MIN_PRESERVE_RATIO = 0.45
FINETUNE_ROWS      = 10000
FINETUNE_EPOCHS    = 5
FINETUNE_BATCH     = 2
GRAD_ACCUM         = 2          # effective batch = 4
FINETUNE_LR        = 3e-4
MAX_SRC_LEN        = 512
MAX_TGT_LEN        = 512
OUTPUT_DIR         = MODEL_DIR

print(f"\n{'='*65}")
print("  STEP 7a: Fine-tuning FLAN-T5-base on medical simplification data")
print(f"{'='*65}")

ft = finetune_df[["original", "english simplified"]].dropna()
ft = ft[ft["original"].str.strip().astype(bool) & ft["english simplified"].str.strip().astype(bool)]

# ── Information-preservation filter ─────────────────────────────────────────
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
print("  Loading FLAN-T5-base model …")
tokenizer  = AutoTokenizer.from_pretrained(MODEL_NAME)
base_model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
base_model.gradient_checkpointing_enable()
print(f"  ✓ Model loaded  (vocab size: {tokenizer.vocab_size:,})")


def preprocess_for_training(examples):
    """Tokenize src→tgt pairs with the task prefix prepended to every source."""
    sources = [TASK_PREFIX + s for s in examples["original"]]
    targets = examples["english simplified"]
    model_inputs = tokenizer(
        sources, max_length=MAX_SRC_LEN, truncation=True, padding="max_length"
    )
    labels = tokenizer(
        text_target=targets, max_length=MAX_TGT_LEN, truncation=True, padding="max_length"
    )
    labels["input_ids"] = [
        [(t if t != tokenizer.pad_token_id else -100) for t in label]
        for label in labels["input_ids"]
    ]
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs


hf_dataset = Dataset.from_pandas(ft)
split    = hf_dataset.train_test_split(test_size=0.1, seed=42)
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
    gradient_accumulation_steps=GRAD_ACCUM,
    learning_rate=FINETUNE_LR,
    weight_decay=0.01,
    warmup_steps=200,
    eval_strategy="epoch",
    save_strategy="no",               # no intermediate checkpoints
    predict_with_generate=True,
    fp16=(device == "cuda"),
    logging_steps=100,
    report_to="none",
    load_best_model_at_end=False,
    generation_max_length=MAX_TGT_LEN,
    dataloader_pin_memory=False,
)

data_collator = DataCollatorForSeq2Seq(tokenizer, model=base_model, padding=True)

_trainer_params = set(inspect.signature(Seq2SeqTrainer.__init__).parameters)
_tok_kwarg = "processing_class" if "processing_class" in _trainer_params else "tokenizer"

print(f"  Training: {FINETUNE_EPOCHS} epochs, batch={FINETUNE_BATCH}×{GRAD_ACCUM} (grad accum), lr={FINETUNE_LR}")
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
print("  STEP 7b: Generating Lay English (fine-tuned FLAN-T5-base)")
print(f"{'='*65}")

model = AutoModelForSeq2SeqLM.from_pretrained(OUTPUT_DIR).to(device)
model.config.use_cache = True
model.eval()


def _generate_chunk(chunk_text: str, model, tokenizer, device) -> str:
    """
    Tokenize and generate for ONE chunk of plain text.

    CRITICAL DESIGN DECISION — single tokenizer() call per chunk:
    ─────────────────────────────────────────────────────────────
    SentencePiece adds ▁ (U+2581) word-boundary markers ONLY at the
    very start of a tokenizer() call. If you manually stitch together
    token ID tensors from two separate calls (prefix_ids + chunk_ids),
    the boundary between them loses its ▁ marker. The model then sees
    a malformed sub-word sequence and degenerates to repeating a single
    token (e.g. "s s s s s" — the exact bug seen with ClinicalT5).

    Solution: decode each chunk window back to text, then re-tokenize
    the complete "TASK_PREFIX + chunk_text" string in ONE call.
    """
    prefixed = TASK_PREFIX + chunk_text
    enc = tokenizer(
        prefixed,
        max_length=MAX_SRC_LEN,
        truncation=True,
        return_tensors="pt",
    ).to(device)
    n_tokens = enc["input_ids"].shape[-1]
    dyn_min  = max(20, int(n_tokens * 0.55))

    with torch.no_grad():
        out_ids = model.generate(
            **enc,
            max_new_tokens=min(n_tokens + 100, MAX_TGT_LEN),
            min_length=dyn_min,
            num_beams=4,
            length_penalty=1.5,
            early_stopping=False,
            no_repeat_ngram_size=4,
        )
    return tokenizer.decode(out_ids[0], skip_special_tokens=True).strip()


def generate_lay_english(text: str, model, tokenizer) -> str:
    """
    Generate simplified lay English from a (potentially long) discharge summary.

    LONG-DOCUMENT HANDLING — TEXT-LEVEL CHUNKING:
    ─────────────────────────────────────────────
    FLAN-T5-base has a 512-token encoder limit. Long discharge summaries are
    split into 450-token overlapping windows. Each window is decoded back to
    text, then passed to _generate_chunk() which re-tokenizes it properly.

    Overlap (50 tokens) prevents hard sentence cuts at window boundaries.
    Short documents produce a single chunk with no change in behaviour.
    """
    if not isinstance(text, str) or not text.strip():
        return text if isinstance(text, str) else ""

    CHUNK_TOKENS  = 450
    CHUNK_OVERLAP = 50

    try:
        # Tokenise the FULL text to get boundary positions.
        # We explicitly pass truncation=True and max_length=100000 to suppress the HuggingFace
        # "Token indices sequence length is longer than the specified maximum" warning, 
        # since we intentionally want the full length to manually chunk it.
        full_ids = tokenizer(
            text, add_special_tokens=False, return_tensors="pt",
            truncation=True, max_length=100000
        )["input_ids"][0]

        total = full_ids.shape[0]
        chunk_outputs = []
        start = 0

        while start < total:
            end        = min(start + CHUNK_TOKENS, total)
            chunk_body = full_ids[start:end]

            # ── KEY: decode back to text, then re-tokenize with prefix ──────
            chunk_text = tokenizer.decode(chunk_body, skip_special_tokens=True)
            passage    = _generate_chunk(chunk_text, model, tokenizer, device)
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

df["lay_english_flant5"] = ""
for start in tqdm(range(0, total_rows, BATCH_SIZE), desc="Generating"):
    end = min(start + BATCH_SIZE, total_rows)
    for idx in range(start, end):
        df.at[idx, "lay_english_flant5"] = generate_lay_english(
            df.at[idx, "lay_replaced_summary"], model, tokenizer
        )

print("  ✓ Generation complete.")

# ═══════════════════════════════════════════════════════════════
# STEP 8: EVALUATION
# ═══════════════════════════════════════════════════════════════

def evaluate_summary(original, simplified):
    if not isinstance(original, str) or not original.strip():
        original = ""
    if not isinstance(simplified, str) or not simplified.strip():
        simplified = ""
    flesch_orig = textstat.flesch_reading_ease(original) if original else 0.0
    flesch_simp = textstat.flesch_reading_ease(simplified) if simplified else 0.0
    wc_orig = len(original.split())
    wc_simp = len(simplified.split())
    return {
        "flesch_original":    flesch_orig,
        "flesch_simplified":  flesch_simp,
        "flesch_improvement": flesch_simp - flesch_orig,
        "word_count_original":   wc_orig,
        "word_count_simplified": wc_simp,
        "compression_ratio": wc_simp / wc_orig if wc_orig > 0 else 0.0,
    }


print("\nRunning evaluation …")
eval_results = [
    evaluate_summary(df.at[i, "translated discharge_summary"], df.at[i, "lay_english_flant5"])
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
    "lay_replaced_summary", "lay_english_flant5",
    "translated diagnosis_ICD", "translanted outcome",
    "lenght of stay", "medical specialties",
    "flesch_original", "flesch_simplified", "flesch_improvement",
    "word_count_original", "word_count_simplified", "compression_ratio",
]
existing_cols = [c for c in OUTPUT_COLUMNS if c in df.columns]
missing_cols  = [c for c in OUTPUT_COLUMNS if c not in df.columns]
if missing_cols:
    print(f"  ⚠ Missing columns (skipped): {missing_cols}")

OUTPUT_PATH = os.path.join(RESULTS_DIR, "flant5_pipeline_output.xlsx")
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
top_entities  = "\n".join([f"    {term:40s}  —  {count}"
                            for term, count in entity_counts.most_common(10)])

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

"""
Medical Discharge Summary → Indian Lay English Pipeline (BioGPT version)
=========================================================================
Platform: Kaggle Notebook (GPU T4 x2)
Model   : microsoft/biogpt (~347M params)
          Decoder-only GPT trained on PubMed biomedical literature.

KEY DIFFERENCE vs PEGASUS/BART pipelines:
  BioGPT is a CAUSAL (decoder-only) LM, not an encoder-decoder.
  Fine-tuning uses prompt-completion format:
    "Simplify: {original}\n### Simplified: {simplified}<|endoftext|>"
  Loss is computed ONLY on the completion part (prompt tokens → -100).
  Generation: feed the prompt prefix, model auto-completes the simplified text.
"""

# ═══════════════════════════════════════════════════════════════
# STEP 0: ENVIRONMENT + LIBRARY INSTALLATION
# ═══════════════════════════════════════════════════════════════
import subprocess, sys, os

# add your hugging face token here
os.environ["HF_TOKEN"] = ""

# Single-GPU: prevents DataParallel gradient-reduction OOM on Kaggle T4×2
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
# Expandable segments: avoids fragmentation-induced OOM on small allocations
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"


def _pip(*args):
    """Run pip silently."""
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q",
         "--progress-bar", "off", "--no-warn-conflicts", *args],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


print("Step 0: Installing required libraries ...")
_pip("openpyxl", "textstat", "datasets", "accelerate", "sentencepiece", "sacremoses")
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
import re, gc, glob, warnings
import pandas as pd
import numpy as np
import spacy
import textstat
import torch
from tqdm import tqdm
from collections import Counter
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    Trainer,
    TrainingArguments,
    default_data_collator,
)
from datasets import Dataset

warnings.filterwarnings("ignore")

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

MAIN_DIR = "./BioGPT"
MODEL_DIR = os.path.join(MAIN_DIR, "model")
RESULTS_DIR = os.path.join(MAIN_DIR, "results")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# STEP 2: LOAD ALL DATASETS
# ═══════════════════════════════════════════════════════════════

def _locate(pattern):
    hits = glob.glob(f"/kaggle/input/**/{pattern}", recursive=True)
    if not hits:
        hits = glob.glob(f"**/{pattern}", recursive=True)
    return hits[0] if hits else pattern


# 2a. Annotated discharge summaries
ANNOTATED_PATH = _locate("anotated_dataset_v2.xlsx")
df = pd.read_excel(ANNOTATED_PATH, sheet_name="annotated_dataset")
print(f"[annotated_dataset] {len(df)} rows | cols: {list(df.columns)}")

# 2b. Abbreviations dictionary
abbr_df = pd.read_excel(ANNOTATED_PATH, sheet_name="abbreviations")
abbr_dict = dict(zip(
    abbr_df["abbreviated word"].astype(str).str.lower().str.strip(),
    abbr_df["translated"].astype(str).str.strip(),
))
print(f"[abbreviations]     {len(abbr_dict)} entries")

# 2c. ICD Codes dictionary
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

# 2d. data.tsv — fine-tuning pairs
DATA_TSV_PATH = _locate("data.tsv")
finetune_df = pd.read_csv(DATA_TSV_PATH, sep="\t", low_memory=False)
print(f"[data.tsv]          {len(finetune_df)} rows | cols: {list(finetune_df.columns)}")

# 2e. predictions-t5 (optional benchmarking)
try:
    t5_df = pd.read_csv(_locate("predictions-t5-base.tsv"), sep="\t")
    print(f"[predictions-t5]    {len(t5_df)} rows")
except Exception as e:
    t5_df = None
    print(f"[predictions-t5]    ⚠ Not found / skipped ({e.__class__.__name__}).")

# 2f. mtsamples (optional)
try:
    mt_df = pd.read_csv(_locate("mtsamples.csv"))
    print(f"[mtsamples.csv]     {len(mt_df)} rows")
except Exception as e:
    mt_df = None
    print(f"[mtsamples.csv]     ⚠ Not found / skipped ({e.__class__.__name__}).")

# 2g. PMC-Patients (optional)
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
# STEP 7a: FINE-TUNE BioGPT ON data.tsv
# ═══════════════════════════════════════════════════════════════
# BioGPT is a DECODER-ONLY (causal LM) model — fundamentally different from
# PEGASUS / BioBART which are encoder-decoder models.
#
# Training strategy — prompt-completion format:
#   Full text  = PROMPT + COMPLETION
#   PROMPT     = "Simplify: {original}\n### Simplified: "
#   COMPLETION = "{simplified}<|endoftext|>"
#   Loss mask  = -100 for every prompt token  (only learn to produce completion)
#
# Generation strategy:
#   Feed PROMPT, call model.generate(), decode only the NEW tokens.
# ──────────────────────────────────────────────────────────────
MODEL_NAME      = "microsoft/biogpt"
# ── INFORMATION PRESERVATION FIXES ────────────────────────────────────────
# Root cause of summarisation: (a) hard token limits cut off text
# (b) length_penalty<1 actively penalised longer outputs;
# (c) training pairs where simplified << original taught the model to condense.
#
# Fixes applied:
#   1. MAX_NEW_TOKENS=450 — matches chunk size for full-length output.
#   2. MIN_PRESERVE_RATIO=0.45 — discard training pairs where the simplified
#      text is less than 45% the length of the original (those are summaries).
#   3. Task prefix updated to explicitly state the intent.
#   4. Generation uses length_penalty=1.5 + dynamic min_new_tokens.
# ──────────────────────────────────────────────────────────────────────────
MIN_PRESERVE_RATIO = 0.45
FINETUNE_ROWS   = 10000
FINETUNE_EPOCHS = 5
FINETUNE_BATCH  = 4          # BioGPT (~347M) is lighter than PEGASUS; batch=4 fits T4
GRAD_ACCUM      = 1          # effective batch = 4
FINETUNE_LR     = 3e-5
MAX_SRC_LEN     = 450        # max tokens for the source portion of the prompt
MAX_NEW_TOKENS  = 450        # max tokens the model generates (completion only)
MAX_SEQ_LEN     = min(1024, MAX_SRC_LEN + MAX_NEW_TOKENS + 50)   # total sequence length for training
OUTPUT_DIR      = MODEL_DIR

# Prompt template — keep it short so more of the 1024-token window is for content
PROMPT_PREFIX = "lay simplify preserving all details: "
PROMPT_SUFFIX = "\n### Simplified: "

print(f"\n{'='*65}")
print("  STEP 7a: Fine-tuning BioGPT on medical simplification data")
print(f"{'='*65}")

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

# Load tokenizer + model
print("  Loading BioGPT model …")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

# BioGPT (like all GPT models) has no pad token by default
# Set pad_token = eos_token, and pad on the RIGHT for causal LM
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

base_model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
base_model.config.pad_token_id = tokenizer.eos_token_id
print(f"  ✓ Model loaded  (vocab size: {tokenizer.vocab_size:,})")


def preprocess_for_training(examples):
    """
    Build full token sequences for causal LM training.

    For each pair (original, simplified):
      1. Encode PROMPT  = "Simplify: {original}\n### Simplified: "
      2. Encode COMPLETION = "{simplified}<|endoftext|>"
      3. Concatenate → input_ids  (truncated to MAX_SEQ_LEN)
      4. labels = copy of input_ids, but PROMPT tokens → -100
         (so loss is computed only on the completion part)
    """
    all_input_ids = []
    all_labels    = []
    all_attn_mask = []

    for src, tgt in zip(examples["original"], examples["english simplified"]):
        # Build the two parts as strings
        prompt     = PROMPT_PREFIX + str(src) + PROMPT_SUFFIX
        completion = str(tgt) + tokenizer.eos_token

        # Tokenize separately (no padding yet) to know prompt length
        prompt_ids     = tokenizer.encode(prompt,     add_special_tokens=False)
        completion_ids = tokenizer.encode(completion, add_special_tokens=False)

        # Truncate source so that prompt + completion <= MAX_SEQ_LEN
        # Reserve enough room for the completion + suffix tokens
        max_prompt_len = MAX_SEQ_LEN - len(completion_ids)
        if max_prompt_len < 10:          # pathological: completion alone too long
            completion_ids = completion_ids[:MAX_SEQ_LEN - 10]
            max_prompt_len = 10
        prompt_ids = prompt_ids[-max_prompt_len:]  # keep the END of a long prompt

        input_ids = prompt_ids + completion_ids
        # Pad to MAX_SEQ_LEN
        pad_len = MAX_SEQ_LEN - len(input_ids)
        attn_mask = [1] * len(input_ids) + [0] * pad_len
        input_ids = input_ids + [tokenizer.pad_token_id] * pad_len

        # Labels: -100 for prompt tokens and padding, actual ids for completion
        labels = (
            [-100] * len(prompt_ids)        # mask the prompt
            + completion_ids                # learn this
            + [-100] * pad_len              # mask the padding
        )

        all_input_ids.append(input_ids)
        all_labels.append(labels)
        all_attn_mask.append(attn_mask)

    return {
        "input_ids":      all_input_ids,
        "attention_mask": all_attn_mask,
        "labels":         all_labels,
    }


hf_dataset = Dataset.from_pandas(ft)
split    = hf_dataset.train_test_split(test_size=0.1, seed=42)
train_ds = split["train"].map(preprocess_for_training, batched=True,
                               remove_columns=["original", "english simplified"])
eval_ds  = split["test"].map(preprocess_for_training, batched=True,
                               remove_columns=["original", "english simplified"])
train_ds.set_format("torch")
eval_ds.set_format("torch")
print(f"  Train: {len(train_ds)}  |  Eval: {len(eval_ds)}")

# Clear cache before building trainer
gc.collect()
torch.cuda.empty_cache()

# Gradient checkpointing — trades speed for VRAM
base_model.gradient_checkpointing_enable()
base_model.config.use_cache = False    # incompatible with grad checkpointing

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=FINETUNE_EPOCHS,
    per_device_train_batch_size=FINETUNE_BATCH,
    per_device_eval_batch_size=FINETUNE_BATCH,
    gradient_accumulation_steps=GRAD_ACCUM,
    learning_rate=FINETUNE_LR,
    weight_decay=0.01,
    warmup_steps=200,
    eval_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=2,
    fp16=(device == "cuda"),
    logging_steps=100,
    report_to="none",
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    dataloader_pin_memory=False,
)

# default_data_collator simply stacks pre-tokenized tensors — no label tampering
trainer = Trainer(
    model=base_model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=eval_ds,
    data_collator=default_data_collator,
)

print(f"  Training: {FINETUNE_EPOCHS} epochs, batch={FINETUNE_BATCH}×{GRAD_ACCUM} (grad accum), lr={FINETUNE_LR}")
trainer.train()
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"  ✓ Fine-tuned model saved to {OUTPUT_DIR}")

# ═══════════════════════════════════════════════════════════════
# STEP 7b: GENERATE LAY ENGLISH WITH FINE-TUNED MODEL
# ═══════════════════════════════════════════════════════════════
print(f"\n{'='*65}")
print("  STEP 7b: Generating Lay English (fine-tuned BioGPT)")
print(f"{'='*65}")

# Re-enable cache for fast inference
model = AutoModelForCausalLM.from_pretrained(OUTPUT_DIR).to(device)
model.config.use_cache = True
model.eval()


def _generate_chunk(chunk_ids, model, tokenizer, device):
    """
    Run the causal LM on a single pre-tokenised chunk.
    BioGPT is a decoder-only model, so we pass the chunk + prompt string,
    generate the completion, and return only the newly generated tokens.
    """
    inp = chunk_ids.unsqueeze(0).to(device)               # (1, seq_len)
    attn = torch.ones_like(inp)
    
    prompt_len = inp.shape[-1]
    # For a causal LM, we use min_new_tokens to force the generator to
    # produce a minimum number of output tokens regardless of input length.
    dyn_min_new = max(20, int((prompt_len - 15) * 0.55))

    with torch.no_grad():
        out_ids = model.generate(
            input_ids=inp,
            attention_mask=attn,
            max_new_tokens=min(prompt_len, MAX_NEW_TOKENS),
            min_new_tokens=dyn_min_new,
            num_beams=4,
            length_penalty=1.5,
            early_stopping=False,
            no_repeat_ngram_size=4,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    
    # Decode ONLY the newly generated tokens (skip the prompt prefix)
    new_tokens = out_ids[0][prompt_len:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def generate_lay_english(text, model, tokenizer):
    """
    Generate simplified lay English using fine-tuned BioGPT.

    LONG-DOCUMENT HANDLING (chunked generation)
    ═══════════════════════════════════════════
    BioGPT has a 1024 token limit. Chunking splits the text into
    overlapping windows, processes each by prepending the prompt
    instruction, generating the continuation, and joining the results.
    """
    if not isinstance(text, str) or len(text.strip()) == 0:
        return text if isinstance(text, str) else ""

    CHUNK_TOKENS  = 400
    CHUNK_OVERLAP = 50

    try:
        # Tokenize without the prompt suffix/prefix first
        full_ids = tokenizer(
            text,
            add_special_tokens=False,
            return_tensors="pt",
        )["input_ids"][0]

        prefix_ids = tokenizer(PROMPT_PREFIX, add_special_tokens=False, return_tensors="pt")["input_ids"][0]
        suffix_ids = tokenizer(PROMPT_SUFFIX, add_special_tokens=False, return_tensors="pt")["input_ids"][0]
        total = full_ids.shape[0]

        chunk_outputs = []
        start = 0
        while start < total:
            end = min(start + CHUNK_TOKENS, total)
            chunk_body = full_ids[start:end]

            chunk_with_prompt = torch.cat([prefix_ids, chunk_body, suffix_ids])

            passage = _generate_chunk(chunk_with_prompt, model, tokenizer, device)
            if passage:
                chunk_outputs.append(passage)

            if end >= total:
                break
            start = end - CHUNK_OVERLAP

        return " ".join(chunk_outputs)

    except Exception as e:
        print(f"  ⚠ Generation failed: {e}")
        return text


BATCH_SIZE          = 10
total_rows          = len(df)

df["lay_english_biogpt"] = ""
for start in tqdm(range(0, total_rows, BATCH_SIZE), desc="Generating"):
    end = min(start + BATCH_SIZE, total_rows)
    for idx in range(start, end):
        df.at[idx, "lay_english_biogpt"] = generate_lay_english(
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
        "flesch_original":    flesch_orig,
        "flesch_simplified":  flesch_simp,
        "flesch_improvement": flesch_simp - flesch_orig,
        "word_count_original":    wc_orig,
        "word_count_simplified":  wc_simp,
        "compression_ratio":  wc_simp / wc_orig if wc_orig > 0 else 0.0,
    }


print("\nRunning evaluation …")
eval_results = [
    evaluate_summary(df.at[i, "translated discharge_summary"], df.at[i, "lay_english_biogpt"])
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
    "lay_replaced_summary", "lay_english_biogpt",
    "translated diagnosis_ICD", "translanted outcome",
    "lenght of stay", "medical specialties",
    "flesch_original", "flesch_simplified", "flesch_improvement",
    "word_count_original", "word_count_simplified", "compression_ratio",
]
existing_cols = [c for c in OUTPUT_COLUMNS if c in df.columns]
missing_cols  = [c for c in OUTPUT_COLUMNS if c not in df.columns]
if missing_cols:
    print(f"  ⚠ Missing columns (skipped): {missing_cols}")

OUTPUT_PATH = os.path.join(RESULTS_DIR, "biogpt_pipeline_output.xlsx")
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

"""
analysis/gliner_ner/pipeline.py
───────────────────────────────
Unified Master Pipeline for GLiNER Clinical Entity Extraction + LLM Simplification.

Supported LLM Providers:
  - Groq Cloud API:
      • qwen/qwen3.8-27b
      • openai/gpt-oss-120b
  - Ollama Local Models:
      • ollama/medgemma:4b
      • ollama/gemma4:12b
      • ollama/llama3.1:8b
      • ollama/qwen3:8b

Requirements:
  pip install gliner pandas

Groq API Key:
  Configured in analysis/gliner_ner/.env (or GROQ_API_KEY env var)

Usage:
  # 1. Full Pipeline: GLiNER + Simplification with Groq Cloud model
  python -m analysis.gliner_ner.pipeline --models qwen/qwen3.8-27b --n 5
  python -m analysis.gliner_ner.pipeline --models openai/gpt-oss-120b --strategies gliner-repair-fewshot --n 5

  # 2. GLiNER Repair + Few-Shot Approach
  python -m analysis.gliner_ner.pipeline --models openai/gpt-oss-120b --strategies gliner-repair-fewshot --n 30
  python -m analysis.gliner_ner.pipeline --models qwen/qwen3.8-27b --strategies gliner-repair-fewshot --n 30
  python -m analysis.gliner_ner.pipeline --models ollama/medgemma:4b --strategies gliner-repair-fewshot --n 30

  # 3. Full Pipeline with Local Ollama model
  python -m analysis.gliner_ner.pipeline --models ollama/medgemma:4b --n 5

  # 4. Extraction Only (Benchmark GLiNER without LLM generation)
  python -m analysis.gliner_ner.pipeline --mode ner-only

  # 5. Interactive test on single report text
  python -m analysis.gliner_ner.pipeline --sample "Heart size is normal. No focal consolidation, pneumothorax, or large pleural effusion."

  # 6. Display benchmark summary table
  python -m analysis.gliner_ner.pipeline --summary
"""

import os
import sys
import time
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd


# ══════════════════════════════════════════════════════════════════════════════
# 1. PATH & ENVIRONMENT RESOLUTION (.env LOADING)
# ══════════════════════════════════════════════════════════════════════════════

def _load_env_file(path: Path):
    if not path.exists():
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip("'\"")
                    if k and k not in os.environ:
                        os.environ[k] = v
    except Exception:
        pass


def _resolve_paths():
    curr = Path(__file__).resolve().parent
    repo_root = curr
    for parent in [curr] + list(curr.parents):
        if (parent / ".git").exists() or (parent / "analysis").exists() or (parent / "datasets").exists():
            repo_root = parent
            break
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Load environment files in precedence order: local folder -> analysis/.env -> root/.env
    _load_env_file(curr / ".env")
    _load_env_file(repo_root / "analysis" / ".env")
    _load_env_file(repo_root / ".env")

    datasets_dir = repo_root / "datasets"
    results_dir = repo_root / "analysis" / "results"
    if not results_dir.exists():
        results_dir = repo_root / "results"

    gliner_results_dir = results_dir / "gliner_ner"
    return repo_root, datasets_dir, results_dir, gliner_results_dir


REPO_ROOT, DATASETS_DIR, RESULTS_DIR, GLINER_RESULTS_DIR = _resolve_paths()
OUT_JSON = GLINER_RESULTS_DIR / "results.json"
OUT_CSV = GLINER_RESULTS_DIR / "results.csv"
COMPARISON_CSV = GLINER_RESULTS_DIR / "comparison_with_llm.csv"
OPENI_BASELINE_JSON = RESULTS_DIR / "openi" / "results.json"
OPENI_30_CSV = DATASETS_DIR / "radiology_reports" / "openi_30_samples" / "openi_30_samples.csv"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()


# ══════════════════════════════════════════════════════════════════════════════
# 2. ENTITY LABELS & GLiNER EXTRACTOR
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_GLINER_MODEL = os.getenv("GLINER_MODEL_NAME", "Ihor/gliner-biomed-large-v1.0")

RADIOLOGY_ENTITY_LABELS = [
    "anatomical structure",
    "abnormal finding",
    "normal finding",
    "absent finding",
    "uncertain finding",
    "medical device",
    "measurement",
    "change over time",
]

DISCHARGE_ENTITY_LABELS = [
    "diagnosis", "medication", "procedure", "symptom", "vital sign", "lab result", "dosage", "date", "anatomical structure"
]

PATHOLOGY_ENTITY_LABELS = [
    "histological diagnosis", "tumor grade", "surgical margin", "anatomical structure", "biomarker", "measurement"
]


class GLiNERExtractor:
    """Self-contained GLiNER model wrapper for clinical entity extraction."""

    def __init__(self, model_name: str = DEFAULT_GLINER_MODEL, threshold: float = 0.4, device: Optional[str] = None):
        self.model_name = model_name
        self.threshold = threshold
        self.device = device
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from gliner import GLiNER
            except ImportError:
                raise ImportError("GLiNER is not installed. Install with: pip install gliner")
            print(f"Loading GLiNER checkpoint: {self.model_name}...")
            self._model = GLiNER.from_pretrained(self.model_name)
            if self.device:
                self._model = self._model.to(self.device)
        return self._model

    def predict_spans(self, text: str, labels: Optional[List[str]] = None, threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        if not text or not text.strip():
            return []
        target_labels = labels or RADIOLOGY_ENTITY_LABELS
        thresh = threshold if threshold is not None else self.threshold
        return self.model.predict_entities(text, target_labels, threshold=thresh)

    def extract_structured_json(self, text: str, datatype: str = "radiology", labels: Optional[List[str]] = None, threshold: Optional[float] = None) -> Dict[str, Any]:
        if not labels:
            labels = DISCHARGE_ENTITY_LABELS if datatype == "discharge" else PATHOLOGY_ENTITY_LABELS if datatype == "pathology" else RADIOLOGY_ENTITY_LABELS

        spans = self.predict_spans(text, labels=labels, threshold=threshold)
        normal_findings, abnormal_findings, measurements, anatomical_structures, incidental_findings = [], [], [], [], []
        diagnoses, medications, procedures = [], [], []

        for ent in spans:
            lbl = ent["label"].lower().strip()
            val = ent["text"].strip()
            if not val:
                continue

            if lbl == "normal finding":
                if val not in normal_findings:
                    normal_findings.append(val)
            elif lbl in ("abnormal finding", "uncertain finding", "symptom"):
                abnormal_findings.append({
                    "finding": val,
                    "location": "",
                    "severity": "abnormal" if lbl != "uncertain finding" else "uncertain",
                    "confidence": round(ent.get("score", 1.0), 3),
                })
            elif lbl == "measurement":
                measurements.append({"structure": "", "value": val, "unit": ""})
            elif lbl == "anatomical structure":
                if val not in anatomical_structures:
                    anatomical_structures.append(val)
            elif lbl in ("medical device", "change over time"):
                incidental_findings.append(f"{lbl}: {val}")
            elif lbl in ("diagnosis", "histological diagnosis"):
                if val not in diagnoses:
                    diagnoses.append(val)
            elif lbl == "medication":
                medications.append({"name": val, "dosage": ""})
            elif lbl == "procedure":
                if val not in procedures:
                    procedures.append(val)

        return {
            "exam_info": {
                "modality": "Radiology" if datatype == "radiology" else datatype.title(),
                "body_region": "Chest" if datatype == "radiology" else None,
                "anatomical_structures_identified": anatomical_structures,
            },
            "normal_findings": normal_findings,
            "abnormal_findings": abnormal_findings,
            "measurements": measurements,
            "incidental_findings": incidental_findings,
            "diagnoses": diagnoses,
            "medications": medications,
            "procedures": procedures,
            "raw_spans": spans,
        }

    @staticmethod
    def to_retention_block(ner_data: Dict[str, Any]) -> str:
        lines = ["=== EXTRACTED CLINICAL ENTITIES — YOU MUST RETAIN ALL OF THESE ==="]
        exam = ner_data.get("exam_info", {})
        if exam.get("modality"):
            lines.append(f"Exam: {exam.get('modality')} (Region: {exam.get('body_region', 'N/A')})")
        normals = ner_data.get("normal_findings", [])
        if normals:
            lines.append("Normal structures (reassure about these):")
            for nf in normals:
                lines.append(f"  ✓ {nf}")
        abnormals = ner_data.get("abnormal_findings", [])
        if abnormals:
            lines.append("Abnormal findings (MUST explain all of these):")
            for af in abnormals:
                lines.append(f"  [ABNORMAL] {af.get('finding', '')}")
        measurements = ner_data.get("measurements", [])
        if measurements:
            lines.append("Measurements to include:")
            for m in measurements:
                lines.append(f"  • {m.get('value', '')}")
        lines.append("=================================================================")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 3. PROMPTS & SIMPLIFICATION LOGIC (FEW-SHOT & REPAIR)
# ══════════════════════════════════════════════════════════════════════════════

# Import older regular few-shot benchmark prompts & builder
try:
    from analysis.prompts.builder import build_prompt
    from analysis.prompts.radiology_prompts import (
        RADIOLOGY_CXR_SIMPLIFY_SYSTEM_PROMPT,
        RADIOLOGY_CXR_SIMPLIFY_FEW_SHOT_EXAMPLES,
        RADIOLOGY_CXR_REPAIR_SYSTEM_PROMPT,
    )
except ImportError:
    build_prompt = None
    RADIOLOGY_CXR_SIMPLIFY_SYSTEM_PROMPT = None
    RADIOLOGY_CXR_SIMPLIFY_FEW_SHOT_EXAMPLES = None
    RADIOLOGY_CXR_REPAIR_SYSTEM_PROMPT = None

CXR_SIMPLIFY_SYSTEM_PROMPT = RADIOLOGY_CXR_SIMPLIFY_SYSTEM_PROMPT if RADIOLOGY_CXR_SIMPLIFY_SYSTEM_PROMPT else """You are a medical radiology simplification assistant. Rewrite the following chest X-ray report in simple, plain English that a patient with no medical training can understand (6th-grade reading level).

Rules:
1. Rewrite the report sentence by sentence, in the same order. Use one short sentence per finding.
2. Replace every medical term with everyday words (e.g. 'pleural effusion' -> 'fluid around the lungs', 'pneumothorax' -> 'air outside the lungs', 'cardiomediastinal silhouette' -> 'the heart and the area around it'). Keep a medical term only if there is no simple word for it.
3. Keep every negative finding as a negative: 'No pneumothorax' must stay 'There is no air outside the lungs'. Never drop the word 'no'.
4. Keep every positive finding, measurement, side (left/right) and comparison with earlier exams ('stable', 'increased', 'unchanged').
5. Do not add explanations, reassurance, advice or anything that is not in the report.
6. Write plain sentences only: no headings, bullet points or brackets.
7. Output only the rewritten text, nothing else."""

# 3 Curated Train Exemplars from the older regular few-shot benchmark
CXR_FEW_SHOT_EXAMPLES = RADIOLOGY_CXR_SIMPLIFY_FEW_SHOT_EXAMPLES if RADIOLOGY_CXR_SIMPLIFY_FEW_SHOT_EXAMPLES else [
    {   # Open-i 3242.xml (train)
        "input": "The heart and cardiomediastinal silhouette are normal in size and contour. There is no focal air space opacity, pleural effusion, or pneumothorax. There are multilevel degenerative changes in the thoracic spine. No acute cardiopulmonary finding.",
        "output": "The heart and the area around it look normal in size and shape. There is no sign of pneumonia, fluid around the lungs, or air outside the lungs. There are several levels of wear and tear in the spine. No sudden heart or lung problem is found."
    },
    {   # Open-i 3697.xml (train)
        "input": "The cardiomediastinal silhouette is stable in appearance. There are extensive fibrotic changes in the right lung with rightward shift of the trachea, similar to the previous exam. The left lung is well-aerated without focal airspace consolidation, pleural effusions or pneumothorax. There is left apical pleural-parenchymal scarring. No acute bony findings. 1. No acute cardiopulmonary findings. 2. Extensive fibrotic changes of the right lung, similar to the previous exam.",
        "output": "The heart and middle part of the chest look the same as before. The right lung has a lot of scar tissue, which is causing the windpipe to shift to the right, just like the last time it was checked. The left lung is well-inflated and doesn't have any specific areas of lung collapse, fluid around the lungs, or air outside the lungs. There is some scarring at the top of the left lung. There are no new bone issues. 1. There are no new heart or lung problems. 2. The right lung has a lot of scar tissue, just like it did before."
    },
    {   # Open-i 3694.xml (train)
        "input": "Interval removal of left-sided chest tube. Small residual left apical pneumothorax has increased slightly in size the prior exam, now measuring approximately 0.9 cm from the thoracic apex. Stable cardiomediastinal silhouette. No focal airspace consolidation. No pleural effusion. No acute cardiopulmonary abnormality.",
        "output": "The chest tube on the left side was removed. There's a small amount of air leakage around the lung on the left side, which has gotten a little bigger since the last check, now about 0.9 cm from the top of the chest. The heart and middle part of the chest look the same as before. There's no sign of a specific lung infection. No fluid is seen around the lungs. There are no urgent heart or lung issues."
    }
]

CXR_NER_GUIDED_SYSTEM_PROMPT = CXR_SIMPLIFY_SYSTEM_PROMPT.replace(
    "\n\nRules:", "\n\n{ner_retention_block}\n\nRules:", 1
) + "\n8. Every finding in the extracted entities block above must appear in your rewrite with the same meaning, including every negative ('no ...') finding."

CXR_REPAIR_SYSTEM_PROMPT = RADIOLOGY_CXR_REPAIR_SYSTEM_PROMPT if RADIOLOGY_CXR_REPAIR_SYSTEM_PROMPT else """You check a plain-language rewrite of a chest X-ray report. You are given the original report, a checklist of every finding in it, and a draft rewrite.

If the draft covers every checklist item with the correct meaning (including every 'no', side, size and comparison), output the draft exactly as it is.

Otherwise, fix only what is missing or wrong: add or correct those sentences in the same plain style and keep every other sentence unchanged. Do not add anything that is not in the report.

Output only the final text, nothing else."""


def build_regular_few_shot_prompt(source_text: str) -> Tuple[str, str]:
    """
    Constructs the system prompt and few-shot user prompt using the benchmark's
    original regular few-shot mechanism (from analysis/prompts/radiology_prompts.py
    and analysis/prompts/builder.py).
    """
    if build_prompt is not None:
        try:
            sys_prompt, user_prompt, _ = build_prompt("simplification", "radiology_cxr", "few-shot", source_text)
            return sys_prompt, user_prompt
        except Exception:
            pass

    # Fallback to exact identical structure as build_prompt
    sys_prompt = CXR_SIMPLIFY_SYSTEM_PROMPT
    user_parts = ["Here are examples of what I expect:\n"]
    for i, eg in enumerate(CXR_FEW_SHOT_EXAMPLES):
        user_parts.append(f"--- Example {i+1} ---")
        user_parts.append(f"Original Medical Report:\n{eg['input'].strip()}\n")
        user_parts.append(f"Output:\n{eg['output'].strip()}\n")
    user_parts.append("--- Your Task ---")
    user_parts.append("Please rewrite the following chest X-ray report in plain English for the patient:\n")
    user_parts.append(f"Original Medical Report:\n{source_text.strip()}\n")
    user_parts.append("Output:\n")
    return sys_prompt, "\n".join(user_parts)


def format_gliner_checklist(gliner_data: Dict[str, Any]) -> str:
    lines = []
    for nf in gliner_data.get("normal_findings", []):
        lines.append(f"- Normal: {nf}")
    for af in gliner_data.get("abnormal_findings", []):
        lines.append(f"- Abnormal: {af.get('finding', '')}")
    for raw in gliner_data.get("raw_spans", []):
        if raw.get("label") == "absent finding":
            lines.append(f"- Absent: No {raw.get('text', '')}")
    for m in gliner_data.get("measurements", []):
        lines.append(f"- Measurement: {m.get('value', '')}")
    return "\n".join(lines) if lines else "- All findings within normal limits."


def normalize_model_name(model_id: str) -> str:
    """Normalizes various model aliases to canonical IDs."""
    m = model_id.strip()
    m_clean = m.lower().replace("-", "").replace(" ", "").replace("_", "").replace("/", "")
    if "gptoss" in m_clean or "gpt120" in m_clean or m.lower() in ("openai/gpt-oss-120b", "cerebras/gptoss", "gpt-oss"):
        return "openai/gpt-oss-120b"
    elif "qwen27" in m_clean or "qwen3.8" in m_clean or m.lower() in ("qwen/qwen3.8-27b", "cerebras/qwen3.8", "qwen"):
        return "qwen/qwen3.8-27b"
    elif "medgemma" in m_clean or "medgemma:4b" in m_clean or m.lower() in ("ollama/medgemma:4b", "medgemma4b"):
        return "ollama/medgemma:4b"
    return m


def normalize_strategy_name(strategy: str) -> str:
    """Normalizes strategy name to canonical identifiers."""
    s = strategy.strip().lower()
    if s in ("gliner-repair-fewshot", "gliner-repair+fewshot", "gliner_repair_fewshot", "repair-fewshot", "repair+fewshot", "gliner-repair", "repair"):
        return "gliner-repair-fewshot"
    elif s in ("gliner-guided", "guided"):
        return "gliner-guided"
    return s


# ══════════════════════════════════════════════════════════════════════════════
# 4. LLM INFERENCE (GROQ CLOUD & OLLAMA LOCAL)
# ══════════════════════════════════════════════════════════════════════════════

def call_groq(model_id: str, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> Tuple[str, float]:
    """Sends a chat completion request to Groq Cloud API."""
    key = (os.getenv("GROQ_API_KEY") or GROQ_API_KEY).strip()
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set. Please configure it in analysis/gliner_ner/.env")

    # Normalize model ID aliases
    normalized_model = normalize_model_name(model_id)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    payload = {
        "model": normalized_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 512 if "qwen" in normalized_model.lower() else 1024,
    }
    if "qwen" in normalized_model.lower():
        payload["reasoning_format"] = "hidden"

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": "Mozilla/5.0",  # Required to prevent Cloudflare 403 Forbidden
        },
        method="POST",
    )
    t0 = time.time()
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
                time.sleep(0.5)  # Courteous pause to avoid bursts
                return text, time.time() - t0
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", "ignore")
            if e.code == 429 and attempt < max_retries - 1:
                wait_sec = 2.0 * (attempt + 1)
                import re
                match = re.search(r"try again in ([\d\.]+)s", err_msg)
                if match:
                    try:
                        wait_sec = max(wait_sec, float(match.group(1)) + 1.0)
                    except ValueError:
                        pass
                print(f"[Groq rate limit: waiting {wait_sec:.1f}s before retry {attempt+1}/{max_retries}...]", flush=True)
                time.sleep(wait_sec)
                continue
            raise RuntimeError(f"Groq API HTTP {e.code} for '{normalized_model}': {err_msg[:300]}")
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2.0)
                continue
            raise RuntimeError(f"Groq API error for '{normalized_model}': {e}")


def call_ollama(model_id: str, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> Tuple[str, float]:
    """Sends a local chat completion request to the Ollama daemon."""
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    payload = {
        "model": model_id.replace("ollama/", ""),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "think": False,
        "options": {"temperature": temperature, "num_predict": 4096, "num_ctx": 8192},
    }
    req = urllib.request.Request(
        f"{ollama_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = (data.get("message", {}).get("content") or "").strip()
            return text, time.time() - t0
    except Exception as e:
        raise RuntimeError(f"Ollama call to '{model_id}' failed: {e}")


def call_llm(model: str, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> Tuple[str, float]:
    """Routes generation request to Groq Cloud or Local Ollama."""
    m_lower = model.lower()
    if m_lower.startswith("ollama/") or any(k in m_lower for k in ("medgemma", "gemma", "llama", "deepseek", "qwen3:8b")):
        return call_ollama(model, system_prompt, user_prompt, temperature=temperature)
    else:
        # Defaults to Groq for cloud execution
        return call_groq(model, system_prompt, user_prompt, temperature=temperature)


# ══════════════════════════════════════════════════════════════════════════════
# 5. DATASET LOADER & EVALUATOR
# ══════════════════════════════════════════════════════════════════════════════

def load_dataset(dataset_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Loads clinical samples from custom CSV or the default openi_30_samples.csv."""
    csv_file = Path(dataset_path) if dataset_path else OPENI_30_CSV
    if not csv_file.exists():
        raise FileNotFoundError(f"Dataset CSV not found at: {csv_file}")

    df = pd.read_csv(csv_file)
    text_col = "report" if "report" in df.columns else ("radiology_report" if "radiology_report" in df.columns else df.columns[0])
    ref_col = "simplified_summary" if "simplified_summary" in df.columns else ("layman_report" if "layman_report" in df.columns else (df.columns[-1] if len(df.columns) > 1 else None))

    # Map report text to original XML sample_id if baseline results exist to maintain exact IDs
    text_to_sid = {}
    if OPENI_BASELINE_JSON.exists():
        try:
            with open(OPENI_BASELINE_JSON, "r", encoding="utf-8") as f:
                b_records = json.load(f)
            text_to_sid = {
                r["source_text"].strip(): r["sample_id"]
                for r in b_records if r.get("source_text") and r.get("sample_id")
            }
        except Exception:
            pass

    samples = []
    for idx, row in df.iterrows():
        rep = str(row[text_col]).strip() if pd.notna(row[text_col]) else ""
        ref = str(row[ref_col]).strip() if (ref_col and pd.notna(row[ref_col])) else ""
        if not rep:
            continue
        sid = str(row.get("sample_id") or text_to_sid.get(rep, f"openi_{idx+1}.xml"))
        samples.append({
            "sample_id": sid,
            "datatype": "radiology",
            "source_text": rep,
            "reference_text": ref,
        })
    return samples


def evaluate_output(source_text: str, generated_text: str, reference_text: str) -> Dict[str, Any]:
    """Runs quality & readability evaluations against the gold reference with graceful per-metric fallback."""
    scores: Dict[str, Any] = {}
    if not generated_text or not generated_text.strip():
        return scores

    # 1. Readability
    try:
        from analysis.metrics.readability import compute_readability_metrics
        scores.update(compute_readability_metrics(generated_text))
    except Exception:
        try:
            import textstat
            scores["flesch_reading_ease"] = round(textstat.flesch_reading_ease(generated_text), 2)
            scores["flesch_kincaid_grade_level"] = round(textstat.flesch_kincaid_grade(generated_text), 2)
        except Exception:
            pass

    # 2. Quality (SARI, ROUGE, BERTScore)
    try:
        from analysis.metrics.quality import compute_sari, compute_rouge_scores, compute_bertscore
        if reference_text:
            scores["sari"] = compute_sari(source_text, generated_text, [reference_text])
            scores.update(compute_rouge_scores(reference_text, generated_text))
            scores.update(compute_bertscore(reference_text, generated_text))
    except Exception as e:
        print(f"(quality metrics notice: {e})", end=" ")

    # 3. Meaning Preservation (SIM)
    try:
        from analysis.metrics.meaning_preservation import compute_sbert_cosine_similarity
        if reference_text:
            scores["sim_reference"] = compute_sbert_cosine_similarity(reference_text, generated_text)
    except Exception:
        pass

    # 4. Factuality (AlignScore - requires .cache/alignscore/AlignScore-base.ckpt)
    try:
        from analysis.metrics.factuality import compute_alignscore
        scores["alignscore"] = compute_alignscore(source_text, generated_text)
    except Exception:
        scores["alignscore"] = None

    return scores


def backfill_missing_metrics(records: List[Dict[str, Any]], save_callback: Optional[Any] = None) -> int:
    """
    Checks all existing successful translations to see if any evaluation metric
    (such as alignscore, sari, rougeL_f1, bertscore_f1, flesch_reading_ease, fkgl)
    is missing or None, and backfills it without re-running the translation.

    Optimizations:
      - Validates 'rougeL_f1' correctly (preventing redundant re-computation of core metrics).
      - If only AlignScore is missing, computes ONLY AlignScore (avoids re-running BERTScore on CPU).
      - Emits live progress prints and incrementally saves after backfilled records.
    """
    alignscore_ckpt = REPO_ROOT / ".cache" / "alignscore" / "AlignScore-base.ckpt"
    alignscore_ready = alignscore_ckpt.exists() and alignscore_ckpt.stat().st_size > 1_500_000_000

    to_process = []
    for r in records:
        if r.get("status") != "success" or not r.get("output_text"):
            continue

        mets = r.setdefault("metrics", {})
        needs_alignscore = alignscore_ready and (mets.get("alignscore") is None)
        has_rouge = (mets.get("rougeL_f1") is not None) or (mets.get("rouge_l") is not None)
        needs_core = any(
            (mets.get(m) is None) for m in ("sari", "bertscore_f1", "flesch_reading_ease")
        ) or not has_rouge

        if needs_alignscore or needs_core:
            to_process.append((r, needs_alignscore, needs_core))

    if not to_process:
        return 0

    print(f"\n[Backfill] Found {len(to_process)} records with missing evaluation metrics. Backfilling now...", flush=True)
    updated = 0
    t0 = time.time()

    for i, (r, needs_alignscore, needs_core) in enumerate(to_process, 1):
        src = r.get("source_text", "")
        out = r.get("output_text", "")
        ref = r.get("reference_text", "")
        mets = r.setdefault("metrics", {})
        sid = r.get("sample_id", "?")
        m = r.get("model", "?")
        s = r.get("strategy", "?")

        actions = []
        if needs_alignscore and not needs_core:
            actions.append("AlignScore")
            try:
                from analysis.metrics.factuality import compute_alignscore
                score = compute_alignscore(src, out)
                if score is not None:
                    mets["alignscore"] = score
            except Exception as e:
                pass
        elif needs_core:
            actions.append("Core Metrics + AlignScore" if needs_alignscore else "Core Metrics")
            new_mets = evaluate_output(src, out, ref)
            for k, v in new_mets.items():
                if v is not None:
                    mets[k] = v

        updated += 1
        print(f"  [Backfill {i}/{len(to_process)}] Backfilled {', '.join(actions)} for {m} | {s} ({sid})", flush=True)

        if save_callback and (i % 5 == 0 or i == len(to_process)):
            save_callback()

    elapsed = time.time() - t0
    print(f"[Backfill] Finished backfilling {updated} records in {elapsed:.1f}s.\n", flush=True)
    return updated


# ══════════════════════════════════════════════════════════════════════════════
# 6. PIPELINE RUNNER & SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

def run_full_pipeline(
    models: List[str],
    strategies: List[str],
    gliner_model_name: str = DEFAULT_GLINER_MODEL,
    dataset_path: Optional[str] = None,
    max_samples: Optional[int] = None,
    threshold: float = 0.4,
    ner_only: bool = False,
    resume: bool = True,
):
    print(f"\nInitializing GLiNER model: {gliner_model_name}...")
    gliner_extractor = GLiNERExtractor(model_name=gliner_model_name, threshold=threshold)

    # Load dataset from custom path or default openi_30_samples.csv
    samples = load_dataset(dataset_path=dataset_path)
    ds_label = dataset_path if dataset_path else "openi_30_samples.csv"
    print(f"Loaded {len(samples)} reports from '{ds_label}'.")

    GLINER_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    if resume and OUT_JSON.exists():
        try:
            with open(OUT_JSON, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            records = []

    # 1. Backfill any evaluation columns that were left unprocessed (e.g. AlignScore)
    updated_count = backfill_missing_metrics(records, save_callback=lambda: _save_records(records))
    if updated_count > 0:
        _save_records(records)

    # 2. Only consider successful translations with valid output as completed.
    # Any previous run that resulted in an error will be re-processed.
    done_keys = {
        (r.get("sample_id"), r.get("model"), r.get("strategy"))
        for r in records
        if r.get("status") == "success" and r.get("output_text")
    }

    # ── MODE 1: NER-Only Extraction Benchmark ─────────────────────────────────
    if ner_only:
        print("\n--- Running NER-Only Extraction Benchmark ---")
        pending_samples = [
            s for s in samples
            if not (resume and (s["sample_id"], gliner_model_name, "gliner-extraction") in done_keys)
        ]
        completed_count = len(samples) - len(pending_samples)
        if not pending_samples:
            print(f"[{gliner_model_name}] All {len(samples)} reports already extracted. Skipping.")
            return

        to_run = pending_samples[:max_samples] if max_samples else pending_samples
        print(f"Total: {len(samples)} | Completed: {completed_count} | Pending: {len(pending_samples)} | Processing batch of: {len(to_run)}")

        for i, s in enumerate(to_run, 1):
            sid = s["sample_id"]
            key = (sid, gliner_model_name, "gliner-extraction")

            text = s["source_text"]
            t0 = time.time()
            spans = gliner_extractor.predict_spans(text)
            structured_json = gliner_extractor.extract_structured_json(text, datatype=s.get("datatype", "radiology"))
            latency = time.time() - t0

            counts: Dict[str, int] = {"total": len(spans)}
            for sp in spans:
                lbl = sp.get("label", "unknown")
                counts[lbl] = counts.get(lbl, 0) + 1

            records.append({
                "sample_id": sid,
                "model": gliner_model_name,
                "strategy": "gliner-extraction",
                "status": "success",
                "latency_seconds": round(latency, 4),
                "source_text": text,
                "reference_text": s.get("reference_text", ""),
                "ner_json": structured_json,
                "entity_counts": counts,
            })
            done_keys.add(key)
            _save_records(records)
            print(f"[{gliner_model_name}] ({i}/{len(to_run)}) Extracted report {sid} ({latency:.3f}s)...", flush=True)

        _save_and_print_ner_summary(records)
        return

    # ── MODE 2: End-to-End GLiNER + Simplification Pipeline ──────────────────
    norm_models = [normalize_model_name(m) for m in models]
    norm_strategies = [normalize_strategy_name(s) for s in strategies]
    print(f"\n--- Running End-to-End Pipeline: {len(norm_models)} models x {len(norm_strategies)} strategies ---")
    for model in norm_models:
        for strategy in norm_strategies:
            pending_samples = [
                s for s in samples
                if not (resume and (s["sample_id"], model, strategy) in done_keys)
            ]
            completed_count = len(samples) - len(pending_samples)
            if not pending_samples:
                print(f"\n[{model} | {strategy}] All {len(samples)} reports are already completed. Skipping.")
                continue

            to_run = pending_samples[:max_samples] if max_samples else pending_samples
            print(f"\n[{model} | {strategy}] Total: {len(samples)} | Completed: {completed_count} | Pending: {len(pending_samples)} | Processing next batch of {len(to_run)} reports...")

            for i, s in enumerate(to_run, 1):
                sid = s["sample_id"]
                key = (sid, model, strategy)
                src = s["source_text"]
                ref = s["reference_text"]
                print(f"[{model} | {strategy}] ({i}/{len(to_run)}) Processing report {sid}...", flush=True)

                # Stage 1: GLiNER Extraction
                t0 = time.time()
                gliner_json = gliner_extractor.extract_structured_json(src, datatype=s.get("datatype", "radiology"))
                ner_latency = time.time() - t0

                # Stage 2: Simplification
                t_llm_0 = time.time()
                draft = None
                try:
                    if strategy == "gliner-guided":
                        block = GLiNERExtractor.to_retention_block(gliner_json)
                        sys_prompt = CXR_NER_GUIDED_SYSTEM_PROMPT.replace("{ner_retention_block}", block)
                        user_prompt = f"Rewrite the following chest X-ray report in plain English for the patient:\n\n{src.strip()}"
                        output_text, _ = call_llm(model, sys_prompt, user_prompt)
                    elif strategy == "gliner-repair-fewshot":
                        # GLiNER Repair + Full Benchmark Few-Shot Approach
                        # Step 1: Draft using the 3-example benchmark few-shot mechanism
                        draft_sys, draft_user = build_regular_few_shot_prompt(src)
                        draft, _ = call_llm(model, draft_sys, draft_user)

                        # Step 2: GLiNER checklist extraction
                        checklist = format_gliner_checklist(gliner_json)

                        # Step 3: GLiNER repair verification
                        repair_user = f"Original report:\n{src.strip()}\n\nChecklist:\n{checklist}\n\nDraft rewrite:\n{draft.strip()}\n\nFinal text:"
                        output_text, _ = call_llm(model, CXR_REPAIR_SYSTEM_PROMPT, repair_user)
                    else:
                        raise ValueError(f"Unknown strategy: {strategy}")

                    total_latency = (time.time() - t_llm_0) + ner_latency
                    status = "success"
                    error = None
                except Exception as e:
                    output_text = ""
                    total_latency = time.time() - t_llm_0
                    status = "error"
                    error = str(e)

                # Stage 3: Evaluation
                metrics = {}
                if status == "success" and ref:
                    metrics = evaluate_output(src, output_text, ref)

                rec = {
                    "sample_id": sid,
                    "model": model,
                    "strategy": strategy,
                    "status": status,
                    "error": error,
                    "latency_seconds": round(total_latency, 3),
                    "gliner_latency_seconds": round(ner_latency, 4),
                    "source_text": src,
                    "reference_text": ref,
                    "output_text": output_text,
                    "metrics": metrics,
                    "ner_json": gliner_json,
                }
                if draft is not None:
                    rec["draft_text"] = draft

                # Update existing record if key exists (e.g. replacing a prior error), else append
                match_idx = next((idx for idx, existing in enumerate(records) if (existing.get("sample_id"), existing.get("model"), existing.get("strategy")) == key), None)
                if match_idx is not None:
                    records[match_idx] = rec
                else:
                    records.append(rec)

                if status == "success":
                    done_keys.add(key)

                sari = metrics.get("sari", 0.0)
                status_icon = "✓" if status == "success" else "✗"
                print(f"[{model} | {strategy}] {sid} {status_icon} (SARI: {sari:.1f}, time: {total_latency:.2f}s)")

                _save_records(records)

    _save_records(records)
    print_simplification_summary(records)


def _save_records(records: List[Dict[str, Any]]):
    tmp = OUT_JSON.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    tmp.replace(OUT_JSON)

    flat = [{**{k: v for k, v in r.items() if k != "metrics"}, **(r.get("metrics") or {})} for r in records]
    pd.DataFrame(flat).to_csv(OUT_CSV, index=False)


def _save_and_print_ner_summary(records: List[Dict[str, Any]]):
    _save_records(records)
    df = pd.DataFrame(records)
    print("\n" + "=" * 80)
    print("GLiNER EXTRACTION BENCHMARK SUMMARY")
    print("=" * 80)
    print(f"Total processed: {len(df)}")
    print(f"Average latency: {df['latency_seconds'].mean() * 1000:.1f} ms")
    print(f"Throughput: {1.0 / df['latency_seconds'].mean():.1f} reports/second")
    print(f"Saved: {OUT_JSON} and {OUT_CSV}")
    print("=" * 80 + "\n")


def print_simplification_summary(records: List[Dict[str, Any]]):
    curr_rows = []
    for r in records:
        if r.get("status") == "success" and r.get("metrics"):
            curr_rows.append({
                "model": r.get("model"),
                "strategy": r.get("strategy"),
                **r.get("metrics", {}),
            })

    if not curr_rows:
        print("No evaluated simplification records found.")
        return

    baseline_rows = []
    if OPENI_BASELINE_JSON.exists():
        try:
            with open(OPENI_BASELINE_JSON, "r", encoding="utf-8") as f:
                b_records = json.load(f)
            for r in b_records:
                strat = r.get("strategy")
                if r.get("status") == "success" and strat in ("few-shot", "ner-guided") and r.get("metrics"):
                    baseline_rows.append({
                        "model": r.get("model"),
                        "strategy": f"baseline_{strat}",
                        **r.get("metrics", {}),
                    })
        except Exception:
            pass

    summary_metrics = ["sari", "rougeL_f1", "bertscore_f1", "alignscore", "flesch_reading_ease", "flesch_kincaid_grade_level"]
    all_rows = baseline_rows + curr_rows
    df = pd.DataFrame(all_rows)
    cols = [c for c in summary_metrics if c in df.columns]

    print("\n" + "=" * 90)
    print("GLiNER + SIMPLIFICATION BENCHMARK LEADERBOARD (GROQ / OLLAMA)")
    print("=" * 90)
    groups = ["model", "strategy"]
    summary_table = df.groupby(groups)[cols].mean().round(2)
    summary_table.insert(0, "N", df.groupby(groups).size())
    print(summary_table.to_string())
    print("=" * 90)
    print(f"Outputs written to: {OUT_JSON} and {OUT_CSV}\n")


def main():
    parser = argparse.ArgumentParser(description="Unified Pipeline for GLiNER + Simplification with Groq Cloud & Ollama.")
    parser.add_argument("--mode", choices=["all", "ner-only", "simplify"], default="all", help="Execution mode.")
    parser.add_argument(
        "--models",
        nargs="+",
        default=["qwen/qwen3.8-27b"],
        help="LLM models for simplification (e.g. qwen/qwen3.8-27b, openai/gpt-oss-120b, ollama/medgemma:4b).",
    )
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=["gliner-guided", "gliner-repair-fewshot"],
        help="Strategies to run: gliner-guided, gliner-repair-fewshot.",
    )
    parser.add_argument("--gliner-model", default=DEFAULT_GLINER_MODEL, help="GLiNER model checkpoint.")
    parser.add_argument("--dataset-path", default=None, help="Path to custom CSV dataset (defaults to openi_30_samples.csv).")
    parser.add_argument("--n", type=int, default=5, help="Number of reports to run.")
    parser.add_argument("--threshold", type=float, default=0.4, help="GLiNER confidence threshold.")
    parser.add_argument("--no-resume", action="store_true", help="Overwrite previous cached results.")
    parser.add_argument("--rescore", action="store_true", help="Backfill missing metrics (e.g. AlignScore) for existing outputs without re-generating.")
    parser.add_argument("--summary", action="store_true", help="Display saved summary table.")
    parser.add_argument("--sample", type=str, default=None, help="Test raw clinical text interactively.")

    args = parser.parse_args()

    if args.sample:
        extractor = GLiNERExtractor(model_name=args.gliner_model, threshold=args.threshold)
        print(f"\n--- Input Text ---\n{args.sample}\n")
        res = extractor.extract_structured_json(args.sample)
        print("--- Extracted JSON ---")
        print(json.dumps(res, indent=2))
        print("\n--- Downstream Retention Block ---")
        print(GLiNERExtractor.to_retention_block(res))
        return

    if args.rescore:
        if OUT_JSON.exists():
            with open(OUT_JSON, "r", encoding="utf-8") as f:
                records = json.load(f)
            updated = backfill_missing_metrics(records, save_callback=lambda: _save_records(records))
            print(f"Rescored and backfilled missing metrics for {updated} records.")
            _save_records(records)
            print_simplification_summary(records)
        else:
            print(f"No results found at {OUT_JSON}")
        return

    if args.summary:
        if OUT_JSON.exists():
            with open(OUT_JSON, "r", encoding="utf-8") as f:
                records = json.load(f)
            print_simplification_summary(records)
        else:
            print(f"No results file found at {OUT_JSON}")
        return

    models = [normalize_model_name(m) for m in args.models]
    strategies = [normalize_strategy_name(s) for s in args.strategies]

    run_full_pipeline(
        models=models,
        strategies=strategies,
        gliner_model_name=args.gliner_model,
        dataset_path=args.dataset_path,
        max_samples=args.n,
        threshold=args.threshold,
        ner_only=(args.mode == "ner-only"),
        resume=not args.no_resume,
    )


if __name__ == "__main__":
    main()

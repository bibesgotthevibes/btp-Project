"""
analysis/metrics/factuality.py
──────────────────────────────
Factual consistency of the output against the SOURCE report via AlignScore
(Zha et al., ACL 2023), the factuality metric used by BioLaySumm.
- alignscore   (precision): is every output claim supported by the source? Low = invented content.
- completeness (recall):    is every source sentence supported by the output? Low = omitted findings.
  missed_findings counts source sentences the output doesn't cover (score < MISSED_THRESHOLD).
All 0-100 except missed_findings.

Setup (once):
  checkpoint: curl -L -o .cache/alignscore/AlignScore-base.ckpt \
      https://huggingface.co/yzha/AlignScore/resolve/main/AlignScore-base.ckpt
  packages:   see analysis/requirements.txt (alignscore installed with --no-deps)
"""

import os
import re
from functools import lru_cache
from pathlib import Path

ALIGNSCORE_CKPT = Path(os.getenv(
    "ALIGNSCORE_CKPT",
    Path(__file__).resolve().parents[2] / ".cache" / "alignscore" / "AlignScore-base.ckpt",
))


@lru_cache(maxsize=1)
def _alignscore():
    if not ALIGNSCORE_CKPT.exists():
        raise FileNotFoundError(f"AlignScore checkpoint not found at {ALIGNSCORE_CKPT} (see factuality.py docstring)")
    import torch
    import transformers
    transformers.AdamW = torch.optim.AdamW  # alignscore imports this (training-only); removed in new transformers
    from alignscore import AlignScore
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    return AlignScore(model="roberta-base", batch_size=8, device=device,
                      ckpt_path=str(ALIGNSCORE_CKPT), evaluation_mode="nli_sp", verbose=False)


def compute_alignscore(source_text: str, generated_text: str) -> float:
    if not source_text.strip() or not generated_text.strip():
        return 0.0
    return round(float(_alignscore().score(contexts=[source_text], claims=[generated_text])[0]) * 100.0, 2)


# Calibrated on the 30 benchmark gold references: at 0.1, 6% of their source sentences are
# flagged (paraphrases like "pleural effusion" -> "fluid around the lungs" score ~0.4-0.6;
# genuinely omitted findings score ~0.01-0.05).
MISSED_THRESHOLD = 0.1
_SENT = re.compile(r"(?<=[.!?])\s+")


def compute_completeness(source_text: str, generated_text: str) -> dict:
    """AlignScore in reverse: each source sentence is a claim checked against the output."""
    sents = [s for s in _SENT.split(source_text.strip()) if len(re.findall(r"[A-Za-z]{2,}", s)) >= 2]
    if not sents or not generated_text.strip():
        return {"completeness": 0.0, "missed_findings": len(sents)}
    scores = _alignscore().score(contexts=[generated_text] * len(sents), claims=sents)
    return {"completeness": round(sum(scores) / len(scores) * 100.0, 2),
            "missed_findings": sum(1 for x in scores if x < MISSED_THRESHOLD)}

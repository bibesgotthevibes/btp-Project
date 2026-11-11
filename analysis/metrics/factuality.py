"""
analysis/metrics/factuality.py
──────────────────────────────
Factual consistency of the output against the SOURCE report via AlignScore
(Zha et al., ACL 2023), the factuality metric used by BioLaySumm.
0-100; higher = every output claim is supported by the source. Low = hallucination.

Setup (once):
  checkpoint: curl -L -o .cache/alignscore/AlignScore-base.ckpt \
      https://huggingface.co/yzha/AlignScore/resolve/main/AlignScore-base.ckpt
  packages:   see analysis/requirements.txt (alignscore installed with --no-deps)
"""

import os
from functools import lru_cache
from pathlib import Path

ALIGNSCORE_CKPT = Path(os.getenv(
    "ALIGNSCORE_CKPT",
    Path(__file__).resolve().parents[2] / ".cache" / "alignscore" / "AlignScore-base.ckpt",
))


def ensure_alignscore_checkpoint() -> bool:
    if ALIGNSCORE_CKPT.exists() and ALIGNSCORE_CKPT.stat().st_size > 1_500_000_000:
        return True
    ALIGNSCORE_CKPT.parent.mkdir(parents=True, exist_ok=True)
    url = "https://huggingface.co/yzha/AlignScore/resolve/main/AlignScore-base.ckpt"
    print(f"\n[AlignScore] Checkpoint not found. Downloading (~1.8GB) to {ALIGNSCORE_CKPT}...", flush=True)
    import subprocess
    cmd = ["curl", "-L", "-C", "-", "-o", str(ALIGNSCORE_CKPT), url]
    subprocess.run(cmd, check=True)
    return ALIGNSCORE_CKPT.exists() and ALIGNSCORE_CKPT.stat().st_size > 1_500_000_000


@lru_cache(maxsize=1)
def _alignscore():
    if not ALIGNSCORE_CKPT.exists() or ALIGNSCORE_CKPT.stat().st_size < 1_500_000_000:
        ensure_alignscore_checkpoint()
    if not ALIGNSCORE_CKPT.exists():
        raise FileNotFoundError(f"AlignScore checkpoint not found at {ALIGNSCORE_CKPT} (see factuality.py docstring)")
    import torch
    import transformers
    transformers.AdamW = torch.optim.AdamW  # alignscore imports this (training-only); removed in new transformers
    import alignscore.inference
    import re

    _orig_sent_tokenize = alignscore.inference.sent_tokenize
    def _safe_sent_tokenize(text, **kwargs):
        try:
            return _orig_sent_tokenize(text, **kwargs)
        except Exception:
            sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
            return sents if sents else [text]
    alignscore.inference.sent_tokenize = _safe_sent_tokenize

    from alignscore import AlignScore
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    return AlignScore(model="roberta-base", batch_size=8, device=device,
                      ckpt_path=str(ALIGNSCORE_CKPT), evaluation_mode="nli_sp", verbose=False)


def compute_alignscore(source_text: str, generated_text: str) -> float:
    if not source_text.strip() or not generated_text.strip():
        return 0.0
    return round(float(_alignscore().score(contexts=[source_text], claims=[generated_text])[0]) * 100.0, 2)


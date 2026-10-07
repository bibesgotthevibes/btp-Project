"""
run_ner_pipeline.py
───────────────────
One-shot script to launch the NER-guided simplification pipeline and
save output to a log file. Run from the d:/btp-Project directory.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env from analysis/.env
from pathlib import Path
env_path = Path(__file__).parent / "analysis" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())
    print(f"✅ Loaded .env from {env_path}")
else:
    print(f"⚠️  No .env found at {env_path}")

from analysis.runner import run_benchmark

if __name__ == "__main__":
    records = run_benchmark(
        tasks=["simplification"],
        strategies=["ner-guided"],
        resume=True,
        dry_run=False,
        smoke_test=False,
        run_eval_inline=True,
        pace_delay=2.0,
    )
    print(f"\n✅ Pipeline complete. {len(records)} records written.")

"""
analysis/gliner_ner
───────────────────
Unified Task 3 Package: GLiNER Entity Extraction + Downstream Simplification.
"""

def get_pipeline():
    from .pipeline import run_full_pipeline, GLiNERExtractor
    return run_full_pipeline, GLiNERExtractor

__all__ = ["get_pipeline"]

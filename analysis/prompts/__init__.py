"""Prompts package for medical simplification, summarization, and NER-guided simplification."""
from .builder import (
    build_prompt,
    build_ner_extraction_prompt,
    build_ner_guided_prompt,
    PROMPT_REGISTRY,
    NER_GUIDED_SYSTEM_PROMPTS,
)

__all__ = [
    "build_prompt",
    "build_ner_extraction_prompt",
    "build_ner_guided_prompt",
    "PROMPT_REGISTRY",
    "NER_GUIDED_SYSTEM_PROMPTS",
]

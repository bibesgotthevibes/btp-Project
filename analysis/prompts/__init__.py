"""Prompts package for medical simplification and summarization."""
from .builder import build_prompt, PROMPT_REGISTRY

__all__ = ["build_prompt", "PROMPT_REGISTRY"]

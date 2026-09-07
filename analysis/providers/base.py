"""
analysis/providers/base.py
──────────────────────────
Abstract provider class and standardized GenerationResult dataclass.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class GenerationResult:
    """Standardized output container for any model generation trial."""
    text: str = ""
    status: str = "success"  # "success" | "skipped" | "error"
    error: Optional[str] = None
    provider: str = ""
    model: str = ""
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_seconds: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "status": self.status,
            "error": self.error,
            "provider": self.provider,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "latency_seconds": round(self.latency_seconds, 3),
            "extra": self.extra,
        }

class BaseProvider:
    """Base interface for all LLM API providers."""
    
    def generate(
        self,
        model_id: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> GenerationResult:
        """Execute a text generation call and return a GenerationResult."""
        raise NotImplementedError

"""
analysis/providers/router.py
────────────────────────────
Model routing and dispatch engine.
Routes experiment model strings to appropriate providers with graceful fallback:
- 'gemini/*'   -> GeminiProvider (with fallback_models from config)
- 'cerebras/*' -> CerebrasProvider, falling back to Groq
- 'ollama/*'   -> OllamaProvider (local)
See MODEL_ENDPOINTS in config.py for the exact model IDs.
"""

from typing import Dict, Any, Optional
from .base import GenerationResult
from .gemini_provider import GeminiProvider
from .cerebras_provider import CerebrasProvider
from .groq_provider import GroqProvider
from .ollama_provider import OllamaProvider
from ..config import (
    MODEL_ENDPOINTS,
    GEMINI_API_KEY,
    CEREBRAS_API_KEY,
    GROQ_API_KEY,
)

class ModelRouter:
    def __init__(
        self,
        gemini_key: Optional[str] = None,
        cerebras_key: Optional[str] = None,
        groq_key: Optional[str] = None,
        allow_substitute: bool = True,
    ):
        # When False, never swap in a different model (e.g. gemini-2.5-flash for
        # gemini-3.8-flash) — return the error so results stay correctly labelled.
        self.allow_substitute = allow_substitute
        self.gemini_provider = GeminiProvider(gemini_key or GEMINI_API_KEY)
        self.cerebras_provider = CerebrasProvider(cerebras_key or CEREBRAS_API_KEY)
        self.groq_provider = GroqProvider(groq_key or GROQ_API_KEY)
        self.ollama_provider = OllamaProvider()

    def generate(
        self,
        model_key: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> GenerationResult:
        """Route generation request to the appropriate provider and model ID."""
        cfg = MODEL_ENDPOINTS.get(model_key, {})
        provider_type = cfg.get("provider", "")
        model_id = cfg.get("model_id", model_key)

        # ── 1. Gemini Models ──────────────────────────────────────────────────
        if provider_type == "gemini" or "gemini" in model_key.lower():
            if not self.gemini_provider.api_key:
                return GenerationResult(
                    status="skipped",
                    error="GEMINI_API_KEY is not configured",
                    provider="gemini",
                    model=model_id,
                )

            # Try primary model ID (e.g. gemini-3.8-flash / gemini-3.1-pro-preview)
            res = self.gemini_provider.generate(
                model_id=model_id,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            # If model encountered error (503 high demand, 429 quota, 404) and fallback models exist, try fallback
            if res.status == "error" and self.allow_substitute and cfg.get("fallback_models"):
                for fb_model in cfg.get("fallback_models", []):
                    fb_res = self.gemini_provider.generate(
                        model_id=fb_model,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    if fb_res.status == "success":
                        fb_res.extra["fallback_used"] = True
                        fb_res.extra["requested_model"] = model_id
                        return fb_res
            return res

        # ── 2. Cerebras Models (with Groq Fallback) ───────────────────────────
        if provider_type == "cerebras" or "cerebras" in model_key.lower():
            # If Cerebras key is available, try Cerebras first
            if self.cerebras_provider.api_key:
                res = self.cerebras_provider.generate(
                    model_id=model_id,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if res.status == "success":
                    return res

                # If Cerebras failed (402 payment required, 429, 404, etc.), fallback to Groq
                if self.groq_provider.api_key:
                    groq_model = cfg.get("groq_model_id") or model_id
                    groq_candidates = [groq_model] + [m for m in cfg.get("fallback_models", []) if m != groq_model]
                    groq_errors = []
                    for alt_model in groq_candidates:
                        groq_res = self.groq_provider.generate(
                            model_id=alt_model,
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                        if groq_res.status == "success" and (groq_res.text or "").strip():
                            groq_res.extra = groq_res.extra or {}
                            groq_res.extra["fallback_provider"] = "groq"
                            groq_res.extra["requested_model"] = model_id
                            return groq_res
                        groq_errors.append(f"{alt_model}: {(groq_res.error or 'empty response')[:300]}")
                    # Surface the Groq failures too, not just the Cerebras one
                    res.error = f"{res.error} | groq: " + " || ".join(groq_errors)

                return res

            # If Cerebras key is NOT available but Groq key is, route to Groq
            if self.groq_provider.api_key:
                groq_model = cfg.get("groq_model_id") or model_id
                groq_candidates = [groq_model] + [m for m in cfg.get("fallback_models", []) if m != groq_model]
                for alt_model in groq_candidates:
                    groq_res = self.groq_provider.generate(
                        model_id=alt_model,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    if groq_res.status == "success" and (groq_res.text or "").strip():
                        groq_res.extra["routed_to"] = "groq"
                        groq_res.extra["requested_model"] = model_id
                        return groq_res
                return groq_res

            # Neither key is present
            return GenerationResult(
                status="skipped",
                error="Neither CEREBRAS_API_KEY nor GROQ_API_KEY is configured",
                provider="cerebras",
                model=model_id,
            )

        # ── 3. Local Ollama Models ────────────────────────────────────────────
        if provider_type == "ollama":
            return self.ollama_provider.generate(
                model_id=model_id,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        # ── 4. Unknown model fallback ─────────────────────────────────────────
        return GenerationResult(
            status="error",
            error=f"Unrecognized model configuration for '{model_key}'",
            provider="unknown",
            model=model_key,
        )

"""
analysis/providers/ollama_provider.py
─────────────────────────────────────
Local Ollama provider (no API key). Calls the native /api/chat endpoint.
"""

import json
import time
import urllib.request
import urllib.error

from .base import BaseProvider, GenerationResult
from ..config import OLLAMA_URL, REQUEST_TIMEOUT


class OllamaProvider(BaseProvider):
    def generate(
        self,
        model_id: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> GenerationResult:
        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "think": False,  # hide reasoning traces from thinking models (qwen3, deepseek-r1)
            "options": {"temperature": temperature, "num_predict": max_tokens, "num_ctx": 8192},
        }
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        start = time.time()
        try:
            # Local generation is slow on first load; allow 5x the cloud timeout.
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT * 5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return GenerationResult(status="error", error=f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}",
                                    provider="ollama", model=model_id, latency_seconds=time.time() - start)
        except (urllib.error.URLError, TimeoutError) as e:
            return GenerationResult(status="error", error=f"Ollama unreachable at {OLLAMA_URL}: {e}",
                                    provider="ollama", model=model_id, latency_seconds=time.time() - start)

        text = (data.get("message", {}).get("content") or "").strip()
        prompt_tokens, completion_tokens = data.get("prompt_eval_count"), data.get("eval_count")
        return GenerationResult(
            text=text,
            status="success" if text else "error",
            error=None if text else "Empty generation content returned",
            provider="ollama",
            model=model_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=(prompt_tokens or 0) + (completion_tokens or 0),
            latency_seconds=time.time() - start,
        )

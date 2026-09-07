"""
analysis/providers/cerebras_provider.py
───────────────────────────────────────
Cerebras Cloud API provider calling OpenAI-compatible chat completions.
Handles:
- OpenAI-compatible REST endpoint (api.cerebras.ai/v1/chat/completions)
- Rate limits (429) with exponential backoff
- Graceful skipping if CEREBRAS_API_KEY is not configured
"""

import json
import time
import urllib.request
import urllib.error
from typing import Optional

from .base import BaseProvider, GenerationResult
from ..config import (
    CEREBRAS_API_KEY,
    CEREBRAS_API_URL,
    MAX_RETRIES,
    INITIAL_RETRY_DELAY,
    REQUEST_TIMEOUT,
)

class CerebrasProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or CEREBRAS_API_KEY or "").strip()

    def generate(
        self,
        model_id: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> GenerationResult:
        if not self.api_key:
            return GenerationResult(
                status="skipped",
                error="CEREBRAS_API_KEY is not configured",
                provider="cerebras",
                model=model_id,
            )

        endpoint = CEREBRAS_API_URL

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # For Qwen models suppress reasoning format if supported
        if "qwen" in model_id.lower():
            payload["reasoning_format"] = "hidden"

        payload_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "MedBenchmark-Analysis/1.0",
        }

        delay = INITIAL_RETRY_DELAY
        last_error = ""

        for attempt in range(MAX_RETRIES + 1):
            start_time = time.time()
            try:
                try:
                    import requests
                    resp = requests.post(
                        endpoint,
                        headers=headers,
                        json=payload,
                        timeout=REQUEST_TIMEOUT,
                    )
                    latency = time.time() - start_time

                    if resp.status_code == 200:
                        data = resp.json()
                        text = (
                            data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                        )
                        usage = data.get("usage", {})
                        return GenerationResult(
                            text=text.strip(),
                            status="success",
                            provider="cerebras",
                            model=model_id,
                            prompt_tokens=usage.get("prompt_tokens"),
                            completion_tokens=usage.get("completion_tokens"),
                            total_tokens=usage.get("total_tokens"),
                            latency_seconds=latency,
                        )

                    status_code = resp.status_code
                    error_text = resp.text
                except ImportError:
                    req = urllib.request.Request(
                        endpoint,
                        data=payload_bytes,
                        headers=headers,
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                        latency = time.time() - start_time
                        data = json.loads(response.read().decode("utf-8"))
                        text = (
                            data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                        )
                        usage = data.get("usage", {})
                        return GenerationResult(
                            text=text.strip(),
                            status="success",
                            provider="cerebras",
                            model=model_id,
                            prompt_tokens=usage.get("prompt_tokens"),
                            completion_tokens=usage.get("completion_tokens"),
                            total_tokens=usage.get("total_tokens"),
                            latency_seconds=latency,
                        )

                last_error = f"HTTP {status_code}: {error_text[:300]}"
                if status_code in (429, 503) and attempt < MAX_RETRIES:
                    time.sleep(delay)
                    delay *= 2
                    continue
                return GenerationResult(
                    status="error",
                    error=last_error,
                    provider="cerebras",
                    model=model_id,
                    latency_seconds=time.time() - start_time,
                )

            except urllib.error.HTTPError as e:
                latency = time.time() - start_time
                err_body = e.read().decode("utf-8") if e.fp else str(e)
                last_error = f"HTTP {e.code}: {err_body[:300]}"
                if e.code in (429, 503) and attempt < MAX_RETRIES:
                    time.sleep(delay)
                    delay *= 2
                    continue
                return GenerationResult(
                    status="error",
                    error=last_error,
                    provider="cerebras",
                    model=model_id,
                    latency_seconds=latency,
                )
            except Exception as e:
                latency = time.time() - start_time
                last_error = f"Request error: {str(e)}"
                if attempt < MAX_RETRIES:
                    time.sleep(delay)
                    delay *= 2
                    continue
                return GenerationResult(
                    status="error",
                    error=last_error,
                    provider="cerebras",
                    model=model_id,
                    latency_seconds=latency,
                )

        return GenerationResult(
            status="error",
            error=f"Exceeded max retries. Last error: {last_error}",
            provider="cerebras",
            model=model_id,
        )

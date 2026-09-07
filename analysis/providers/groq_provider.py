"""
analysis/providers/groq_provider.py
───────────────────────────────────
Groq API provider calling OpenAI-compatible chat completions.
Used as primary/fallback provider for GPT-OSS (openai/gpt-oss-20b)
and Qwen (qwen/qwen3.6-27b).
"""

import json
import time
import urllib.request
import urllib.error
from typing import Optional

from .base import BaseProvider, GenerationResult
from ..config import (
    GROQ_API_KEY,
    GROQ_API_URL,
    MAX_RETRIES,
    INITIAL_RETRY_DELAY,
    REQUEST_TIMEOUT,
)

class GroqProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or GROQ_API_KEY or "").strip()

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
                error="GROQ_API_KEY is not configured",
                provider="groq",
                model=model_id,
            )

        endpoint = GROQ_API_URL

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": min(max_tokens, 2048),
        }

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
                        choice = data.get("choices", [{}])[0]
                        msg = choice.get("message", {})
                        text = (msg.get("content") or "").strip()
                        if not text and msg.get("reasoning"):
                            text = (msg.get("reasoning") or "").strip()

                        if not text:
                            last_error = f"Empty generation content returned (finish_reason={choice.get('finish_reason')})"
                            if attempt < MAX_RETRIES:
                                time.sleep(delay)
                                delay *= 2
                                continue
                            return GenerationResult(
                                status="error",
                                error=last_error,
                                provider="groq",
                                model=model_id,
                                latency_seconds=latency,
                            )

                        usage = data.get("usage", {})
                        return GenerationResult(
                            text=text,
                            status="success",
                            provider="groq",
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
                        choice = data.get("choices", [{}])[0]
                        msg = choice.get("message", {})
                        text = (msg.get("content") or "").strip()
                        if not text and msg.get("reasoning"):
                            text = (msg.get("reasoning") or "").strip()

                        if not text:
                            last_error = f"Empty generation content returned (finish_reason={choice.get('finish_reason')})"
                            if attempt < MAX_RETRIES:
                                time.sleep(delay)
                                delay *= 2
                                continue
                            return GenerationResult(
                                status="error",
                                error=last_error,
                                provider="groq",
                                model=model_id,
                                latency_seconds=latency,
                            )

                        usage = data.get("usage", {})
                        return GenerationResult(
                            text=text,
                            status="success",
                            provider="groq",
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
                    provider="groq",
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
                    provider="groq",
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
                    provider="groq",
                    model=model_id,
                    latency_seconds=latency,
                )

        return GenerationResult(
            status="error",
            error=f"Exceeded max retries. Last error: {last_error}",
            provider="groq",
            model=model_id,
        )

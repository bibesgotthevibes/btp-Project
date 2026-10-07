"""
analysis/providers/gemini_provider.py
─────────────────────────────────────
Google Gemini API provider calling REST generateContent endpoint.
Handles:
- gemini-3.8-flash
- gemini-3.1-pro-preview
- Automatic retry on 429/503 with exponential backoff
- Graceful return if GEMINI_API_KEY is not configured
"""

import json
import time
import urllib.request
import urllib.error
from typing import Optional

from .base import BaseProvider, GenerationResult
from ..config import (
    GEMINI_API_KEY,
    GEMINI_API_URL,
    MAX_RETRIES,
    INITIAL_RETRY_DELAY,
    REQUEST_TIMEOUT,
)

def _result_from_response(data: dict, model_id: str, latency: float) -> GenerationResult:
    """Build a result from a generateContent response, flagging cut-off output as an error."""
    candidate = data.get("candidates", [{}])[0]
    text = "".join(p.get("text", "") for p in candidate.get("content", {}).get("parts", []) if not p.get("thought"))
    usage = data.get("usageMetadata", {})
    finish = candidate.get("finishReason")
    if finish == "MAX_TOKENS":
        # Thinking models spend output budget on hidden reasoning; a cut-off answer is not a result
        return GenerationResult(
            status="error",
            error=f"Output truncated (finishReason=MAX_TOKENS, thinking tokens={usage.get('thoughtsTokenCount')})",
            provider="gemini",
            model=model_id,
            latency_seconds=latency,
        )
    return GenerationResult(
        text=text.strip(),
        status="success",
        provider="gemini",
        model=model_id,
        prompt_tokens=usage.get("promptTokenCount"),
        completion_tokens=usage.get("candidatesTokenCount"),
        total_tokens=usage.get("totalTokenCount"),
        latency_seconds=latency,
        extra={"finish_reason": finish, "thinking_tokens": usage.get("thoughtsTokenCount")},
    )


class GeminiProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or GEMINI_API_KEY or "").strip()

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
                error="GEMINI_API_KEY is not configured",
                provider="gemini",
                model=model_id,
            )

        endpoint = f"{GEMINI_API_URL}/{model_id}:generateContent?key={self.api_key}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        payload_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
        }

        delay = INITIAL_RETRY_DELAY
        last_error = ""

        for attempt in range(MAX_RETRIES + 1):
            start_time = time.time()
            try:
                # Use requests if installed, otherwise urllib
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
                        return _result_from_response(data, model_id, latency)

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
                        return _result_from_response(data, model_id, latency)

                # Inspect HTTP error for retryable conditions
                last_error = f"HTTP {status_code}: {error_text[:300]}"
                if status_code in (429, 503) and attempt < MAX_RETRIES:
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    return GenerationResult(
                        status="error",
                        error=last_error,
                        provider="gemini",
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
                    provider="gemini",
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
                    provider="gemini",
                    model=model_id,
                    latency_seconds=latency,
                )

        return GenerationResult(
            status="error",
            error=f"Exceeded max retries. Last error: {last_error}",
            provider="gemini",
            model=model_id,
        )

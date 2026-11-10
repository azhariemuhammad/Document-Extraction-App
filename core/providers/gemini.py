import os
import time

from google import genai
from google.genai import errors, types

from core.providers.base import Capabilities, GenerateResponse, ModelProvider, ProviderError


class GeminiProvider(ModelProvider):
    name = "gemini"
    capabilities = Capabilities(images=True, native_json_schema=True, max_images_per_call=16)

    def __init__(self):
        key = os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", "")
        if not key or not self.model:
            raise ValueError("Gemini needs GEMINI_API_KEY and GEMINI_MODEL in .env (see .env.example).")
        self.client = genai.Client(api_key=key)

    def generate(self, prompt: str, images: list[bytes], schema: dict) -> GenerateResponse:
        parts = [types.Part.from_bytes(data=img, mime_type="image/png") for img in images]
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=schema,
            temperature=0,  # extraction should be repeatable, not creative
        )
        start = time.perf_counter()
        try:
            resp = self.client.models.generate_content(model=self.model, contents=[*parts, prompt], config=config)
        except errors.APIError as e:
            # 429 (quota) and 5xx are worth retrying; 400/401/403/404 mean our request or key is wrong
            retryable = e.code == 429 or (e.code or 0) >= 500
            raise ProviderError(f"Gemini API error {e.code}: {e.message}", retryable=retryable) from e
        except Exception as e:  # network drops and timeouts
            raise ProviderError(f"Could not reach Gemini: {e}", retryable=True) from e

        if not resp.text:
            reason = resp.prompt_feedback.block_reason if resp.prompt_feedback else "empty response"
            raise ProviderError(f"Gemini returned no text ({reason}).", retryable=False)

        usage = resp.usage_metadata
        out_tokens = None
        if usage and usage.candidates_token_count is not None:
            out_tokens = usage.candidates_token_count + (usage.thoughts_token_count or 0)  # thinking is billed
        return GenerateResponse(
            text=resp.text, model=self.model,
            input_tokens=usage.prompt_token_count if usage else None, output_tokens=out_tokens,
            latency_ms=int((time.perf_counter() - start) * 1000),
        )

"""Per-page extraction: cache -> provider call (with retry) -> parse (with one repair call)."""
import hashlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path

from pydantic import TypeAdapter

from core.models import Block, PageResult, PageUnit
from core.prompts import PROMPT_VERSION, build_prompt
from core.providers.base import GenerateResponse, ModelProvider, ProviderError

MAX_ATTEMPTS = 4
_BLOCKS = TypeAdapter(list[Block])


class _Tally:
    """Adds up provider calls, tokens and time across retries and the repair call."""

    def __init__(self):
        self.calls = 0
        self.latency_ms = 0
        self.input_tokens: int | None = None
        self.output_tokens: int | None = None

    def add(self, resp: GenerateResponse):
        self.latency_ms += resp.latency_ms
        if resp.input_tokens is not None:
            self.input_tokens = (self.input_tokens or 0) + resp.input_tokens
        if resp.output_tokens is not None:
            self.output_tokens = (self.output_tokens or 0) + resp.output_tokens


def extract_document(
    file_bytes: bytes,
    pages: list[PageUnit],
    provider: ModelProvider,
    instruction: str,
    on_progress: Callable[[int, int], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> list[PageResult]:
    results = []
    for i, page in enumerate(pages, start=1):  # sequential on purpose: free-tier rate limits
        results.append(extract_page(file_bytes, page, provider, instruction, sleep))
        if on_progress:
            on_progress(i, len(pages))
    return results


def extract_page(file_bytes: bytes, page: PageUnit, provider: ModelProvider, instruction: str,
                 sleep: Callable[[float], None] = time.sleep) -> PageResult:
    # The instruction and prompt version are in the key: change either and old answers are not reused.
    key = hashlib.sha256(
        b"\0".join([file_bytes, str(page.page_no).encode(), instruction.encode(),
                    provider.model.encode(), PROMPT_VERSION.encode()])
    ).hexdigest()
    cache_file = Path(os.getenv("CACHE_DIR", "data/cache")) / f"{key}.json"
    if cache_file.exists():
        return PageResult.model_validate_json(cache_file.read_text()).model_copy(update={"cached": True})

    result = _call_provider(page, provider, instruction, sleep)
    if not result.error:  # failures are never cached, so a re-run tries again
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(result.model_dump_json())
    return result


def _call_provider(page: PageUnit, provider: ModelProvider, instruction: str, sleep) -> PageResult:
    prompt = build_prompt(instruction, page.page_no, page.text_layer)
    schema = _BLOCKS.json_schema()
    if not provider.capabilities.native_json_schema:
        prompt += f"\n\nReturn JSON matching this schema:\n{json.dumps(schema)}"

    tally = _Tally()
    try:
        resp = _generate_with_retry(provider, prompt, [page.image_png], schema, tally, sleep)
        try:
            blocks = _parse(resp.text, page.page_no)
        except ValueError as e:  # includes bad JSON and schema violations
            repair = (f"{prompt}\n\nYour previous answer was invalid ({e}).\n"
                      f"Previous answer:\n{resp.text}\n\nReturn corrected JSON only.")
            resp = _generate_with_retry(provider, repair, [page.image_png], schema, tally, sleep)
            blocks = _parse(resp.text, page.page_no)
    except (ProviderError, ValueError) as e:
        error = str(e) if isinstance(e, ProviderError) else f"Model returned unusable output after a repair attempt: {e}"
        return PageResult(page=page.page_no, error=error, model=provider.model, attempts=tally.calls,
                          latency_ms=tally.latency_ms, input_tokens=tally.input_tokens,
                          output_tokens=tally.output_tokens)
    return PageResult(page=page.page_no, blocks=blocks, model=resp.model, attempts=tally.calls,
                      latency_ms=tally.latency_ms, input_tokens=tally.input_tokens,
                      output_tokens=tally.output_tokens)


def _generate_with_retry(provider, prompt, images, schema, tally: _Tally, sleep) -> GenerateResponse:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        tally.calls += 1
        try:
            resp = provider.generate(prompt, images, schema)
        except ProviderError as e:
            if not e.retryable or attempt == MAX_ATTEMPTS:
                raise
            sleep(2 ** attempt)  # 2s, 4s, 8s: gives a rate limit or overloaded model time to recover
            continue
        tally.add(resp)
        return resp


def _parse(text: str, page_no: int) -> list[Block]:
    try:
        blocks = _BLOCKS.validate_python(json.loads(text))
    except ValueError as e:  # json.JSONDecodeError and pydantic.ValidationError are both ValueErrors
        raise ValueError(str(e)[:800]) from e
    # The page number is known to us; don't rely on the model to echo it correctly.
    return [b.model_copy(update={"page": page_no}) for b in blocks]

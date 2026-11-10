"""Per-page extraction. Retry, cache and repair are added in block 3."""
import json
from collections.abc import Callable

from pydantic import TypeAdapter

from core.models import Block, PageResult, PageUnit
from core.prompts import build_prompt
from core.providers.base import ModelProvider

_BLOCKS = TypeAdapter(list[Block])


def extract_document(
    pages: list[PageUnit],
    provider: ModelProvider,
    instruction: str,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[PageResult]:
    results = []
    for i, page in enumerate(pages, start=1):  # sequential on purpose: free-tier rate limits
        results.append(extract_page(page, provider, instruction))
        if on_progress:
            on_progress(i, len(pages))
    return results


def extract_page(page: PageUnit, provider: ModelProvider, instruction: str) -> PageResult:
    prompt = build_prompt(instruction, page.page_no, page.text_layer)
    try:
        resp = provider.generate(prompt, [page.image_png], _BLOCKS.json_schema())
        blocks = _BLOCKS.validate_python(json.loads(resp.text))
    except Exception as e:  # a failed page must not stop the run
        return PageResult(page=page.page_no, error=f"{type(e).__name__}: {e}", model=provider.model)
    return PageResult(
        page=page.page_no, blocks=blocks, model=resp.model, latency_ms=resp.latency_ms,
        input_tokens=resp.input_tokens, output_tokens=resp.output_tokens,
    )

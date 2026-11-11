"""One run from file bytes to Markdown. Used by the UI and the CLI so they behave identically."""
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from core.extractor import extract_document
from core.loaders import load_document
from core.models import PageResult, ValidationReport
from core.providers.base import ModelProvider
from core.renderer import render_markdown
from core.validator import validate


@dataclass
class RunOutput:
    results: list[PageResult]
    report: ValidationReport
    run_info: dict
    markdown: str


def run_pipeline(data: bytes, mime: str, instruction: str, provider: ModelProvider,
                 checks: list[dict[str, str]] = [],
                 on_progress: Callable[[int, int], None] | None = None) -> RunOutput:
    started = time.perf_counter()
    pages = load_document(data, mime)
    results = extract_document(data, pages, provider, instruction, on_progress)
    report = validate(results, len(pages), {p.page_no: p.text_layer for p in pages}, checks)

    run_info = {
        "provider": provider.name,
        "model": provider.model,
        "pages": len(pages),
        "total time": f"{time.perf_counter() - started:.1f}s",
        "tokens (in/out)": f"{sum(r.input_tokens or 0 for r in results)} / {sum(r.output_tokens or 0 for r in results)}",
        "provider calls": sum(r.attempts for r in results if not r.cached),
        "cache hits": sum(r.cached for r in results),
        "coverage": f"{report.coverage:.0%}",
        "grounded evidence": "n/a" if report.grounded_rate is None else f"{report.grounded_rate:.0%}",
        "arithmetic checks": report.checks_passed or "n/a",
        "failed pages": [r.page for r in results if r.error] or "none",
    }
    return RunOutput(results, report, run_info, render_markdown(results, report, run_info))


def save_outputs(out: RunOutput, name: str) -> Path:
    """Write <name>.md and <name>.json to outputs/. The JSON is what the evaluation reads."""
    folder = Path(os.getenv("OUTPUT_DIR", "outputs"))
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.md").write_text(out.markdown)
    payload = {"run_info": out.run_info, "results": [r.model_dump() for r in out.results]}
    (folder / f"{name}.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False))
    return folder / f"{name}.md"

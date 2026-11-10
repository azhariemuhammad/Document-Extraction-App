"""Runnable fake adapter. Tests the integration (loader -> extractor -> validator -> renderer -> UI),
NOT extraction accuracy. Its output is canned and ignores the image."""
import json
import re
import time

from core.providers.base import Capabilities, GenerateResponse, ModelProvider, ProviderError


class FakeProvider(ModelProvider):
    name = "fake"
    model = "fake-1"
    capabilities = Capabilities(images=True, native_json_schema=True, max_images_per_call=1)

    def __init__(self, fail_times: int = 0, retryable: bool = True, bad_json_times: int = 0):
        self.fail_times = fail_times
        self.retryable = retryable
        self.bad_json_times = bad_json_times
        self.calls = 0

    def generate(self, prompt: str, images: list[bytes], schema: dict) -> GenerateResponse:
        start = time.perf_counter()
        self.calls += 1
        if self.fail_times > 0:
            self.fail_times -= 1
            raise ProviderError("fake provider: simulated 429 rate limit", retryable=self.retryable)
        if self.bad_json_times > 0:
            self.bad_json_times -= 1
            return GenerateResponse("this is not json", self.model, 100, 5, 1)

        m = re.search(r"PAGE NUMBER:\s*(\d+)", prompt)
        page = int(m.group(1)) if m else 1
        blocks = [
            {"type": "heading", "text": "Fake document", "page": page, "region": "top",
             "status": "ok", "excerpt": "Fake document"},
            {"type": "field", "key": "1", "label": "Net income", "text": "Rp62.628.902", "page": page,
             "region": "line 1", "status": "uncertain", "note": "Canned value: the fake provider never reads the page.",
             "excerpt": "Penghasilan Neto Fiskal Rp62.628.902"},
            {"type": "checkbox", "key": "9.a", "label": "Option ticked", "checked": True, "page": page,
             "region": "line 9", "status": "ok", "excerpt": "9.a [x]"},
            {"type": "table", "key": "Table 1", "label": "Example table", "columns": ["Condition", "Time (s)"],
             "rows": [["A", "12"], ["B", "15"]], "page": page, "region": "Table 1", "status": "ok",
             "excerpt": "Condition Time (s) A 12 B 15"},
            {"type": "chart", "key": "Fig. 2", "label": "Task time", "columns": ["Condition", "Time (s)"],
             "rows": [["A", "~45"], ["B", "~52"]], "unit": "s", "page": page, "region": "Fig. 2",
             "status": "estimated", "note": "Values read visually from bars.", "excerpt": "Fig. 2 Task time"},
            {"type": "field", "key": "KLU", "label": "Business sector code", "text": None, "page": page,
             "region": "header", "status": "unreadable", "note": "Masked as xx xx xx.", "excerpt": "xx xx xx"},
        ]
        return GenerateResponse(
            text=json.dumps(blocks), model=self.model, input_tokens=1000, output_tokens=200,
            latency_ms=int((time.perf_counter() - start) * 1000) + 1,
        )

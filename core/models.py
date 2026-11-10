"""Data model shared by every module."""
from typing import Literal

from pydantic import BaseModel


class PageUnit(BaseModel):
    page_no: int
    image_png: bytes
    text_layer: str | None  # None for images: nothing to ground against
    width: int
    height: int


class Block(BaseModel):
    """One extracted item. Flat on purpose: Gemini's schema mode handles flat optional
    fields better than unions of block types."""
    type: Literal["heading", "paragraph", "table", "chart", "field", "checkbox"]
    key: str | None = None  # stable id: form line ("9", "8a") or "Table 2"
    label: str | None = None
    text: str | None = None
    columns: list[str] | None = None
    rows: list[list[str]] | None = None  # first cell = row label
    unit: str | None = None
    checked: bool | None = None
    status: Literal["ok", "uncertain", "unreadable", "missing", "estimated"] = "ok"
    page: int
    region: str | None = None
    excerpt: str  # verbatim supporting text from the source
    note: str | None = None  # reason for a non-ok status


class PageResult(BaseModel):
    page: int
    blocks: list[Block] = []
    error: str | None = None
    model: str
    latency_ms: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached: bool = False
    attempts: int = 1


class Issue(BaseModel):
    severity: Literal["error", "warning", "info"]
    page: int | None = None
    key: str | None = None
    message: str


class ValidationReport(BaseModel):
    issues: list[Issue] = []
    grounded_rate: float | None = None
    coverage: float = 1.0
    checks_passed: str | None = None


class UnsupportedInputError(Exception):
    """Unknown MIME type, corrupt file, etc. Shown in the UI."""

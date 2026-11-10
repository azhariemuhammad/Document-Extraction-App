import io

import pymupdf
import pytest
from PIL import Image

from core.extractor import extract_document
from core.loaders import load_document
from core.models import UnsupportedInputError
from core.providers.fake import FakeProvider
from core.renderer import render_markdown


def make_pdf(n_pages: int) -> bytes:
    doc = pymupdf.open()
    for i in range(n_pages):
        doc.new_page().insert_text((72, 72), f"Hello page {i + 1}")
    return doc.tobytes()


def make_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_pdf_has_one_unit_per_page_with_text_layer():
    pages = load_document(make_pdf(3), "application/pdf")
    assert [p.page_no for p in pages] == [1, 2, 3]
    assert "Hello page 2" in pages[1].text_layer


def test_image_is_one_page_without_text_layer():
    pages = load_document(make_png(), "image/png")
    assert len(pages) == 1 and pages[0].text_layer is None


def test_bad_inputs_are_rejected_with_a_message():
    with pytest.raises(UnsupportedInputError):
        load_document(b"not a pdf", "application/pdf")
    with pytest.raises(UnsupportedInputError):
        load_document(b"not an image", "image/png")
    with pytest.raises(UnsupportedInputError):
        load_document(b"x", "text/plain")


def test_end_to_end_with_fake_provider_marks_uncertainty():
    pages = load_document(make_pdf(2), "application/pdf")
    results = extract_document(b"doc", pages, FakeProvider(), "extract everything")
    assert all(r.error is None for r in results)
    statuses = {b.status for r in results for b in r.blocks}
    assert {"uncertain", "estimated", "unreadable"} <= statuses
    md = render_markdown(results)
    assert "## Page 2" in md and "≈ values estimated from chart" in md and "[x]" in md


def test_failed_page_is_reported_not_raised():
    pages = load_document(make_pdf(2), "application/pdf")
    results = extract_document(b"doc", pages, FakeProvider(fail_times=1, retryable=False), "x")
    assert results[0].error and results[1].error is None
    assert "This page failed" in render_markdown(results)

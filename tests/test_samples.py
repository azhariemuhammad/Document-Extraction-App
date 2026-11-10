from pathlib import Path

import pytest

from core.loaders import load_document

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_research_pdf_has_18_pages_with_text_layer():
    path = SAMPLES / "research_paper_applied_ergonomics.pdf"
    if not path.exists():
        pytest.skip("sample PDF not in samples/")
    pages = load_document(path.read_bytes(), "application/pdf")
    assert len(pages) == 18
    assert all(p.text_layer for p in pages)


def test_tax_form_image_is_one_page_without_text_layer():
    path = SAMPLES / "tax_form_spt_1771.jpg"
    if not path.exists():
        pytest.skip("sample image not in samples/")
    pages = load_document(path.read_bytes(), "image/jpeg")
    assert len(pages) == 1 and pages[0].text_layer is None

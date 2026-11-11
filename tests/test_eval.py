import json

from core.models import Block, PageResult
from eval.run_eval import matches, operational, relative_error, score, section


def block(**kw):
    base = dict(type="field", status="ok", page=1, excerpt="x")
    return Block(**{**base, **kw})


def page(blocks, **kw):
    base = dict(page=1, blocks=blocks, error=None, model="m", latency_ms=1000, input_tokens=10, output_tokens=5, cached=False, attempts=1)
    return PageResult(**{**base, **kw})


def test_match_types():
    assert matches("numeric", "1900100", "Rp1.900.100")
    assert not matches("numeric", "1900100", "Rp1.900.101")
    assert matches("exact", "Abc", " abc ")
    assert matches("contains", "ergonom", "Applied Ergonomics")
    assert matches("numeric_tol", "100", "~110")
    assert not matches("numeric_tol", "100", "~120")
    assert not matches("exact", "a", None)


def test_relative_error_parses_tilde():
    assert relative_error("40", "~45") == 0.125


def test_null_expected_is_skipped():
    gold = {"items": [{"key": "A", "page": 1, "kind": "field", "field": "text", "expected": None, "match": "exact"}]}
    s = score(gold, [page([block(key="A", text="v")])])
    assert s["skipped"] == 1 and s["kinds"] == {}


def test_per_kind_accuracy():
    gold = {"items": [
        {"key": "A", "kind": "field", "field": "text", "expected": "5", "match": "numeric"},
        {"key": "B", "kind": "field", "field": "text", "expected": "7", "match": "numeric"},
        {"key": "C", "kind": "checkbox", "field": "checked", "expected": True, "match": "exact"},
        {"key": "T", "kind": "table_cell", "field": "cell", "row": "r1", "column": "c2", "expected": "9", "match": "exact"},
        {"key": "F", "kind": "chart", "field": "cell", "row": "VH", "column": "Time", "expected": "40", "match": "numeric_tol"},
        {"key": "G", "kind": "chart", "field": "cell", "row": "VH", "column": "Time", "expected": "40", "match": "numeric_tol"},
    ]}
    blocks = [
        block(key="A", text="5"), block(key="B", text="8"),
        block(type="checkbox", key="C", checked=True),
        block(type="table", key="T", columns=["", "c1", "c2"], rows=[["r1", "1", "9"]]),
        block(type="chart", key="F", status="estimated", columns=["Cond", "Time"], rows=[["VH", "~44"]]),
    ]
    s = score(gold, [page(blocks)])
    assert s["kinds"] == {"field": (1, 2), "checkbox": (1, 1), "table_cell": (1, 1), "chart": (1, 2)}
    assert s["chart_missing"] == 1 and len(s["chart_errors"]) == 1 and abs(s["chart_errors"][0] - 0.1) < 1e-9


def test_operational_counts():
    op = operational([page([], attempts=3), page([], error="boom", attempts=1, latency_ms=0)])
    assert op["retries"] == 2 and op["failed_pages"] == 1 and op["tokens_in"] == 20


def test_section_end_to_end(tmp_path):
    gold = tmp_path / "g.json"
    gold.write_text(json.dumps({"status": "UNVERIFIED", "items": [
        {"key": "A", "kind": "field", "field": "text", "expected": None, "match": "exact"}]}))
    out = tmp_path / "doc__full_document.json"
    out.write_text(json.dumps({"run_info": {}, "results": [page([block(key="A", text="v")]).model_dump()]}))
    text = section(gold, out)
    assert "0 / 1" in text and "Pending owner check" in text and "n/a (no verified items)" in text

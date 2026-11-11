import json

from core.models import Block, PageResult
from eval.run_eval import find_value, flatten, matches, operational, relative_error, score, section


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


def it(**kw):
    base = dict(id="X1", kind="field", match="exact", verified=True, page=1)
    return {**base, **kw}


def one(item, blocks, **kw):
    s = score({"items": [[item]]}, [page(blocks, **kw)])
    return s["failed"] == [] and sum(h for h, _ in s["kinds"].values()) == 1


def test_nested_items_flatten_and_pending_unverified():
    assert flatten([[{"a": 1}, {"a": 2}], {"a": 3}]) == [{"a": 1}, {"a": 2}, {"a": 3}]
    gold = {"items": [[it(id="A", key="A", expected="v"), it(id="B", key="B", expected="v", verified=False),
                       it(id="C", key="C", expected="v", verified=None), {"key": "D", "kind": "field", "expected": "v", "match": "exact", "id": "D"}]]}
    s = score(gold, [page([block(key="A", text="v")])])
    assert s["items"] == 4 and s["skipped"] == 3 and [i["id"] for i in s["pending"]] == ["B", "C", "D"]
    assert s["kinds"] == {"field": (1, 1)} and s["failed"] == []


def test_failed_items_listed_with_got():
    s = score({"items": [it(key="A", expected="v")]}, [page([block(key="A", text="w")])])
    assert s["failed"] == [{"id": "X1", "key": "A", "expected": "v", "got": "w"}]


def test_match_normalized_date_and_row_contains_all():
    assert matches("normalized", "-.739*", "− 0.739*") is False  # leading zero differs: stays strict
    assert matches("normalized", "-0.18 (0.42)", "− 0.18 (0.42)")
    assert matches("normalized", "12 345 678 9 000 000", "12.345.678.9-000.000")
    assert matches("date", "30-04-2022", "30/04/2022") and not matches("date", "30-04-2022", "31.04.2022")
    assert matches("row_contains_all", ["Verbal", "vocal"], "VV Verbal  Vocal x")
    assert not matches("row_contains_all", ["Verbal", "Gaze"], "VV Verbal")
    assert matches("all_chart_blocks", "estimated", ["estimated", "estimated"])
    assert not matches("all_chart_blocks", "estimated", ["estimated", "ok"]) and not matches("all_chart_blocks", "estimated", [])
    assert matches("pages_with_result", 3, 3) and not matches("pages_with_result", 3, 2)


def test_numeric_tol_rel_abs_and_default():
    assert matches("numeric_tol", 100, "~108", {"rel": 0.08}) and not matches("numeric_tol", 100, "~109", {"rel": 0.08})
    assert matches("numeric_tol", 0, "0.2", {"abs": 0.3}) and not matches("numeric_tol", 0, "0.4", {"abs": 0.3})
    assert matches("numeric_tol", "42.7", "~44.5", {"abs": 2.5}) and matches("numeric_tol", 100, "114")
    assert matches("numeric", "31.8", "31.8") and not matches("numeric", "31.8", "31.9")


def test_key_normalisation():
    assert one(it(key="9a", kind="checkbox", field="checked", expected=True), [block(type="checkbox", key="9.a", checked=True)])
    assert not one(it(key="DIAUDIT", kind="checkbox", field="checked", expected=True), [block(type="checkbox", key="TIDAK DIAUDIT", checked=True)])
    table = block(type="table", key="Table 1 (continued)", columns=["", "A"], rows=[["r", "7"]])
    assert one(it(key="Table 1", kind="table_cell", field="cell", row="r", column="A", expected="7"), [table])
    table10 = block(type="table", key="Table 10", columns=["", "A"], rows=[["r", "7"]])
    assert not one(it(key="Table 1", kind="table_cell", field="cell", row="r", column="A", expected="7"), [table10])


def test_page_respected_and_null_page_means_any():
    blocks = [block(key="A", text="v", page=2)]
    assert not one(it(key="A", expected="v", page=1), blocks, page=2)
    assert one(it(key="A", expected="v", page=None), blocks, page=2)


def test_status_semantics():
    st = dict(kind="field", field="status")
    assert one(it(key="5", expected="missing", **st), [])
    assert one(it(key="5", expected="missing", **st), [block(key="5", text="", status="ok")])
    assert one(it(key="5", expected="missing", **st), [block(key="5", text="0", status="missing")])
    assert not one(it(key="5", expected="missing", **st), [block(key="5", text="0", status="ok")])
    assert one(it(key="K", expected="unreadable", **st), [block(key="K", status="unreadable")])
    assert not one(it(key="K", expected="unreadable", **st), [])


def test_text_without_key_searches_page_prose():
    blocks = [block(type="heading", key=None, text="A  Head   Mounted study"), block(type="table", key="T", text="other")]
    assert one(it(kind="text", key=None, expected="head mounted", match="contains"), blocks)
    assert not one(it(kind="text", key=None, expected="other", match="contains"), blocks)


def test_column_fallback_by_tokens_and_not_found():
    table = block(type="table", key="Table 3", columns=["Condition", "Error – Mexp."], rows=[["VH", "9"]])
    assert find_value(it(kind="table_cell", field="cell", key="Table 3", row="VH", column="Error - Mexp"), [page([table])]) == "9"
    assert find_value(it(kind="table_cell", field="cell", key="Table 3", row="ZZ", column="Error - Mexp"), [page([table])]) is None
    assert find_value(it(kind="table_cell", field="cell", key="Table 3", row="VH", column="Nope"), [page([table])]) is None


def test_table_row_chart_label_status_all_and_coverage():
    table = block(type="table", key="Table 2", columns=["", "A", "B"], rows=[["VV", "Verbal", "Vocal"]])
    assert one(it(kind="table_row", key="Table 2", row="VV", column=None, expected=["verbal", "vocal"], match="row_contains_all"), [table])
    chart = block(type="chart", key="Fig. 2", status="estimated", unit="seconds", columns=["Cond", "Time"], rows=[["VH", "~64"]])
    assert one(it(kind="chart_label", key="Fig. 2", expected="second", match="contains"), [chart])
    assert one(it(kind="status_all", key="Fig.*", page=None, expected="estimated", match="all_chart_blocks"), [chart])
    assert one(it(kind="coverage", key=None, page=None, expected=1, match="pages_with_result"), [])
    s = score({"items": [it(kind="chart_value", field="cell", key="Fig. 2", row="VH", column="Time", expected=60, match="numeric_tol", tol={"rel": 0.1})]},
              [page([chart])])
    assert s["kinds"] == {"chart": (1, 1)} and abs(s["chart_errors"][0] - 4 / 60) < 1e-9


def test_duplicate_key_picks_block_with_wanted_value():
    blocks = [block(type="checkbox", key="9", checked=True), block(key="9", text="Rp1.900.100")]
    assert one(it(key="9", expected=1900100, match="numeric"), blocks)
    assert one(it(key="9", kind="checkbox", field="checked", expected=True), blocks)

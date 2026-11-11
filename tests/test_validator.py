import pytest

from core.models import Block, PageResult
from core.validator import parse_expr, parse_number, validate


def block(**kw):
    base = dict(type="field", key="1", text="Rp100", page=1, excerpt="Rp100")
    return Block(**{**base, **kw})


def page(blocks, n=1, error=None):
    return PageResult(page=n, blocks=blocks, error=error, model="fake")


def test_parse_number():
    assert parse_number("Rp62.628.902") == 62628902
    assert parse_number("Rp0") == 0
    assert parse_number("xxx") is None


def test_parse_expr_and_rejects_code():
    assert parse_expr("6 - 7 - 8c") == [(1, "6"), (-1, "7"), (-1, "8c")]
    with pytest.raises(ValueError):
        parse_expr("__import__('os')")


def test_coverage_counts_failed_pages():
    rep = validate([page([], 1), page([], 2, error="boom")], 2, {})
    assert rep.coverage == 0.5
    assert any(i.severity == "error" and i.page == 2 for i in rep.issues)


def test_grounding_downgrades_ungrounded_excerpt():
    ok = block(key="a", excerpt="the quick brown fox")
    bad = block(key="b", excerpt="completely invented sentence here")
    rep = validate([page([ok, bad])], 1, {1: "intro. The quick brown fox jumps."})
    assert rep.grounded_rate == 0.5
    assert bad.status == "uncertain" and ok.status == "ok"


def test_no_text_layer_means_no_grounding():
    rep = validate([page([block()])], 1, {1: None})
    assert rep.grounded_rate is None


def test_empty_excerpt_table_shape_and_chart_label():
    t = block(type="table", columns=["A", "B"], rows=[["x", "1"], ["y"]])
    c = block(type="chart", key="Fig. 1", status="ok", columns=["C", "V"], rows=[["a", "~1"]])
    e = block(key="e", excerpt="  ")
    rep = validate([page([t, c, e])], 1, {1: None})
    msgs = " ".join(i.message for i in rep.issues)
    assert "do not have 2 cells" in msgs and "no supporting excerpt" in msgs
    assert c.status == "estimated"


CHECKS = [{"target": "3", "expr": "1 - 2"}]


def test_arithmetic_pass_and_fail():
    f = lambda k, v: block(key=k, text=v, excerpt=v)
    good = validate([page([f("1", "Rp100"), f("2", "Rp40"), f("3", "Rp60")])], 1, {}, CHECKS)
    assert good.checks_passed == "1/1"
    bad = validate([page([f("1", "Rp100"), f("2", "Rp40"), f("3", "Rp61")])], 1, {}, CHECKS)
    assert bad.checks_passed == "0/1" and any(i.severity == "error" for i in bad.issues)


def test_unreadable_input_skips_check():
    f = lambda k, v, s="ok": block(key=k, text=v, excerpt=v, status=s)
    rep = validate([page([f("1", "Rp100"), f("2", "xxx", "unreadable"), f("3", "Rp60")])], 1, {}, CHECKS)
    assert rep.checks_passed == "0/1" and all(i.severity != "error" for i in rep.issues)


def test_table_without_cells_is_flagged_not_ok():
    t = block(type="table", key="Table 1", columns=None, rows=None)
    rep = validate([page([t])], 1, {1: None})
    assert t.status == "uncertain"
    assert any("no data was extracted" in i.message for i in rep.issues)

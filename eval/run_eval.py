"""Scores saved outputs against a hand-checked gold file. Offline and deterministic: never calls a provider.

python -m eval.run_eval --gold eval/gold/tax_form.json --output outputs/<file>.json [--gold ... --output ...]
"""
import argparse
import json
import re
from pathlib import Path

from core.loaders import load_document
from core.models import PageResult
from core.profiles import load_profiles
from core.validator import parse_number, validate

ROOT = Path(__file__).resolve().parent.parent
TOLERANCE = 0.15
# Headline groups; the results table also lists every raw kind separately.
GROUPS = {"field": "field", "text": "field", "checkbox": "checkbox", "table_cell": "table_cell", "table_row": "table_cell",
          "chart": "chart", "chart_value": "chart", "chart_label": "chart", "status_all": "chart", "coverage": "coverage"}
LABELS = {"field": "Field accuracy", "checkbox": "Checkbox accuracy", "table_cell": "Table-cell accuracy",
          "chart": "Chart accuracy", "coverage": "Page coverage (gold)"}
DEFAULT_FIELD = {"checkbox": "checked", "table_cell": "cell", "table_row": "cell", "chart": "cell", "chart_value": "cell"}
STRICT_KEY_KINDS = {"field", "text", "checkbox"}  # form keys match exactly; table/figure keys match by prefix
MIME = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def flatten(items: list) -> list[dict]:
    return [j for i in items for j in (flatten(i) if isinstance(i, list) else [i])]


def is_verified(item: dict) -> bool:
    # Old skeleton items have no id/verified flag: there, a non-null expected means checked.
    verified = item.get("verified", "id" not in item)
    return bool(verified) and item.get("expected") is not None


def norm_key(s) -> str:
    return re.sub(r"[\s.]", "", str(s).lower())


def norm_value(s) -> str:
    s = re.sub(r"[\u2212\u2013\u2014]", "-", str(s).lower())
    return re.sub(r"[\s.,]", "", s)


def number(s) -> float | None:
    """parse_number treats '.' as a thousands separator; chart/table decimals like '31.8' must stay decimals."""
    s = re.sub(r"[~*%\s]", "", str(s).replace("\u2212", "-"))
    return float(s) if re.fullmatch(r"-?\d*\.\d{1,2}", s) else parse_number(s)


def key_matches(kind: str, wanted, block_key) -> bool:
    if wanted is None or block_key is None:
        return False
    w, k = norm_key(wanted), norm_key(block_key)
    if kind in STRICT_KEY_KINDS:
        return w == k
    # prefix match so "Table 1" finds "Table 1 (continued)", but not "Table 10"
    return k.startswith(w) and not k[len(w):][:1].isdigit()


def within_tol(expected, got, tol: dict | None) -> bool:
    e, g = number(expected), number(got)
    if e is None or g is None:
        return False
    tol = tol or {}
    if "abs" in tol:
        return abs(g - e) <= tol["abs"]
    return abs(g - e) <= tol.get("rel", TOLERANCE) * abs(e)


def matches(match: str, expected, got, tol: dict | None = None) -> bool:
    if got is None:
        return False
    if match == "all_chart_blocks":
        return bool(got) and all(s == expected for s in got)
    if match == "pages_with_result":
        return int(got) == int(expected)
    if match == "row_contains_all":
        return all(norm_value(x) in norm_value(got) for x in expected)
    if match == "numeric":
        return number(got) is not None and number(got) == number(expected)
    if match == "numeric_tol":
        return within_tol(expected, got, tol)
    if match == "contains":
        return " ".join(str(expected).lower().split()) in " ".join(str(got).lower().split())
    if match == "date":
        return re.findall(r"\d+", str(got)) == re.findall(r"\d+", str(expected)) != []
    if match == "normalized":
        e, g = norm_value(expected), norm_value(got)
        if len(re.sub(r"\D", "", e)) >= 10 and re.fullmatch(r"[\d-]+", e):  # NPWP-style ids: digits only
            e, g = re.sub(r"\D", "", e), re.sub(r"\D", "", g)
        return e == g
    return str(expected).strip().lower() == str(got).strip().lower()


def relative_error(expected, got) -> float | None:
    e, g = number(expected), number(got)
    if e is None or g is None or e == 0:
        return None
    return abs(g - e) / abs(e)


def find_blocks(item: dict, results: list[PageResult]) -> list:
    return [b for r in results for b in r.blocks
            if (not item.get("page") or b.page == item["page"]) and key_matches(item["kind"], item.get("key"), b.key)]


def cell_value(block, item: dict):
    """Row by first cell; column by equal header, else a header containing every word of the wanted column."""
    wanted = norm_key(item["row"])
    rows = [r for r in block.rows or [] if r and norm_key(r[0]) == wanted]
    if not rows:
        return None
    if not item.get("column"):
        return " ".join(rows[0])
    headers = block.columns or []
    col = next((i for i, h in enumerate(headers) if norm_key(h) == norm_key(item["column"])), None)
    if col is None:
        words = set(re.findall(r"\w+", item["column"].lower()))
        col = next((i for i, h in enumerate(headers) if words <= set(re.findall(r"\w+", h.lower()))), None)
    return rows[0][col] if col is not None and col < len(rows[0]) else None


def find_value(item: dict, results: list[PageResult]):
    """What the model extracted for this gold item; None if the block/row/column is absent."""
    kind = item["kind"]
    field = item.get("field") or DEFAULT_FIELD.get(kind, "text")
    page = item.get("page")
    if kind == "coverage":
        return len([r for r in results if not r.error])
    if kind == "status_all":
        return [b.status for r in results for b in r.blocks if b.type == "chart"]
    if kind == "text" and item.get("key") is None:
        texts = [b.text for r in results for b in r.blocks if b.type in ("heading", "paragraph") and b.text and (not page or b.page == page)]
        return " ".join(texts) or None
    blocks = find_blocks(item, results)
    if kind == "chart_label":
        parts = [str(x) for b in blocks for x in (b.label, b.text, b.unit, b.note, *(b.columns or [])) if x]
        return " ".join(parts) or None
    if field == "cell":
        return next((v for v in (cell_value(b, item) for b in blocks) if v is not None), None)
    if not blocks:
        return None
    if field == "status":
        return blocks[0].status
    # the model may emit two blocks with one key (a checkbox "9" and a field "9"): take the one that has the wanted value
    values = [b.checked if field == "checked" else b.text for b in blocks]
    return next((v for v in values if v is not None), None)


def check_item(item: dict, results: list[PageResult]) -> tuple[bool, object]:
    got = find_value(item, results)
    if item.get("field") == "status" and item["expected"] == "missing":
        # a blank line may simply not appear in the output, or appear with empty text
        block = next(iter(find_blocks(item, results)), None)
        return block is None or block.status == "missing" or not (block.text or "").strip(), got
    return matches(item["match"], item["expected"], got, item.get("tol")), got


def score(gold: dict, results: list[PageResult]) -> dict:
    items = flatten(gold["items"])
    scored = [i for i in items if is_verified(i)]
    out = {"items": len(items), "skipped": len(items) - len(scored), "pending": [i for i in items if not is_verified(i)],
           "kinds": {}, "raw_kinds": {}, "failed": [], "chart_errors": [], "chart_missing": 0}
    for i in scored:
        ok, got = check_item(i, results)
        for table, name in ((out["kinds"], GROUPS[i["kind"]]), (out["raw_kinds"], i["kind"])):
            hits, n = table.get(name, (0, 0))
            table[name] = (hits + ok, n + 1)
        if not ok:
            out["failed"].append({"id": i.get("id", "-"), "key": i.get("key"), "expected": i["expected"], "got": got})
        if i["kind"] in ("chart", "chart_value"):
            err = relative_error(i["expected"], got) if got is not None else None
            if got is None or number(got) is None:
                out["chart_missing"] += 1
            elif err is not None:
                out["chart_errors"].append(err)
    return out


def operational(results: list[PageResult]) -> dict:
    ok = [r for r in results if not r.error]
    return {
        "latency_per_page_s": sum(r.latency_ms for r in ok) / len(ok) / 1000 if ok else None,
        "tokens_in": sum(r.input_tokens or 0 for r in results),
        "tokens_out": sum(r.output_tokens or 0 for r in results),
        "retries": sum(max(r.attempts - 1, 0) for r in results),
        "failed_pages": len([r for r in results if r.error]),
    }


def find_source(output: Path) -> Path | None:
    stem = output.stem.split("__")[0]
    return next((p for p in (ROOT / "samples").glob(f"{stem}.*") if p.suffix.lower() in MIME), None)


def validation_metrics(output: Path, results: list[PageResult]) -> dict:
    """Re-run the validator offline: grounding needs the PDF text layers, so images get none."""
    profile = load_profiles().get(output.stem.partition("__")[2])
    layers: dict[int, str | None] = {}
    source = find_source(output)
    pages = max((r.page for r in results), default=0)
    if source:
        units = load_document(source.read_bytes(), MIME[source.suffix.lower()])
        layers, pages = {u.page_no: u.text_layer for u in units}, len(units)
    report = validate(results, pages, layers, profile.checks if profile else [])
    return {"coverage": report.coverage, "grounded": report.grounded_rate, "checks": report.checks_passed}


def load_results(output: Path) -> list[PageResult]:
    return [PageResult(**r) for r in json.loads(output.read_text())["results"]]


def fmt(v, spec="") -> str:
    return "n/a" if v is None else format(v, spec)


def cell(v, missing="") -> str:
    text = missing if v is None else str(v).replace("|", "/").replace("\n", " ")
    return text if len(text) <= 70 else text[:67] + "..."


def section(gold_path: Path, output: Path) -> str:
    gold = json.loads(gold_path.read_text())
    results = load_results(output)
    s, op, val = score(gold, results), operational(results), validation_metrics(output, load_results(output))
    rows = [("Gold items verified / pending", f"{s['items'] - s['skipped']} / {s['skipped']}")]
    for kind, label in LABELS.items():
        hits, n = s["kinds"].get(kind, (0, 0))
        rows.append((label, f"{hits}/{n} = {hits / n:.0%}" if n else "n/a (no verified items)"))
    errs = s["chart_errors"]
    if errs:
        chart = f"{sum(errs) / len(errs):.1%} over {len(errs)} values, {s['chart_missing']} missing"
    elif s["chart_missing"]:
        chart = f"n/a (all {s['chart_missing']} chart values missing from the output)"
    else:
        chart = "n/a (no verified items)"
    rows.append(("Chart value error (mean relative)", chart))
    rows += [
        ("Grounded-evidence rate", fmt(val["grounded"], ".0%")),
        ("Page coverage", f"{val['coverage']:.0%}"),
        ("Arithmetic checks passed", fmt(val["checks"])),
        ("Latency per page", f"{fmt(op['latency_per_page_s'], '.1f')} s"),
        ("Tokens (in / out)", f"{op['tokens_in']} / {op['tokens_out']}"),
        ("Retries", str(op["retries"])),
        ("Failed pages", str(op["failed_pages"])),
    ]
    status = gold.get("status", "UNVERIFIED")
    lines = [f"## {output.name} vs {gold_path.name} (gold status: {status})", "", "| Metric | Value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in rows]
    if s["raw_kinds"]:
        lines += ["", "Accuracy per gold kind:", "", "| Kind | Correct | Total |", "|---|---|---|"]
        lines += [f"| {k} | {h} | {n} |" for k, (h, n) in sorted(s["raw_kinds"].items())]
    if s["failed"]:
        lines += ["", "Failed items:", "", "| Id | Key | Expected | Got |", "|---|---|---|---|"]
        lines += [f"| {f['id']} | {f['key']} | {cell(f['expected'])} | {cell(f['got'], 'not found')} |" for f in s["failed"]]
    if s["pending"]:
        lines += ["", "Pending owner check (excluded from scores): " + ", ".join(
            f"{i.get('id', '-')} {i.get('key')} ({i['kind']})" for i in s["pending"])]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", action="append", required=True, type=Path)
    ap.add_argument("--output", action="append", required=True, type=Path)
    ap.add_argument("--results", type=Path, default=ROOT / "eval" / "results.md")
    args = ap.parse_args()
    if len(args.gold) != len(args.output):
        ap.error("give one --output per --gold")
    text = "# Evaluation results\n\n" + "\n\n".join(section(g, o) for g, o in zip(args.gold, args.output)) + "\n"
    args.results.write_text(text)
    print(text)


if __name__ == "__main__":
    main()

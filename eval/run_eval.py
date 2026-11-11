"""Scores saved outputs against a hand-checked gold file. Offline and deterministic: never calls a provider.

python -m eval.run_eval --gold eval/gold/tax_form.json --output outputs/<file>.json [--gold ... --output ...]
"""
import argparse
import json
from pathlib import Path

from core.loaders import load_document
from core.models import PageResult
from core.profiles import load_profiles
from core.validator import parse_number, validate

ROOT = Path(__file__).resolve().parent.parent
TOLERANCE = 0.15
KINDS = {"field": "Field accuracy", "checkbox": "Checkbox accuracy", "table_cell": "Table-cell accuracy"}
MIME = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def matches(match: str, expected, got) -> bool:
    if got is None:
        return False
    if match == "numeric":
        return parse_number(str(got)) == parse_number(str(expected))
    if match == "numeric_tol":
        return relative_error(expected, got) is not None and relative_error(expected, got) <= TOLERANCE
    if match == "contains":
        return str(expected).lower() in str(got).lower()
    return str(expected).strip().lower() == str(got).strip().lower()


def relative_error(expected, got) -> float | None:
    e, g = parse_number(str(expected)), parse_number(str(got).replace("~", ""))
    if e is None or g is None or e == 0:
        return None
    return abs(g - e) / abs(e)


def find_value(item: dict, results: list[PageResult]):
    """Return what the model extracted for this gold item, or None if the block/cell is absent."""
    for r in results:
        for b in r.blocks:
            if b.key != item["key"] or (item.get("page") and b.page != item["page"]):
                continue
            if item["field"] == "checked":
                return b.checked
            if item["field"] == "text":
                return b.text
            if b.columns and item.get("column") in b.columns:
                col = b.columns.index(item["column"])
                for row in b.rows or []:
                    if row and row[0].strip() == item["row"] and col < len(row):
                        return row[col]
    return None


def score(gold: dict, results: list[PageResult]) -> dict:
    items = gold["items"]
    scored = [i for i in items if i.get("expected") is not None]
    out = {"items": len(items), "skipped": len(items) - len(scored), "kinds": {}, "chart_errors": [], "chart_missing": 0}
    for kind in [*KINDS, "chart"]:
        done = [i for i in scored if i["kind"] == kind]
        if not done:
            continue
        hits = 0
        for i in done:
            got = find_value(i, results)
            ok = matches(i["match"], i["expected"], got)
            hits += ok
            if kind == "chart":
                err = relative_error(i["expected"], got) if got is not None else None
                if err is None:
                    out["chart_missing"] += 1
                else:
                    out["chart_errors"].append(err)
        out["kinds"][kind] = (hits, len(done))
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


def section(gold_path: Path, output: Path) -> str:
    gold = json.loads(gold_path.read_text())
    results = load_results(output)
    s, op, val = score(gold, results), operational(results), validation_metrics(output, load_results(output))
    rows = [("Gold items verified / pending", f"{s['items'] - s['skipped']} / {s['skipped']}")]
    for kind, label in KINDS.items():
        hits, n = s["kinds"].get(kind, (0, 0))
        rows.append((label, f"{hits}/{n} = {hits / n:.0%}" if n else "n/a (no verified items)"))
    errs = s["chart_errors"]
    rows.append(("Chart value error (mean relative)", f"{sum(errs) / len(errs):.1%} over {len(errs)} values, {s['chart_missing']} missing"
                 if errs or s["chart_missing"] else "n/a (no verified items)"))
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
    pending = [f"{i['key']} ({i['kind']})" for i in gold["items"] if i.get("expected") is None]
    if pending:
        lines += ["", "Pending owner check (excluded from scores): " + ", ".join(pending)]
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

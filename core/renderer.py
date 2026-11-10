"""Deterministic Markdown renderer: same results in, same text out. No LLM here."""
from core.models import Block, PageResult, ValidationReport

MARKERS = {"ok": "ok", "uncertain": "⚠️ uncertain", "unreadable": "❓ unreadable",
           "missing": "∅ missing", "estimated": "≈ estimated"}


def _cell(value: str | None) -> str:
    # a "|" or newline inside a value would break the Markdown table
    return (value or "").replace("|", "\\|").replace("\n", " ")


def _source(b: Block) -> str:
    where = " · ".join([f"p.{b.page}"] + ([b.region] if b.region else []))
    return f'📍 {where} · "{b.excerpt.strip()}"'


def _table(columns: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(_cell(c) for c in columns) + " |", "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join(_cell(c) for c in row) + " |" for row in rows]
    return lines


def _field_row(b: Block) -> str:
    status = MARKERS[b.status] + (f" ({b.note})" if b.note else "")
    return f"| {_cell(b.key)} | {_cell(b.label)} | {_cell(b.text) or '—'} | {_cell(status)} | {_cell(_source(b))} |"


def _block(b: Block) -> list[str]:
    """Everything except fields (those are rows of one table, see render_markdown)."""
    if b.type == "heading":
        return [f"### {b.text or b.label}", _source(b)]
    if b.type == "paragraph":
        return [b.text or "", "", _source(b)]
    if b.type == "checkbox":
        mark = "x" if b.checked else " "
        flag = "" if b.status == "ok" else f" {MARKERS[b.status]}"
        return [f"- [{mark}] {b.key or ''} {b.label or ''}{flag}".replace("  ", " "), f"  {_source(b)}"]

    # table or chart
    title = ": ".join(x for x in (b.key, b.label) if x)
    caption = f"**{title}**"
    if b.type == "chart":
        caption += " — ≈ values estimated from chart" + (f" (unit: {b.unit})" if b.unit else "")
    elif b.status != "ok":
        caption += f" {MARKERS[b.status]}"
    out = [caption, ""]
    out += _table(b.columns, b.rows or []) if b.columns else ["_No table data was extracted._"]
    if b.note:
        out += ["", f"_{b.note}_"]
    return out + ["", _source(b)]


def render_markdown(results: list[PageResult], report: ValidationReport | None = None,
                    run_info: dict | None = None) -> str:
    lines = ["# Extraction result", ""]
    for r in sorted(results, key=lambda r: r.page):
        lines += [f"## Page {r.page}", ""]
        if r.error:
            lines += [f"> ❌ **This page failed:** {r.error}", ""]
            continue
        in_fields = False  # consecutive fields share one table, in reading order
        for b in r.blocks:
            if b.type == "field":
                if not in_fields:
                    lines += ["| Line | Field | Value | Status | Source |", "|---|---|---|---|---|"]
                    in_fields = True
                lines.append(_field_row(b))
            else:
                if in_fields:
                    lines.append("")
                    in_fields = False
                lines += _block(b) + [""]
        if in_fields:
            lines.append("")
    if report and report.issues:
        lines += ["## Validation issues", ""]
        lines += [f"- **{i.severity}** (p.{i.page}, {i.key or '-'}): {i.message}" for i in report.issues] + [""]
    if run_info:
        lines += ["## Run info", ""] + [f"- {k}: {v}" for k, v in run_info.items()] + [""]
    return "\n".join(lines)

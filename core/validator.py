"""Checks on the extraction result. No LLM and no domain words: domain rules come from the profile's `checks`."""
import re

from rapidfuzz import fuzz

from core.models import Block, Issue, PageResult, ValidationReport

GROUNDING_THRESHOLD = 85


def parse_number(text: str | None) -> float | None:
    """'Rp62.628.902' -> 62628902. Dots/commas are treated as thousands separators (Indonesian style)."""
    if not text:
        return None
    digits = re.sub(r"[^\d\-]", "", text.replace("(", "-").replace(")", ""))
    return float(digits) if re.fullmatch(r"-?\d+", digits) else None


def parse_expr(expr: str) -> list[tuple[int, str]]:
    """'6 - 7 - 8c' -> [(+1,'6'), (-1,'7'), (-1,'8c')]. Only keys joined by + or -, so there is nothing to eval."""
    tokens = re.findall(r"[+-]|[\w.]+", expr)
    terms, sign = [], 1
    for i, tok in enumerate(tokens):
        if tok in "+-":
            sign = 1 if tok == "+" else -1
        else:
            terms.append((sign, tok))
            sign = 1
    if not terms or re.sub(r"[\w.\s+-]", "", expr):
        raise ValueError(f"unsupported expression: {expr!r}")
    return terms


def validate(results: list[PageResult], expected_pages: int, text_layers: dict[int, str | None],
             checks: list[dict[str, str]] = []) -> ValidationReport:
    issues: list[Issue] = []

    got = {r.page for r in results if not r.error}
    for r in results:
        if r.error:
            issues.append(Issue(severity="error", page=r.page, message=f"Page failed: {r.error}"))
    coverage = len(got) / expected_pages if expected_pages else 0.0

    grounded = checked = 0
    for r in results:
        for b in r.blocks:
            if not b.excerpt.strip():
                issues.append(Issue(severity="warning", page=b.page, key=b.key, message="Block has no supporting excerpt."))
            elif (layer := text_layers.get(b.page)):
                # image inputs have no text layer, so only PDF blocks are grounded
                checked += 1
                if fuzz.partial_ratio(_norm(b.excerpt), _norm(layer)) >= GROUNDING_THRESHOLD:
                    grounded += 1
                else:
                    _downgrade(b)
                    issues.append(Issue(severity="warning", page=b.page, key=b.key,
                                        message="Excerpt not found in the page text layer; marked uncertain."))
            if b.type == "table" and b.columns:
                bad = [i for i, row in enumerate(b.rows or []) if len(row) != len(b.columns)]
                if bad:
                    issues.append(Issue(severity="warning", page=b.page, key=b.key,
                                        message=f"Table rows {bad} do not have {len(b.columns)} cells."))
            if b.type == "chart" and b.status != "estimated":
                b.status = "estimated"  # values read off a chart are never exact
                issues.append(Issue(severity="info", page=b.page, key=b.key, message="Chart status forced to 'estimated'."))

    passed, total = _run_checks(results, checks, issues)
    return ValidationReport(
        issues=issues,
        grounded_rate=grounded / checked if checked else None,
        coverage=coverage,
        checks_passed=f"{passed}/{total}" if total else None,
    )


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def _downgrade(b: Block) -> None:
    if b.status == "ok":
        b.status = "uncertain"
        b.note = b.note or "excerpt not found in the text layer"


def _run_checks(results: list[PageResult], checks: list[dict[str, str]], issues: list[Issue]) -> tuple[int, int]:
    by_key: dict[str, Block] = {}
    for r in results:
        for b in r.blocks:
            if b.key and b.type == "field":
                by_key.setdefault(b.key, b)

    def value(key: str) -> float | None:
        b = by_key.get(key)
        return parse_number(b.text) if b and b.status in ("ok", "uncertain") else None

    passed = total = 0
    for check in checks:
        target, expr = check["target"], check["expr"]
        total += 1
        try:
            terms = parse_expr(expr)
        except ValueError as e:
            issues.append(Issue(severity="error", key=target, message=str(e)))
            continue
        want, parts = value(target), [value(k) for _, k in terms]
        if want is None or None in parts:
            # an unreadable input is not a pass, but not a contradiction either
            issues.append(Issue(severity="info", key=target, message=f"Check {target} = {expr} skipped: a value is missing or unreadable."))
            continue
        got = sum(s * p for (s, _), p in zip(terms, parts))
        if got == want:
            passed += 1
        else:
            issues.append(Issue(severity="error", page=by_key[target].page, key=target,
                                message=f"Check failed: {target} = {expr} gives {got:,.0f}, but the form says {want:,.0f}."))
    return passed, total

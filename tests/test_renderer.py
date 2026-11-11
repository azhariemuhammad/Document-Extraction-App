from core.models import Block, PageResult
from core.renderer import render_markdown


def test_renderer_output_is_stable():
    blocks = [
        Block(type="field", key="1", label="Net income", text="Rp100", page=1, excerpt="1 Net income Rp100"),
        Block(type="field", key="2", label="Phone", text="xxx", status="unreadable", note="masked", page=1, excerpt="xxx"),
        Block(type="checkbox", key="9.a", label="Underpaid", checked=True, page=1, excerpt="9.a"),
        Block(type="chart", key="Fig. 1", label="Task time", unit="s", columns=["Condition", "Time"],
              rows=[["VH", "~45"]], status="estimated", page=1, region="Fig. 1", excerpt="Fig. 1"),
        Block(type="table", key="Table 1", status="uncertain", page=1, excerpt="Table 1"),
    ]
    md = render_markdown([PageResult(page=1, blocks=blocks, model="fake")])
    assert md == """# Extraction result

## Page 1

| Line | Field | Value | Status | Source |
|---|---|---|---|---|
| 1 | Net income | Rp100 | ok | 📍 p.1 · "1 Net income Rp100" |
| 2 | Phone | xxx | ❓ unreadable (masked) | 📍 p.1 · "xxx" |

- [x] 9.a Underpaid
  📍 p.1 · "9.a"

**Fig. 1: Task time** — ≈ values estimated from chart (unit: s)

| Condition | Time |
|---|---|
| VH | ~45 |

📍 p.1 · Fig. 1 · "Fig. 1"

**Table 1** ⚠️ uncertain

_No table data was extracted._

📍 p.1 · "Table 1"
"""

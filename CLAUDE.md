# Configurable Document Extraction App (Senior AI Engineer take-home)

Owner: senior full-stack engineer, new to AI engineering. **Deadline: tomorrow.** They must explain every design
decision in a video, so: simple readable code, short comments for non-obvious choices, **no frameworks**
(no LangChain, no agent frameworks, no vector DBs; this is extraction, not RAG).

Work in the build order below. **After each block, stop** and say how to run/verify it.
Agents live in `.claude/agents/`, skills in `.claude/skills/` (adapted from the Astroslide project).

## The brief (summary)
Local, model-agnostic app: document + user-defined instructions -> readable **Markdown with source references**.
New domains, file formats and providers must be addable independently.

- **Inputs:** PDF and PNG/JPG. Process the full 18-page PDF; document unreadable content / limits.
- **Output:** prose, tables, charts, form fields, checkboxes. Keep table hierarchy, chart labels/values/units.
  **Demonstrate two extraction instructions without changing code.**
- **Model independence:** provider chosen by config + shared interface. One live (Gemini) + one runnable **fake**
  adapter (tests integration, not accuracy). README: how to add a provider, handle capability differences.
- **Evidence & uncertainty:** page/region refs with excerpts. Mark missing/unreadable/uncertain. Label chart estimates.
- **Reliability:** check completeness + formatting; provider failures and unsupported inputs **visible**;
  record model, runtime, tokens. Provider logic separate from extraction and validation.
- **Evaluation:** justified metrics (quality + operational) on both files vs a **small hand-checked gold set**.
  Model confidence alone is not enough. Results table in README.
- **UI:** upload, editable instructions, run, rendered Markdown, source refs, visible errors, `.md` download.
- **Submission:** GitHub repo: source, Dockerfile(s), Compose, `.env.example`, sample outputs, tests.
  `docker compose up --build` starts everything, no host deps beyond Docker. Keys in gitignored `.env`.
  README: setup, architecture, extension points, AI tools used, validation, limitations, next steps, local URL.
- **Grading:** extraction accuracy & evidence 35% · modularity 25% · reliability & validation 20% ·
  usability & judgment 20%. "Prioritize a working submission and clearly stated limitations."

## Sample file facts (tests, gold set, prompts)
**Research PDF**: Applied Ergonomics 98 (2022) 103597, AR maintenance study. 18 pages, real text layer,
two-column. Table 1 spans pages ("Table 1 (continued)"). Tables 2-6. Figs. 2-6 bar charts (task time, errors,
workload, eye-gaze) with `*p < 0.05` markers; Fig. 1 screenshot with labelled AOIs.

**Tax form image**: Indonesian corporate income tax return SPT 1771, tax year 2021, low-res scan.
Known values (**verify visually before using as gold**):
- 1 Penghasilan Neto Fiskal Rp62.628.902 · 2 Kompensasi Kerugian Rp20.000.000
- 3 PKP (1-2) Rp42.628.902 · 4 PPh Terutang Rp2.500.100 (checkbox 3.c "Tarif PPh Ps. 31E" ticked)
- 6 (4+5) Rp2.500.100 · 7 Rp0 · 8a Rp600.000 · 8b Rp0 · 8c (8a+8b) Rp600.000
- 9 (6-7-8c) Rp1.900.100, checkbox 9.a ticked · 11 (9-10c) Rp1.900.100, checkbox 11.a ticked
- "TIDAK DIAUDIT" ticked · date 30-04-2022 · period 2020 s.d. 2021
- Masked values (KLU `xx xx xx`, phone `xxx-xxxxxxx`) -> `unreadable`, never invented.
- The form's own formulas hold -> use as arithmetic validation checks.

## Architecture
```
Upload -> Loader (by MIME) -> [PageUnit] -> Extractor (per page; retry, cache, repair) -> Provider -> LLM
       -> [Block] + run metadata -> Validator -> ValidationReport -> Renderer -> Markdown -> UI / .md / eval
```
**Boundary rules (hard):** only `core/providers/` imports vendor SDKs · only `core/loaders/` knows file formats ·
only `profiles/` knows document domains. Extractor/validator/renderer know none of them.

### Data model (`core/models.py`, Pydantic)
```python
class PageUnit(BaseModel):
    page_no: int            # 1-based
    image_png: bytes
    text_layer: str | None  # None for images
    width: int; height: int

class Block(BaseModel):     # flat on purpose: Gemini schema mode handles flat optional fields better than unions
    type: Literal["heading","paragraph","table","chart","field","checkbox"]
    key: str | None         # stable id: form line ("9", "8a") or "Table 2" / "Fig. 3"
    label: str | None
    text: str | None        # paragraph/heading text, or field value
    columns: list[str] | None
    rows: list[list[str]] | None   # first cell = row label
    unit: str | None
    checked: bool | None
    status: Literal["ok","uncertain","unreadable","missing","estimated"]
    page: int
    region: str | None
    excerpt: str            # verbatim supporting text
    note: str | None        # reason for non-ok status

class PageResult(BaseModel):
    page: int; blocks: list[Block]; error: str | None
    model: str; latency_ms: int; input_tokens: int | None; output_tokens: int | None
    cached: bool; attempts: int
```
Charts reuse `columns`/`rows` (`["Condition","Time (s)"]`, `[["VH","~45"]]`) with `status="estimated"`.

### Interfaces
```python
# core/loaders/base.py
class DocumentLoader(ABC): mime_types: set[str]; def load(self, data: bytes) -> list[PageUnit]
LOADERS = {"application/pdf": PdfLoader(), "image/png": ImageLoader(), "image/jpeg": ImageLoader()}
# unknown MIME -> UnsupportedInputError, shown in UI

# core/providers/base.py
@dataclass
class Capabilities: images: bool; native_json_schema: bool; max_images_per_call: int
class ProviderError(Exception): retryable: bool   # 429/5xx retryable; 400/401 not
class ModelProvider(ABC): name; model; capabilities; def generate(prompt, images, schema) -> GenerateResponse
# GenerateResponse(text, model, input_tokens, output_tokens, latency_ms)
PROVIDERS = {"gemini": GeminiProvider, "fake": FakeProvider}   # LLM_PROVIDER env
```
If `native_json_schema` is False the extractor embeds the schema in the prompt and relies on the repair retry.

- **PdfLoader:** PyMuPDF (`import pymupdf`): `page.get_text()` + `page.get_pixmap(dpi=RENDER_DPI).tobytes("png")`.
- **ImageLoader:** Pillow; reject corrupt, `ImageOps.exif_transpose`, PNG/JPEG only, re-encode PNG, one PageUnit, `text_layer=None`.
- **FakeProvider:** canned valid JSON (one `uncertain`, one `estimated` block) + fake usage; configurable to raise a retryable error once.
- **GeminiProvider:** `google-genai`, image parts + JSON schema; map SDK errors -> ProviderError; usage from response
  metadata; model from `GEMINI_MODEL` (check AI Studio for current free-tier models/limits).

### Profiles (`profiles/*.yaml`, no code)
```yaml
id: tax_form_fields
name: "Tax form - all fields"
instruction: |
  Extract every form field and checkbox. Use the printed line number as `key` (e.g. "1", "8a").
  Masked values such as "xxx" must have status "unreadable".
checks:
  - {target: "3",  expr: "1 - 2"}
  - {target: "8c", expr: "8a + 8b"}
  - {target: "9",  expr: "6 - 7 - 8c"}
  - {target: "11", expr: "9 - 10c"}
```
Four profiles: `full_document`, `research_results` (conditions, metrics, tables, charts only), `tax_form_fields`,
`tax_summary` (income, taxable income, tax due, underpayment, filing date). Evaluate `expr` safely (parse +/- of
keys; **no `eval`**). Normalize "Rp62.628.902" -> 62628902.

### Extractor (`core/extractor.py`), per page
1. cache key = sha256(file bytes + page_no + instruction + model + PROMPT_VERSION); JSON files in `/data/cache`.
2. prompt = SYSTEM_RULES (fixed, app-owned) + profile instruction (user-editable) + text layer hint if present.
3. call provider; exponential backoff on retryable errors (max 4 attempts); record attempts.
4. parse into `list[Block]`; on failure ONE repair call including the validation error.
5. still failing -> `PageResult(error=...)`; continue other pages. **Never crash the run.**
Sequential pages (free-tier limits). Emit progress for the UI.

### Validator (`core/validator.py`, no LLM)
| Check | Rule | Action |
|---|---|---|
| Coverage | every page has a PageResult | issue per failed page |
| Grounding (PDF only) | `rapidfuzz.fuzz.partial_ratio(excerpt, text_layer) >= 85` | status -> uncertain + issue |
| Empty evidence | blank excerpt | issue |
| Table shape | each row length == len(columns) | issue |
| Chart labelling | chart blocks must be `estimated` | force + issue |
| Profile checks | evaluate `checks` by `key` | issue on mismatch |
Returns `ValidationReport(issues=[{severity,page,key,message}], grounded_rate, coverage, checks_passed)`.

### Renderer (`core/renderer.py`, deterministic)
`## Page N`; tables with row-label first column; charts as tables captioned "≈ values estimated from chart";
fields as `Field | Value | Status | Source`; checkboxes `[x]`/`[ ]`; markers ⚠️ uncertain, ❓ unreadable, ∅ missing;
under each block `📍 p.N · region · "excerpt"`. Append "Validation issues" and "Run info" (provider, model,
total time, tokens, cache hits, failed pages).

### UI (`app/ui.py`, Streamlit, single container)
Sidebar: upload, profile dropdown (pre-fills editable instruction), Run. Tabs: Result | Sources | Issues | Run info.
Download .md. All errors via `st.error`.

### Evaluation (`eval/`)
`eval/gold/{tax_form,research_pdf}.json`, ~10-15 hand-checked items each:
`{"key": "9", "field": "text", "expected": "1900100", "match": "numeric"}`; match types `exact`, `numeric`,
`numeric_tol` (charts, ±15%), `contains`. `eval/run_eval.py` scores saved outputs -> `eval/results.md`: field /
checkbox / table-cell accuracy, chart value error, grounded-evidence rate, page coverage, arithmetic checks passed,
latency/page, tokens, retries, failures.

### Repo layout
```
app/ui.py
core/models.py core/extractor.py core/validator.py core/renderer.py core/prompts.py
core/loaders/{base,pdf,image}.py   core/providers/{base,gemini,fake}.py
profiles/*.yaml   eval/gold/*.json eval/run_eval.py eval/results.md
samples/ outputs/ tests/   Dockerfile docker-compose.yml .env.example .gitignore README.md
```
`.env.example`: `LLM_PROVIDER=gemini`, `GEMINI_API_KEY=`, `GEMINI_MODEL=`, `RENDER_DPI=150`.
Compose: one service, port 8501, `env_file: .env`, volumes for `/data/cache` and `outputs/`.

### Tests (pytest, all with FakeProvider, no API key)
loaders (PDF = 18 pages, image -> 1 page, bad file rejected) · end-to-end with fake · retry on retryable error ·
validator (grounding, table shape, arithmetic) · renderer snapshot.

## Build order (stop after each block for the owner to verify)
1. models, base interfaces, FakeProvider, PdfLoader/ImageLoader, renderer, Streamlit UI, Dockerfile + compose.
   Done when `docker compose up --build` renders fake Markdown at http://localhost:8501.
2. GeminiProvider + tax form end-to-end. **Leave `core/prompts.py` SYSTEM_RULES as a draft for the owner to refine.**
3. Full PDF page-by-page with retry, cache, repair; save outputs to `outputs/`.
4. Validator + four profiles; issues in UI.
5. Gold sets (owner verifies by hand) + eval script + results table.
6. Tests, README (setup, architecture diagram, extension points: loader / provider / profile, capability
   differences, quota handling, metrics + results, limitations, next steps, AI tools used).

## Known limitations to state (scope cuts)
No bounding boxes (page + textual region only). Multi-page tables not auto-merged. No OCR cross-check for images
(grounding is PDF-only; images rely on arithmetic checks). One live provider. Chart values are visual estimates.
Free-tier quota limits runs (mitigated by caching). PyMuPDF is AGPL: fine here, needs review commercially.

## Draft SYSTEM_RULES (`core/prompts.py`) - owner will refine
```
You extract information from ONE page of a document. You receive the page image and, when available,
the page's text layer (may have broken column order; use the image for layout, the text for exact wording).

Follow the user's extraction instruction for WHAT to extract. These rules always apply:
1. Return only JSON matching the schema: a list of blocks.
2. Every block needs `excerpt`: text copied verbatim from the page that supports it. Never paraphrase.
3. Never guess. If a value is masked, illegible or cut off -> status "unreadable" and explain in `note`.
   If an expected value is absent -> status "missing". If you are unsure -> status "uncertain".
4. Tables: put headers in `columns`; first cell of each row is its row label; keep empty cells as "".
   If a table continues from/onto another page, say so in `note`.
5. Charts: give title, axis labels and units; values read from bars/lines are approximate -> status
   "estimated" and prefix values with "~". Include significance markers (e.g. "*") if shown.
6. Forms: one `field` block per field (label, value, key = printed line number). One `checkbox` block per
   checkbox with `checked` true/false. Keep numbers exactly as printed (e.g. "Rp1.900.100").
7. `page` = the page number given to you. `region` = a short location (section name, line number, figure).
```

## Working rules for agents and skills
- **Never invent gold values or sample content.** Gold items come from the owner's hand check; sample files are
  attached by the owner. If a file is missing, say so.
- **Prompt changes bump `PROMPT_VERSION`** (cache key depends on it). Don't touch `SYSTEM_RULES` after block 2
  without the owner's say-so; it is theirs to refine.
- **No `eval()`, no new dependencies** beyond: pymupdf, pillow, pydantic, pyyaml, rapidfuzz, google-genai,
  streamlit, pytest. Anything else needs the owner's OK.
- **Visible failures:** never swallow errors; they surface as `PageResult.error`, an issue, or `st.error`.
- Commit one block/step at a time. Don't push to other branches, open PRs, or commit `.env` / API keys.

## Agents (`.claude/agents/`)
| agent | owns |
|---|---|
| `core-implementer` | `core/`, `profiles/`, Dockerfile, compose: loaders, providers, extractor, validator, renderer |
| `ui-implementer` | `app/ui.py` (Streamlit) |
| `eval-implementer` | `eval/`, tests, metrics. Reports numbers, never invents gold |

## Skills (`.claude/skills/`)
- `build-block`: run the next numbered block, stop, hand over how to verify
- `add-extension`: add a provider, loader or profile touching only its own folder
- `extraction-change`: checklist before committing prompt/extractor/validator/renderer changes
- `submit-check`: final review (repo, secrets, tests, Docker, eval, README) scored against the rubric

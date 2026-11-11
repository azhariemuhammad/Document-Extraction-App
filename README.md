# Configurable Document Extraction App

Upload a PDF or a PNG/JPG, write (or pick) an extraction instruction, and get readable **Markdown with source
references** for every extracted item. Runs locally; the model provider is chosen by configuration.

- Handles prose, tables (row labels kept), charts (labelled as estimates), form fields and checkboxes.
- Every item carries `page · region · "verbatim excerpt"` and a status: ok, uncertain, unreadable, missing, estimated.
- Provider failures, unsupported files and failed pages are shown, never hidden.

## Run it

Needs only Docker.

```bash
cp .env.example .env        # then edit it, see below
docker compose up --build
```

Open **http://localhost:8501**.

`.env`:

| Variable | Meaning |
|---|---|
| `LLM_PROVIDER` | `gemini` (live) or `fake` (no key, tests the wiring only) |
| `GEMINI_API_KEY` | your Google AI Studio key (`.env` is gitignored) |
| `GEMINI_MODEL` | model name, no default: the app fails visibly if it is unset |
| `RENDER_DPI` | PDF page render resolution, default 150 |

Use: upload a file, pick a profile (it fills the editable instruction), press **Run extraction**. Tabs:
Result, Sources, Issues, Run info. The document sits beside the result; **Download .md** saves the output.
Each run also writes `outputs/<file>__<profile>.md` and `.json`.

Without Docker (CLI and tests): `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`,
then `python -m pytest -q`, or `python -m core.cli samples/<file> --profile <id>` (export the `.env` values first).

## Architecture

```
Upload -> Loader (by MIME) -> [PageUnit] -> Extractor (per page: cache, retry, repair) -> Provider -> LLM
       -> [Block] + run metadata -> Validator -> ValidationReport -> Renderer -> Markdown -> UI / .md / eval
```

| Module | Job |
|---|---|
| `core/loaders/` | Only code that knows file formats. PDF: PyMuPDF page image + text layer. Image: Pillow, validated and re-encoded. |
| `core/providers/` | Only code that imports a vendor SDK. `gemini`, `fake`. |
| `core/extractor.py` | One page at a time: cache lookup, provider call, retry with backoff, one repair call on bad JSON. A failed page becomes a `PageResult.error`; the run continues. |
| `core/validator.py` | No LLM. Coverage, grounding, table shape, chart labelling, empty tables, profile arithmetic. |
| `core/renderer.py` | Deterministic Markdown. |
| `profiles/*.yaml` | Only place that knows document domains: an instruction plus optional arithmetic `checks`. |
| `app/ui.py` | Streamlit UI. `core/pipeline.py` is the one entry point shared by UI and CLI. |

The unit of output is a flat `Block` (`core/models.py`): heading, paragraph, table, chart, field or checkbox,
with `key`, `page`, `region`, `excerpt`, `status`, `note`. It is flat on purpose: schema-constrained generation
copes better with one shape of optional fields than with unions.

### Reliability

- **Retry:** 429, 5xx and network errors are retried with exponential backoff (max 4 attempts). 400/401/403 are not.
- **Repair:** invalid JSON gets one repair call that includes the parse error. Still invalid -> the page fails visibly.
- **Cache:** one JSON file per page, keyed by sha256 of file bytes + page + instruction + model + prompt version.
  Failures are never cached, so pressing Run again retries only the failed pages. In Docker the cache is a named volume.
- **Quota:** pages run one after another (free-tier rate limits); the cache means a re-run costs nothing for finished pages.
- **Run info:** provider, model, total time, tokens, provider calls, cache hits, failed pages.

### Validation (no LLM)

| Check | Action |
|---|---|
| Coverage | Issue per failed page; coverage rate |
| Grounding (PDF only) | Excerpt must fuzzy-match the page text layer (`rapidfuzz` >= 85) else status -> uncertain |
| Empty evidence / table shape | Issue |
| Table or chart with no data | Status -> uncertain + issue (the model sometimes names a table and gives no cells) |
| Chart labelling | Forced to `estimated` |
| Profile arithmetic | `checks` in the profile, e.g. `9 = 6 - 7 - 8c`; parsed as +/- of keys, no `eval` |

An `ok` status is the model's own claim. Independent evidence is grounding (PDF), the arithmetic checks and the gold set.

## Two instructions, no code changes

Profiles are YAML. Four ship: `full_document`, `research_results`, `tax_form_fields`, `tax_summary`.
Run the same tax form with `tax_form_fields` (every field and checkbox, with arithmetic checks) and `tax_summary`
(only income, taxable income, tax due, filing date), or edit the instruction text in the UI.

## Extension points

Each is added in its own place; nothing else changes.

- **Profile (new domain):** add `profiles/<id>.yaml` with `id`, `name`, `instruction`, optional `checks`.
- **Loader (new format):** add a class in `core/loaders/` with `mime_types` and `load(data) -> list[PageUnit]`, register it in `LOADERS`.
- **Provider (new model):** add `core/providers/<name>.py` implementing `ModelProvider.generate(prompt, images, schema)`,
  declare its `Capabilities`, map vendor errors to `ProviderError(retryable=...)`, add it to `PROVIDERS`, and set
  `LLM_PROVIDER=<name>`. Vendor SDK imports stay in that file.

### Capability differences

Each provider declares `Capabilities(images, native_json_schema, max_images_per_call)`.

- No native JSON schema: the extractor puts the schema in the prompt and relies on the repair retry. (Implemented.)
- No image input (a text-only model): **not implemented yet.** The extractor always sends the page image. The
  intended handling is to send only the text layer for PDFs and fail visibly for images, which have no text layer.

The `fake` provider returns canned JSON (including `uncertain` and `estimated` blocks) and can raise a retryable
error once. It tests integration, **not extraction accuracy**.

## Evaluation

`eval/gold/*.json` hold hand-checked items (`key`, `expected`, `match`: exact, numeric, numeric_tol, contains).
`python -m eval.run_eval --gold <gold.json> --output <outputs/file.json>` scores a saved run offline and writes
`eval/results.md`. Metrics:

- **Quality:** field, checkbox and table-cell accuracy; chart value error (within +-15%); grounded-evidence rate;
  arithmetic checks passed; page coverage. Model confidence alone is not used.
- **Operational:** latency per page, tokens, retries, failed pages.

Chart gold items that could not be read with confidence are marked `verified: false`. The scorer lists them as
pending and does not count them, so the chart value error is reported only over the items that were verified.

### Results

Baseline, scored offline by `eval/run_eval.py` against hand-verified gold items (`eval/results.md` has the full
output, including every failed item). Both runs used `gemini-3.1-flash-lite`. The research run is an earlier saved
output (`full_document` profile) made before the empty-table check was added, so treat it as a first baseline.

| Metric | Tax form image (`tax_form_fields`) | Research PDF, 18 pages (`full_document`) |
|---|---|---|
| Gold items verified / left pending | 32 / 0 | 26 / 11 (unverified chart items) |
| Field accuracy | 18/21 (86%) | 0/3 (title, author and a number sit in `excerpt`, not `text`) |
| Checkbox accuracy | 2/11 (18%) | n/a |
| Table-cell accuracy | n/a | 8/17 (47%) |
| Chart values | n/a | 0/6 (the charts came back without values) |
| Grounded-evidence rate | n/a (image) | 97% |
| Arithmetic checks passed | 3/4 | n/a |
| Page coverage | 100% | 100% |
| Latency per page | 5.9 s | 31.1 s |
| Tokens in / out | 1,500 / 2,126 | 61,132 / 34,880 |
| Retries / failed pages | 0 / 0 | 7 / 0 |

How to read it:

- **Checkboxes:** the model reports only the ticked boxes. Gold unticked boxes that are absent from the output count as
  wrong, so the score is strict. Wrong keys are counted too (for example the line 9 checkbox keyed `9`, not `9a`).
- **Tax fields:** the 3 misses are two fields the model skipped (TAHUN PAJAK, KLU) and line 11 keyed as `11a`, which also makes one
  arithmetic check (11 = 9 - 10c) fail.
- **PDF tables:** every miss is a table the model named but returned without columns or rows (Tables 1, 2, 3, 7).
  The validator now flags these as `uncertain`; they are not yet recovered automatically.
- **Grounding:** 97% of PDF excerpts were found in the page text layer.
- The sets are small (a sample, not a benchmark), and the accuracy figures are not a claim about other documents.

## Limitations

- No bounding boxes: references are page + textual region + excerpt. (Next step: for PDFs, locate the excerpt with PyMuPDF.)
- Tables spanning pages are extracted per page and not merged.
- Grounding works only for PDFs. Images have no text layer, so they rely on the profile arithmetic checks.
- The model sometimes returns a table title without cells; this is flagged as uncertain but not recovered automatically.
- Chart values are visual estimates, labelled as such. Many charts show ranges (box plots, error bars), so there is no
  single "true" value to read, and a hand-read gold value would itself be an estimate. The gold set therefore covers
  chart values only where a bar is clearly readable, and the remaining chart items are left unverified and excluded
  from the scores. Charts are otherwise judged on structure (title, axis labels, units, conditions, significance
  markers, `estimated` status), not on exact numbers.
- One live provider. A text-only provider needs the extractor change described above.
- Speed and quota depend on the chosen model; some models spend minutes per page. The cache and the visible log help.
- Accuracy is measured on two sample files only; other documents work through profiles/instructions but are unmeasured.
- PyMuPDF is AGPL: fine for this take-home, needs a licence review for commercial use.

## Next steps

PDF bounding-box highlighting; automatic repair of empty tables; merging multi-page tables; a text-only provider
with the capability handling above; a retry button for failed pages; a larger gold set.

## AI tools used

Built with Claude Code (Claude Sonnet) using project agents and skills in `.claude/`, with the owner reviewing every
step. The live extraction model is Google Gemini via `google-genai`. The gold values are hand-checked by the owner,
not model-generated.

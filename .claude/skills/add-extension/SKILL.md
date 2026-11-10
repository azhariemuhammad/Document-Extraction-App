---
name: add-extension
description: Add a new model provider, input file loader, or extraction profile without touching the rest of the code. Use when asked to "support X model/provider", "support X files", "add a profile / extract X from Y documents", or to demonstrate an extension point.
argument-hint: "<provider|loader|profile> <name>"
allowed-tools: Bash(grep:*), Bash(file:*), Bash(python -m pytest:*), Read, Edit, Write(core/providers/*), Write(core/loaders/*), Write(profiles/*), Write(tests/*)
---

Request: `$ARGUMENTS`. Goal: **only the one extension folder changes**, plus its registry line, requirements/`.env.example` and a README note. If the extractor, validator or renderer needs editing, stop and tell the owner: the interface is wrong.

## Provider (`core/providers/`)
- Subclass `ModelProvider`; set `name`, `model` (from env, fail visibly if unset), `capabilities`. Vendor SDK imported **only in this file**.
- Capabilities honestly: `images`, `native_json_schema` (False -> extractor embeds the schema in the prompt and relies on the repair retry), `max_images_per_call`. Text-only model: fail visibly, never send blank images.
- Map errors: 429/5xx/timeout -> `ProviderError(retryable=True)`; 400/401/403, bad key, unknown model, safety block -> `retryable=False` with an actionable message.
- Fill `input_tokens`/`output_tokens` from the response (`None` if not reported, never estimate); measure `latency_ms`.
- Register in `PROVIDERS`; add `X_API_KEY=`/`X_MODEL=` (empty) to `.env.example`; add the SDK to `requirements.txt`.
- Tests with a mocked client: success, retryable error, non-retryable error, usage mapping. No network or key.

## Loader (`core/loaders/`)
- Get a real sample from the owner; don't write from a spec alone.
- Subclass `DocumentLoader`: `mime_types` + `load(bytes) -> list[PageUnit]` (1-based pages, PNG, `text_layer` only if the format truly has one). Detect by content, not file name.
- Corrupt/encrypted/empty/oversize -> `UnsupportedInputError` saying what happened and what to do. Never silently return zero pages. State page and pixel caps in the README.
- Register in `LOADERS`; add to the UI file picker.
- Tests: good, corrupt, wrong extension/right content, page count; synthetic fixtures built in the test.

## Profile (`profiles/*.yaml`) - config only, no code
- Fields: `id` (unique snake_case), `name`, `instruction`, optional `checks: [{target, expr}]` (only `+`/`-` of block keys; no `eval`).
- `instruction` says WHAT to extract and the `key` convention (line number, "Table 2", "Fig. 3"). Don't repeat or contradict `SYSTEM_RULES`; no output-format talk.
- Add `checks` only where the document itself guarantees the arithmetic, and only over keys the instruction tells the model to emit. Missing/unreadable operands -> check skipped, not failed.
- Test: every profile loads, ids unique, `expr` parses; fake-provider end-to-end run. The instruction is in the cache key, so edits re-run automatically.

## Always
Run `python -m pytest -q`. Add a short recipe to the README extension-points section. Report files touched, tests run, and anything not verified live (no real key or sample).

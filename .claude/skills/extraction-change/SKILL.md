---
name: extraction-change
description: Pre-commit checklist for any change to prompts.py, extractor.py, validator.py, renderer.py, models.py or a provider's request/response handling. Use before committing such a change, or when asked "is this change ready?".
allowed-tools: Bash(git diff:*), Bash(git log:*), Bash(grep:*), Bash(python -m pytest:*), Bash(python eval/run_eval.py:*), Read
---

Don't commit until every item has an answer. "Not affected, because ..." is an answer.

## 1. Write-up (commit body)
Three or four sentences: what outputs looked like before, what changes, why this approach, what it costs (tokens, latency, extra calls). Name constants touched (`PROMPT_VERSION`, `RENDER_DPI`, thresholds like grounding 85, retry max 4), old -> new.

## 2. Cache and versioning
- Prompt text, `SYSTEM_RULES`, the schema, or how the prompt is assembled changed -> **bump `PROMPT_VERSION`**, or stale cached results will mask the change.
- `Block`/`PageResult` fields changed -> old cache JSON must still parse or be invalidated; say which. Update renderer, validator, UI and gold scorer in the same change or list who must follow.

## 3. Boundaries
```bash
grep -rnE "google|genai|openai|anthropic" core --include=*.py | grep -v "core/providers/"
grep -rnE "pymupdf|fitz|PIL" core --include=*.py | grep -v "core/loaders/"
grep -rniE "rp[0-9]|SPT|PKP|Applied Ergonomics|Table 1" core --include=*.py | grep -v "core/prompts.py"
```
Each hit outside its home is a bug (vendor SDK outside providers, format code outside loaders, domain words in generic code). `SYSTEM_RULES` must stay domain-neutral except for the owner's draft wording.

## 4. Honesty of output
- Does anything now guess, fill in, round or "fix" a value? The validator may flag or downgrade status; it never silently edits a value.
- Masked/illegible -> `unreadable`; absent -> `missing`; unsure -> `uncertain`; chart -> `estimated` (forced by the validator). Still true?
- Failures: provider errors, bad JSON after repair, unsupported input - each still ends in a visible `PageResult.error`, issue or `st.error`? Nothing swallowed, run never crashes?

## 5. Tests and metrics
- `python -m pytest -q` (fake provider, no key). New behaviour has a test; no assertion loosened.
- Renderer output changed on purpose -> update the snapshot **and say why**; unexpected snapshot diff = bug.
- Extraction behaviour changed and saved outputs exist -> run `python eval/run_eval.py` (via `eval-implementer`); report which metrics moved. Don't claim improvement without the numbers.

## 6. Words
README, architecture diagram and "Known limitations" still describe reality? List what needs editing.

## 7. Commit
One block/step per commit, message `<topic>, step N: <what>`, with the attribution lines.

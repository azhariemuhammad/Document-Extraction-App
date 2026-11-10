---
name: build-block
description: Run the next numbered block of the build order in CLAUDE.md (1-6), delegating to core-implementer, ui-implementer and eval-implementer, then STOP and tell the owner how to verify. Use when asked to "build block N", "next block", "continue", or "implement the plan".
argument-hint: "[block number 1-6] (default: next unfinished)"
allowed-tools: Bash(git log:*), Bash(git status:*), Bash(git diff:*), Bash(ls:*), Bash(python -m pytest:*), Bash(docker compose:*), Read, Agent(core-implementer), Agent(ui-implementer), Agent(eval-implementer)
---

Block: `$ARGUMENTS` (blank = the first block in `CLAUDE.md` "Build order" whose "done when" isn't met).

## 1. Check quietly first
`git log --oneline -15`, `git status --short`, `ls` the repo layout. Decide which blocks exist already. Read `CLAUDE.md` data model and interfaces; they are the contract. Never start block N+1 before the owner has verified block N.

## 2. Split the block into steps
Write 3-8 small steps, each with its own check. Assign each to one agent:
- `core/`, `profiles/`, Dockerfile, compose -> `core-implementer`
- `app/ui.py` -> `ui-implementer`
- `eval/`, `tests/` -> `eval-implementer`

Interface first: when UI or eval depends on `core/`, finish the `core/` step and its commit before the dependent step. Give each agent a brief: block, branch (the current one), the exact steps, the check, and "see CLAUDE.md". Run agents one at a time unless their files don't overlap.

## 3. Block-specific traps
- **Block 1:** FakeProvider must be runnable end to end; "done" means `docker compose up --build` shows fake Markdown at http://localhost:8501. Include one `uncertain` and one `estimated` block in the canned output.
- **Block 2:** leave `SYSTEM_RULES` as the draft from `CLAUDE.md` and tell the owner it's theirs to refine. Read the Gemini model name from `GEMINI_MODEL`; if unset, fail visibly, never guess a model. Real calls need `GEMINI_API_KEY`; if absent, say you verified only with the fake provider.
- **Block 3:** cache key includes `PROMPT_VERSION`; verify a second run reports `cached=True` and zero provider calls.
- **Block 4:** validator has no LLM and no domain strings; domain checks live in `profiles/*.yaml`.
- **Block 5:** gold values are the owner's. Agents create skeleton + scorer only (see `eval-implementer`).
- **Block 6:** README sections are listed in `submit-check`; finish with it.

## 4. Verify and hand over
After the agents report: `python -m pytest -q`, review the diff for boundary violations (vendor SDK outside `providers/`, format code outside `loaders/`, domain words outside `profiles/`). Add a **walkthrough for the owner**: for each new or changed file, 2-3 plain sentences on what it does, why it is designed that way, and how it connects to its neighbours, plus the 2-3 questions a reviewer would likely ask about it. The owner must understand every piece well enough to explain it on video; if something is hard to explain, simplify the code instead. Then **stop** and tell the owner, in under 10 lines: what changed, the exact commands to run/verify (`docker compose up --build`, URL, what to click), what is unverified (e.g. no API key, sample file missing), and decisions that are theirs. Say plainly if any check failed or was skipped.

## Principles
- Simple, explainable code beats clever code; the owner must defend every decision on video.
- No frameworks, no new dependencies outside the list in `CLAUDE.md`.
- Never invent sample content, gold values or accuracy numbers.
- Do not push other branches or open PRs unless asked.

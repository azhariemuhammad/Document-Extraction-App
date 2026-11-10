---
name: submit-check
description: Final pre-submission review of the take-home - repo contents, secrets, tests, Docker, eval results, README claims, limitations - scored against the grading rubric. Use when asked to "submit", "is it ready?", "final check", "how would this be graded?", or at the end of build block 6.
allowed-tools: Bash(git status:*), Bash(git log:*), Bash(git ls-files:*), Bash(git check-ignore:*), Bash(grep:*), Bash(ls:*), Bash(python -m pytest:*), Bash(python eval/run_eval.py:*), Bash(docker compose:*), Bash(curl -s:*), Read
---

Report each item **pass / fail / not checked (why)**. Never claim something ran that didn't (e.g. no Docker or API key here). Fix nothing silently; list fixes for the owner. Don't push or open a PR unless asked.

## 1. Repo and secrets
- [ ] `app/ core/ profiles/` (4 profiles) `eval/ tests/ samples/ outputs/`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `.gitignore`, `README.md`
- [ ] `outputs/` has Markdown for **both** files, incl. two different instructions on one file
```bash
git check-ignore .env && git ls-files | grep -E '(^|/)\.env$'
grep -rnE "AIza[0-9A-Za-z_-]{20,}|sk-[A-Za-z0-9]{20,}" $(git ls-files)
```
- [ ] `.env` ignored and untracked, no keys, `.env.example` values empty, no cache/venv committed

## 2. Behaviour
- [ ] `python -m pytest -q` passes with no API key
- [ ] Docker: with `LLM_PROVIDER=fake`, `docker compose up --build -d` then `curl -s localhost:8501/_stcore/health` -> ok; `docker compose down`. Never overwrite an existing `.env`.
- [ ] unsupported file and provider failure show visible UI errors; failed pages shown, not hidden
- [ ] 18-page PDF fully processed

## 3. Boundaries (modularity)
```bash
grep -rnE "google|genai|openai|anthropic" core --include=*.py | grep -v "core/providers/"
grep -rnE "pymupdf|fitz|PIL" core --include=*.py | grep -v "core/loaders/"
grep -rniE "rp[0-9]|SPT|PKP|Applied Ergonomics" core --include=*.py | grep -v "core/prompts.py"
```
Any hit outside its home is a bug.

## 4. Evaluation and README honesty
- [ ] gold items hand-verified (no `UNVERIFIED` left, or listed pending); `python eval/run_eval.py` matches `eval/results.md`
- [ ] every README number comes from `eval/results.md`; fake-provider results never presented as accuracy
- [ ] README has: setup, URL, architecture diagram, extension points (provider/loader/profile, capability differences, quota handling), validation, metrics + results table, limitations, next steps, AI tools used (owner fills in)
- [ ] limitations match reality: no boxes, tables not merged across pages, no image OCR cross-check, one live provider, chart values estimated, free-tier quota, PyMuPDF AGPL

## 5. Score like the panel
Score out of weight with 2-3 evidence bullets (file:line): extraction accuracy & evidence /35 · modularity /25 · reliability & validation /20 · usability & judgment /20. Then: verdict (ready / not ready), blockers first, top 3 fixes by points gained per hour, and three questions the owner's video must answer well.

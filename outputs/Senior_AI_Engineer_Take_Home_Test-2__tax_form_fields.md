# Extraction result

## Page 1

- [ ] 1 Inputs and samples
  📍 p.1 · "Inputs and samples. Support PDF and PNG or JPG."

- [ ] 2 Markdown output
  📍 p.1 · "Markdown output. Handle prose, tables, charts and form fields or checkboxes where present."

- [ ] 3 Model independence
  📍 p.1 · "Model independence. Select providers through configuration and a shared interface."

- [ ] 4 Evidence and uncertainty
  📍 p.1 · "Evidence and uncertainty. Include page or image-region references with supporting excerpts for extracted information."

- [ ] 5 Reliability
  📍 p.1 · "Reliability. Check output completeness and formatting."

- [ ] 6 Evaluation
  📍 p.1 · "Evaluation. Select and justify metrics for extraction quality and operational performance."

- [ ] 7 Simple UI
  📍 p.1 · "Simple UI. Provide file upload, editable extraction instructions, a run action, rendered Markdown results, source references, visible errors and a .md download."

- [ ] 8 GitHub repository
  📍 p.1 · "GitHub repository. Submit a repository we can access, containing the full source, Dockerfiles, Compose configuration, .env.example, sample Markdown outputs and relevant tests."

- [ ] 9 Video walkthrough
  📍 p.1 · "Video walkthrough. Submit a short video showing startup, extraction on both samples, Markdown output and source references, plus an explanation of the architecture and limitations."

## Validation issues

- **info** (p.None, 3): Check 3 = 1 - 2 skipped: a value is missing or unreadable.
- **info** (p.None, 8c): Check 8c = 8a + 8b skipped: a value is missing or unreadable.
- **info** (p.None, 9): Check 9 = 6 - 7 - 8c skipped: a value is missing or unreadable.
- **info** (p.None, 11): Check 11 = 9 - 10c skipped: a value is missing or unreadable.

## Run info

- provider: gemini
- model: gemini-3.1-flash-lite
- pages: 1
- total time: 4.4s
- tokens (in/out): 2289 / 717
- provider calls: 1
- cache hits: 0
- coverage: 100%
- grounded evidence: 100%
- arithmetic checks: 0/4
- failed pages: none

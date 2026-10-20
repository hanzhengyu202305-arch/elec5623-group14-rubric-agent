# Generative AI use disclosure

- **Tool:** Claude (Anthropic) running in Cursor, 12–13 Sep 2026.
- **What it produced:** the initial code of this repository, the synthetic dataset generator, tests, documentation and the evaluation harness, working from the approved Group 14 Track A proposal and the ELEC5623 lecture/lab materials on Canvas. On 13 Sep it also installed a local open-weight model (Ollama, `qwen2.5:7b-instruct`) on the group member's machine, ran the evaluation with it and committed the report (`docs/EVALUATION_live_qwen7b.md`), transcribed the Canvas marking rubric into `dataset/real/`, and added our own proposal PDF (cover removed) as the real test document.
- **What it did not do:** decide the product scope (that is the proposal), label data with a second annotator, run marker sessions, or choose the production model.
- **Human review:** the group is responsible for reading, running and modifying everything here before any Canvas submission. Each member's edits are recorded in git history under their own branch (see `CONTRIBUTING.md`).
- **In the product itself:** the assessment model is called only through `src/rubric_agent/gateway.py`; its output is treated as untrusted input and validated before a marker sees it (`docs/GOVERNANCE.md`).

- **Tool:** Cursor agent, 22 Sep 2026.
- **What it produced:** downloaded the new Canvas files into the course folder; drafted `docs/FINAL_REPORT_DRAFT.md` and `docs/WEEK8_TUTOR_UPDATE.md` from the existing repository and the 13 Sep evaluation files; added the Week 7 note in `docs/ARCHITECTURE.md`.
- **What it did not do:** run a new model evaluation, relabel data, invent marker-session results, or change the agent pipeline. The LangChain Lab 7 notebook was saved as course material and was not turned into this product.

- **Tool:** Cursor agent, 23 Sep 2026.
- **What it produced:** concurrent criterion calls in `run_pipeline`, a test that the calls overlap and stay in rubric order, and `scripts/export_second_pass.py`, which writes a blank labelling sheet.
- **What it did not do:** relabel the 62 pairs, run a new model evaluation, invent marker-session times, or change the prompt or the validator.
- **Also on 23 Sep:** a marker checklist (`src/rubric_agent/coverage.py`) shown on the review page. It does not alter scores or the 13 Sep metrics.

- **Tool:** Cursor agent, 23 Sep 2026 (related work and quote check).
- **What it produced:** a comparison in section 3 of `docs/FINAL_REPORT_DRAFT.md` with eight public GitHub grading repositories, and a validator check (`quote_not_in_evidence`) that a quote written next to an evidence id must occur in that unit, with unit tests.
- **What it did not do:** relabel the 62 pairs, rerun the model, or change the 13 Sep metrics.

- **Tool:** Cursor agent, 4 Oct 2026.
- **What it produced:** revised `docs/FINAL_REPORT_DRAFT.md` against Haolin Jin's proposal comments, and wrote `docs/MARKER_RESPONSE.md`. Publisher and arXiv pages were opened for Cai (2026), Hong et al. (2026, arXiv v1 and the current record) and Chu et al. (2025). GradeAgentOps was taken from the Crossref record for DOI 10.3390/ai7060198, including the deposited abstract.
- **What it did not do:** change the 6.5/10 proposal mark, resubmit the proposal, invent who did which work, invent metrics or quotations, relabel the 62 pairs, or rerun the model.

- **Tool:** Cursor agent, 7 Oct 2026 (robustness wrap-up).
- **What it produced:** wrote `docs/robustness/RESULTS.md` from the already-run `robustness.json`, post-processed token counts with `scripts/extract_usage.py`, and inserted those figures into the report, status and changelog.
- **What it did not do:** change the frozen prompts or final-test inputs, fill the faithfulness sheet, annotate final_test, or rerun the model.

Update this file whenever an AI tool contributes to a change.

## 4 October 2026 — Codex assistance

- **Produced:** source-based comparison of the tutor-named EFS, GradeAgentOps and RULERS methods; updated report, fixed evaluation protocol and named proposed responsibilities. User selected Zhengyu Han as core GenAI/evaluation lead. Project instructions now retain the user's request to apply the actual proposal feedback in later 5623 work.
- **Implemented:** finite/schema/feedback validation; review/export integrity; same-prompt full-context B3 and replay; evaluation denominators, conditional score metrics, per-criterion QWK, manifests and per-repeat outputs; targeted regression tests and a repeatable local-model smoke script.
- **Verified by tools:** offline tests/lint, fixture A/B3 runs, and actual local Qwen2.5-7B smoke runs (synthetic decoy and own de-identified PDF). Exact records are in `docs/validation/README.md` and companion JSON. A smoke check is not a full labelled quality study.
- **Not completed by AI:** independent human annotation, participant timings, teammate acceptance of proposed roles, actual-member contribution attestations, or the live assessed Q&A. No grades were submitted and no Canvas write was performed.
- **Human review:** still required before submission. AI-generated code or text must not be claimed as independently authored or already reviewed by every teammate.

## 7 October 2026 — Codex GitHub readability update

- **Produced:** a Chinese-first project homepage, an English technical reference preserved from the previous README, and a task-based documentation index. Updated the Chinese walkthrough to match the new navigation and distinguish historical screenshots from current experiments.
- **Scope:** documentation only; no source, prompts, labels, model configuration or experiment results were changed. No new model accuracy or timing claims were made.
- **Verification:** local documentation links, whitespace checks and the existing freeze guard. No new model evaluation or human study was conducted.
- **Human review:** the documentation change is submitted for review; teammate approval and coursework submission are not claimed.

## 20 October 2026 — OpenRouter gateway option

- **Produced:** an optional OpenRouter gateway (`--gateway openrouter[:model]`) on the existing OpenAI-compatible client. The key is read from `RMA_OPENROUTER_API_KEY` at runtime. The Review page lists it when that variable is set and labels it not configured otherwise. Docs name `RMA_OPENROUTER_API_KEY` and `RMA_OPENROUTER_MODEL`.
- **What it did not do:** call OpenRouter, run a marking campaign, or change frozen evaluation numbers.

# Governance, safety and limitations

## Human oversight (C1, NFR5)

* The system produces *provisional* criterion suggestions. There is no code path that records a grade anywhere.
* Export of a review record is refused while any criterion is `pending`. Accepted, edited and rejected decisions carry a UTC timestamp.
* Marker values override AI values in the export; the AI suggestion is kept in the same row so later analysis (M9) is possible.

## Privacy and data (C3, NFR6)

* `dataset/` is synthetic and group-authored. The only real document is **our own proposal** (`dataset/real/`), with the cover page (names, student IDs) removed. No other student's work is in this repository.
* Two live options with different data paths:
  * **Local Ollama** (`ollama:<model>`): the model runs on the demo machine; submission text never leaves it. This is the option used for `docs/EVALUATION_live_qwen7b.md` and needs no approval beyond the group's own.
  * **Hosted / Azure** (`live`, `RMA_*` env): text is sent to the provider. It is offered in the UI only when the variables are set, and it never appears in tests or CI. Before any real or de-identified submission goes this way the group needs tutor confirmation of the provider, a written data-handling note, and de-identification of the file.
* Uploaded files in the UI are written under `data/` (git-ignored); nothing is uploaded anywhere except the chosen model endpoint.
* The run log stores evidence IDs, scores and warnings, not the submission text.

## Secrets

* Keys are read from `RMA_MODEL_API_KEY` (generic live gateway) or `RMA_OPENROUTER_API_KEY` (OpenRouter) once, sent only in the request header, never printed, never written to the run log. `gateway.name` contains model and host only.
* The Azure key from Lab 1 stays in Azure/Foundry (course rule). Configure it through the environment on the machine that runs the demo; do not paste it into code, notebooks or chat.

Example (Azure AI Foundry):

```bash
export RMA_GATEWAY=live
export RMA_MODEL_ENDPOINT="https://<resource>.openai.azure.com/openai/deployments/<deployment>"
export RMA_MODEL="<deployment>"
export RMA_MODEL_API_KEY="<key>"
export RMA_API_KEY_HEADER=api-key
export RMA_API_VERSION=2024-10-21
rma demo --submission s4_decoy_eval
```

Example (OpenRouter; put a new key in the environment, not in a file that is committed):

```bash
export RMA_OPENROUTER_API_KEY="<key>"
export RMA_OPENROUTER_MODEL="openai/gpt-4o-mini"   # optional; this is the default
rma --gateway openrouter demo
```

Example (local Ollama, no key; the UI lists running models by itself):

```bash
brew install ollama && ollama pull qwen2.5:7b-instruct
OLLAMA_CONTEXT_LENGTH=16384 ollama serve &      # default context (4k) is too small for B2 on long documents
rma --gateway ollama:qwen2.5:7b-instruct demo --submission s4_decoy_eval
```

## Model output is untrusted input (Lab 6 §6, §10)

* Every model response is parsed strictly against Listing 6.1; anything else is rejected with `invalid_model_output` (after one re-ask that quotes the parse error).
* A transport failure produces an explicit `provider_error`, never a fabricated score.
* The validator checks the content, not just the shape: evidence IDs must exist in the retrieved set, scores must be on the rubric grid, and every sentence that asserts something about the submission must carry a citation.
* A rejected record gets **one** corrective round: the model sees the validator's findings and answers again; the answer is validated again. Two failures → no score. The number of attempts is in the log, so "how often did the model need correcting" is a reported number (`revision_rate`), not a hidden retry loop.
* Prompts are versioned files; the version is in every log line so a prompt change is auditable.

## Known limitations

1. **The fixture is not a model.** Numbers in `docs/EVALUATION.md` produced with `fixture-*` show that the harness works; M4 (sufficiency agreement) and M8 (score agreement) are expected to be poor with the fixture and must be re-measured with a real model.
2. **Text-only.** Scanned PDFs, images, tables rendered as images and handwriting are out of scope (C4).
3. **Lexical retrieval.** BM25 can miss paraphrased evidence; the S4 decoy defence relies on the assessment step, not retrieval.
4. **Small labelled set.** 62 pairs, one annotator pass, phrase-based relevance. The annotation round with two labellers and agreement statistics (proposal §8.1) is still to do.
5. **Human metrics missing.** M9–M11, M14 require marker sessions.
6. **English only.** Tokenisation and negation cues are English.

## Risk register (from proposal Table 9.1, status)

| Risk | Mitigation in code | Status |
|---|---|---|
| Hallucinated evidence | validator rejects unknown IDs and uncited claims | done, tested |
| Over-trust in AI score | scores shown as "suggested", export gate, marker override | done, tested |
| Model/API unavailable | fixture gateway; local model option; fail-closed errors | done |
| Privacy breach | synthetic data, opt-in live gateway, key only in env | done; approval process pending |
| PDF extraction failure | explicit `SubmissionParseError`; text-PDF only | done |
| Schedule slip | de-scoping order §10.3 (FR14 → re-ranking → UI polish → dataset size) | tracked in STATUS.md |

## AI use disclosure

See `AI_USE.md`. Claude in Cursor drafted this repository from the approved proposal; the group reviews, runs and owns the result. Any Canvas submission must include this disclosure.

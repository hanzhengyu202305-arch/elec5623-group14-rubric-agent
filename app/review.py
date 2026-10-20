"""Marker review UI (FR7, FR12, FR13, FR15, NFR4, NFR5).

Loaded by app/streamlit_app.py (st.navigation); run: streamlit run app/streamlit_app.py
The marker never writes a prompt. Every criterion must be accepted, edited or
rejected before export is enabled. Sibling pages: evaluation.py, run_log.py.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rubric_agent import PROMPT_VERSION  # noqa: E402
from rubric_agent.coverage import top_band_coverage  # noqa: E402
from rubric_agent.errors import ExportBlocked, RubricParseError, SubmissionParseError  # noqa: E402
from rubric_agent.gateway import build_gateway, local_ollama_models  # noqa: E402
from rubric_agent.minimax import DEFAULT_ENDPOINT, DEFAULT_MODEL, MiniMaxGateway  # noqa: E402
from rubric_agent.pipeline import run_direct_baseline, run_pipeline  # noqa: E402
from rubric_agent.store import RunLogger  # noqa: E402

DATASET = ROOT / "dataset"
RUN_LOG = ROOT / "data" / "runs.jsonl"
EXAMPLES: dict[str, tuple[Path, Path]] = {
    "Group 14 proposal v2 (real 16-page PDF) on the official Canvas rubric": (
        DATASET / "real" / "elec5623_business_proposal_rubric.md", DATASET / "real" / "group14_proposal_v2.pdf"),
    "s1_standard (S1 baseline)": (DATASET / "rubrics/engineering_report.md", DATASET / "submissions/s1_standard.txt"),
    "s2_dispersed (S2 evidence spread out)": (DATASET / "rubrics/engineering_report.md", DATASET / "submissions/s2_dispersed.txt"),
    "s3_missing_eval (S3 criterion absent)": (DATASET / "rubrics/engineering_report.md", DATASET / "submissions/s3_missing_eval.txt"),
    "s4_decoy_eval (S4 keyword decoy)": (DATASET / "rubrics/engineering_report.md", DATASET / "submissions/s4_decoy_eval.txt"),
    "s5_long (S5 12 pages)": (DATASET / "rubrics/engineering_report.md", DATASET / "submissions/s5_long.txt"),
    "p3_decoy on proposal rubric (numbered format)": (DATASET / "rubrics/proposal_rubric.md", DATASET / "submissions/p3_decoy.txt"),
    "s1_standard on half-mark table rubric (S7)": (DATASET / "rubrics/half_mark.md", DATASET / "submissions/s1_standard.txt"),
}

st.title("AI-Assisted Rubric Marking Agent")
st.caption("ELEC5623 Group 14 · Track A prototype · provisional scores are suggestions, the marker decides.")

for key in ("result", "session", "case_id", "baseline", "gateway_label"):
    st.session_state.setdefault(key, None)


@st.cache_data(ttl=30)
def _ollama_models() -> list[str]:
    return local_ollama_models()


# --- Sidebar ------------------------------------------------------------------------
with st.sidebar:
    st.header("1 · Inputs")
    example = st.selectbox("Example", ["(upload my own)", *EXAMPLES])
    rubric_file = st.file_uploader("Rubric (.md / .txt / .pdf)", type=["md", "txt", "pdf"])
    submission_file = st.file_uploader("Submission (.txt / .pdf)", type=["txt", "pdf"])

    st.header("2 · Model")
    options = {"fixture (offline, deterministic)": "fixture"}
    if os.environ.get("RMA_MODEL_ENDPOINT") and os.environ.get("RMA_MODEL"):
        options[f"live · {os.environ['RMA_MODEL']} (RMA_* environment)"] = "live"
    for name in _ollama_models():
        options[f"local Ollama · {name}"] = f"ollama:{name}"
    openrouter_model = (os.environ.get("RMA_OPENROUTER_MODEL") or "").strip() or "openai/gpt-4o-mini"
    openrouter_ready = bool((os.environ.get("RMA_OPENROUTER_API_KEY") or "").strip())
    if openrouter_ready:
        options[f"OpenRouter · {openrouter_model}"] = f"openrouter:{openrouter_model}"
    else:
        options["OpenRouter (not configured)"] = "openrouter"
    options["MiniMax API (hosted)"] = "minimax"
    gateway_label = st.radio("Gateway", list(options),
                             help="Live gateways appear only when configured (RMA_* variables) or when a local Ollama server is running. Keys are never shown or logged.")
    spec = options[gateway_label]
    if spec == "openrouter" or spec.startswith("openrouter:"):
        if openrouter_ready:
            st.caption("OpenRouter sends the selected text to https://openrouter.ai/api/v1. The API key stays in RMA_OPENROUTER_API_KEY and is not shown.")
        else:
            st.caption("OpenRouter is not configured. Set RMA_OPENROUTER_API_KEY and restart. Optional: RMA_OPENROUTER_MODEL. The key is never shown.")
    if spec == "minimax":
        minimax_regions = {
            "International · platform.minimax.io": DEFAULT_ENDPOINT,
            "China · platform.minimaxi.com": "https://api.minimaxi.com/v1",
        }
        region = st.selectbox("MiniMax account region", list(minimax_regions), key="minimax-region",
                              index=1 if os.environ.get("RMA_MINIMAX_ENDPOINT") == "https://api.minimaxi.com/v1" else 0,
                              help="Select the region of the console that issued your key, not your physical location. A region/key mismatch may return HTTP 401.")
        minimax_endpoint = minimax_regions[region]
        st.caption(f"Base URL: {minimax_endpoint}")
        minimax_model = st.text_input("MiniMax model", value=os.environ.get("RMA_MINIMAX_MODEL", DEFAULT_MODEL))
        minimax_key = st.text_input("MiniMax API key", type="password", key="minimax-key",
                                   help="Kept in this browser session only; not saved to files or run logs.")
        st.caption("Subscription keys (sk-cp) and pay-as-you-go keys use different quotas. Assessment evidence is sent to MiniMax; Ollama is not required.")
    fail_mode = st.selectbox("S6 fault injection (fixture only)", ["none", "unknown_id", "out_of_range", "uncited_claim", "invalid_json"],
                             disabled=spec != "fixture")
    k = st.slider("Evidence units per criterion (K)", 1, 10, 5)
    log_runs = st.checkbox("Append to personal log (data/minimax_runs.jsonl)" if spec == "minimax" else "Append to run log (data/runs.jsonl)",
                           value=True, help="FR16: model id, prompt version, retrieval settings, evidence IDs, latency.")
    run = st.button("Run review", type="primary", use_container_width=True)

    st.divider()
    st.caption(f"Prompt version `{PROMPT_VERSION}` · uploads stay on this machine; nothing is sent anywhere except the chosen model endpoint.")


def _save_upload(upload, folder: str) -> Path:
    tmp = ROOT / "data" / folder / upload.name
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(upload.getvalue())
    return tmp


if run:
    if spec == "fixture" and fail_mode != "none":
        spec = f"fixture:{fail_mode}"
    try:
        gateway = (MiniMaxGateway(api_key=minimax_key or os.environ.get("RMA_MINIMAX_API_KEY", ""),
                                  endpoint=minimax_endpoint, model=minimax_model)
                   if spec == "minimax" else build_gateway(spec))
        if example != "(upload my own)":
            rubric_src, sub_src = EXAMPLES[example]
            case_id = sub_src.stem
        elif rubric_file and submission_file:
            rubric_src = _save_upload(rubric_file, "rubrics")
            sub_src = _save_upload(submission_file, "submissions")
            case_id = submission_file.name
        else:
            st.error("Pick an example or upload both a rubric and a submission.")
            st.stop()
        logger = RunLogger(ROOT / "data" / "minimax_runs.jsonl" if spec == "minimax" else RUN_LOG) if log_runs else None
        with st.spinner("Parsing, retrieving evidence and assessing… (a local 7B model needs roughly 10 s per criterion)"):
            result = run_pipeline(rubric_src, sub_src, gateway=gateway, k=k, test_case_id=case_id, logger=logger,
                                  workers=1 if spec == "minimax" else None)
        st.session_state.result = result
        st.session_state.session = result.review_session()
        st.session_state.case_id = case_id
        st.session_state.baseline = None
        st.session_state.gateway_label = gateway_label
        st.session_state.sources = (rubric_src, sub_src, spec)
        st.session_state.source_gateway = gateway
        if any("provider_error" in a.draft.flags for a in result.assessments):
            st.error("Model API request failed; no fallback to fixture. Check the key, endpoint, model permissions, quota and output limit.")
            if spec == "minimax" and getattr(gateway, "provider_error", None):
                st.error(gateway.provider_error)
        for key in list(st.session_state.keys()):
            if key.startswith(("act-", "sc-", "cm-")):
                del st.session_state[key]
    except (RubricParseError, SubmissionParseError) as exc:
        st.error(f"Could not read input: {exc}")
        st.stop()
    except (RuntimeError, ValueError) as exc:
        st.error(str(exc))
        st.stop()

result = st.session_state.result
session = st.session_state.session
if not result or not session:
    st.info("Pick an example in the sidebar (or upload a rubric and a submission) and press **Run review**. "
            "The first example runs the agent over our own proposal against the official Canvas rubric.")
    st.stop()

# --- Header ---------------------------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Criteria", len(result.rubric.criteria))
c2.metric("Pages", len(result.pages))
c3.metric("Evidence units", len(result.units))
c4.metric("Pipeline latency", f"{result.latency_ms / 1000:.1f} s")
c5.metric("Model", result.model_id)
st.caption(f"Rubric **{result.rubric.title}** ({result.rubric.source_format} format) · case `{st.session_state.case_id}` · gateway {st.session_state.gateway_label}")

flagged = [a for a in result.assessments if not a.accepted]
revised = [a for a in result.assessments if "revised_once" in a.draft.flags]
if flagged:
    st.warning(f"{len(flagged)} criterion record(s) failed validation and cannot be accepted. Review the warnings, then edit or reject each suggestion.")
if revised:
    st.info(f"{len(revised)} record(s) were corrected by the model after the validator sent its findings back (one corrective round; the corrected answer was validated again).")

with st.expander("Rubric as parsed (FR1–FR3)", expanded=False):
    for c in result.rubric.criteria:
        st.markdown(f"**{c.id} · {c.name}** — max {c.max_mark:g}, step {c.granularity:g}")
        for d in c.descriptors:
            st.markdown(f"&nbsp;&nbsp;&nbsp;`{d.score:g}` {d.text}")

# --- Per-criterion review ---------------------------------------------------------------
st.subheader("3 · Review each criterion")
for validated in result.assessments:
    draft = validated.draft
    crit = next(c for c in result.rubric.criteria if c.id == draft.criterion_id)
    decision = session.decisions[draft.criterion_id]
    badge = {"sufficient": "🟢", "partial": "🟡", "insufficient": "🔴"}[draft.sufficiency]
    state_badge = {"pending": "⏳", "accepted": "✅", "edited": "✏️", "rejected": "🚫"}[decision.state]
    suggested = f"{draft.provisional_score:g}" if draft.provisional_score is not None else "—"
    title = f"{state_badge} {draft.criterion_id} · {crit.name} · {badge} {draft.sufficiency} · suggested {suggested} / {crit.max_mark:g}"
    with st.expander(title, expanded=decision.state == "pending"):
        left, right = st.columns([3, 2])
        with left:
            if validated.warnings:
                st.error("Validator: " + "; ".join(validated.warnings))
            if "revised_once" in draft.flags:
                st.caption("Corrected once after validator feedback.")
            st.markdown("**AI explanation**")
            st.write(draft.explanation)
            if draft.sufficiency != "insufficient":
                st.caption(f"Grounding audit: {validated.claims - validated.unsupported_claims}/{validated.claims} claims about the submission carry an evidence ID.")
            if draft.draft_feedback:
                st.markdown("**Draft feedback to the student (optional, FR14)**")
                st.write(draft.draft_feedback)
            hits = result.retrieved.get(draft.criterion_id, [])
            coverage = top_band_coverage(crit, hits)
            if coverage is not None:
                st.markdown(f"**Top-band checklist** (software, max {coverage.score:g})")
                st.caption(coverage.text)
                st.write("Present: " + (", ".join(coverage.present) or "—"))
                st.write("Missing: " + (", ".join(coverage.missing) or "—"))
            st.markdown(f"**Evidence** ({len(hits)} retrieved, {len(draft.evidence_ids)} cited)")
            if not hits:
                st.info("No relevant evidence found for this criterion (FR6 explicit state).")
            for unit in hits:
                cited = unit.id in draft.evidence_ids
                with st.container(border=True):
                    st.markdown(f"{'**' if cited else ''}{unit.id}{'**' if cited else ''} · {unit.locator}" + (" · cited" if cited else " · retrieved, not cited"))
                    if unit.adjacent_before:
                        st.caption("↑ " + unit.adjacent_before[:240])
                    st.write(unit.text)
                    if unit.adjacent_after:
                        st.caption("↓ " + unit.adjacent_after[:240])
        with right:
            st.markdown("**Marker decision**")
            states = ["pending", "accepted", "edited", "rejected"]
            action = st.radio("State", states, index=states.index(decision.state), key=f"act-{draft.criterion_id}", horizontal=True,
                              help="accepted = keep AI score · edited = your score overrides · rejected = no score recorded")
            default_score = decision.marker_score if decision.marker_score is not None else (draft.provisional_score or 0.0)
            score = st.number_input("Marker score", min_value=0.0, max_value=float(crit.max_mark), step=float(crit.granularity),
                                    value=float(default_score), key=f"sc-{draft.criterion_id}", disabled=action != "edited")
            comment = st.text_area("Marker comment", value=decision.marker_comment, key=f"cm-{draft.criterion_id}", height=90)
            if action == "pending":
                if decision.state != "pending":
                    session.reset(draft.criterion_id)
            else:
                try:
                    session.decide(draft.criterion_id, action, score=score, comment=comment)
                except ValueError as exc:
                    # A failed replacement must not leave the previously confirmed
                    # score available for export while the widget shows another value.
                    session.reset(draft.criterion_id)
                    st.error(str(exc))

# --- Baseline comparison ------------------------------------------------------------------
st.subheader("Compare with baseline B2 (whole document, one prompt)")
st.caption("B2 is the 'paste everything into a chatbot' approach from the proposal. It returns scores without evidence IDs, so nothing can be checked.")
if st.button("Run B2 on this submission", help="Uses the same gateway. With a local model this is one long call."):
    rubric_src, sub_src, spec = st.session_state.sources
    with st.spinner("Grading the whole document in one call…"):
        _, drafts = run_direct_baseline(rubric_src, sub_src, gateway=(st.session_state.source_gateway
                                       if spec == "minimax" else build_gateway(spec.split(":")[0] if spec.startswith("fixture") else spec)))
    st.session_state.baseline = drafts
if st.session_state.baseline:
    rows = []
    for validated, b2 in zip(result.assessments, st.session_state.baseline):
        d = validated.draft
        rows.append({
            "criterion": d.criterion_id,
            "agent score": d.provisional_score,
            "agent evidence": ", ".join(d.evidence_ids) or "—",
            "B2 score": b2.provisional_score,
            "B2 evidence": ", ".join(b2.evidence_ids) or "none (no citations possible)",
            "B2 explanation": b2.explanation[:160],
        })
    st.dataframe(rows, use_container_width=True)

# --- Export -------------------------------------------------------------------------------
st.subheader("4 · Export")
missing = session.unconfirmed()
got, cap = session.total()
if missing:
    st.error(f"Export blocked (NFR5) until these criteria have a decision: {', '.join(missing)}")
else:
    summary = session.summary()
    st.success(f"All criteria confirmed. Marker total {got:g} / {cap:g} · {summary['edited']} edited, {summary['rejected']} rejected · "
               f"session {summary['duration_s']:.0f} s.")
    try:
        col_a, col_b = st.columns(2)
        col_a.download_button("Download review record (JSON)", data=session.export_json(),
                              file_name=f"review_{st.session_state.case_id}.json", mime="application/json", use_container_width=True)
        col_b.download_button("Download review record (CSV)", data=session.export_csv(),
                              file_name=f"review_{st.session_state.case_id}.csv", mime="text/csv", use_container_width=True)
        with st.expander("Preview record"):
            st.dataframe(session.export_record(), use_container_width=True)
    except ExportBlocked as exc:
        st.error(str(exc))

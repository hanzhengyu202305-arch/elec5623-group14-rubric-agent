"""Run log viewer and replay (FR16, NFR2, NFR7, M12).

Every model call made by the review page (with logging on) or by `rma eval --log`
is one JSON line. This page lists them and can re-execute one entry with the
logged settings to check that the top evidence unit and the score are stable.
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rubric_agent.gateway import local_ollama_models  # noqa: E402
from rubric_agent.store import RunLogger, gateway_spec_for, replay_entry  # noqa: E402

st.title("Run log")
st.caption("One line per model call: model id, prompt version, retrieval settings, evidence IDs, latency, validator outcome (FR16).")

default = ROOT / "data" / "runs.jsonl"
path_text = st.text_input("Log file", value=str(default))
upload = st.file_uploader("…or upload a JSONL log", type=["jsonl"])
if upload:
    tmp = ROOT / "data" / "uploaded_runs.jsonl"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(upload.getvalue())
    path_text = str(tmp)

entries = RunLogger(Path(path_text)).read() if Path(path_text).exists() else []
if not entries:
    st.info("No entries yet. Run a review with *Append to run log* ticked, or `rma eval --log data/runs.jsonl`.")
    st.stop()

models = Counter(e.model_id for e in entries)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Entries", len(entries))
c2.metric("Models", len(models))
c3.metric("Median latency", f"{sorted(e.latency_ms for e in entries)[len(entries) // 2] / 1000:.1f} s")
c4.metric("Corrective rounds", sum(1 for e in entries if e.attempts > 1))

rows = [{
    "#": i, "when": e.created_at[:19], "case": e.test_case_id, "criterion": e.criterion_id, "model": e.model_id,
    "prompt": e.prompt_version, "k": e.retrieval_k, "sufficiency": e.sufficiency, "score": e.provisional_score,
    "cited": ", ".join(e.cited_ids), "top-1": e.evidence_ids[0] if e.evidence_ids else "", "attempts": e.attempts,
    "warnings": "; ".join(e.warnings), "latency s": round(e.latency_ms / 1000, 1),
} for i, e in enumerate(entries)]
st.dataframe(rows, use_container_width=True, hide_index=True, height=min(600, 40 + 35 * len(rows)))

st.subheader("Replay one entry (M12 repeatability)")
idx = st.number_input("Entry #", min_value=0, max_value=len(entries) - 1, value=len(entries) - 1)
entry = entries[int(idx)]
spec = gateway_spec_for(entry.model_id)
available = (
    spec == "fixture"
    or (spec.startswith("ollama:") and spec.partition(":")[2] in local_ollama_models())
    or (spec.startswith("openrouter:") and bool((os.environ.get("RMA_OPENROUTER_API_KEY") or "").strip()))
    or (spec == "live" and bool(os.environ.get("RMA_MODEL_ENDPOINT")))
)
st.write(f"Entry `{entry.test_case_id}` / `{entry.criterion_id}` was produced by `{entry.model_id}` → replay gateway `{spec}`"
         + ("" if available else " (not available on this machine)"))
if st.button("Replay with logged settings", disabled=not available):
    try:
        with st.spinner("Re-running the pipeline for this case…"):
            outcome = replay_entry(entry)
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        st.error(str(exc))
    else:
        a, b, c, d = st.columns(4)
        a.metric("Same top-1 evidence", "yes" if outcome.same_top1 else "no")
        b.metric("Same cited set", "yes" if outcome.same_cited else "no")
        c.metric("Score drift", "—" if outcome.score_drift is None else f"{outcome.score_drift:.0%} of max")
        d.metric("Within 10% tolerance", "yes" if outcome.within_tolerance else "no")

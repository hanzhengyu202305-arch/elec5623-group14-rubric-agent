"""`rma` command line.

  rma demo   [--rubric R] [--submission S] [--gateway fixture|live|openrouter[:model]] [--auto-accept] [--log runs.jsonl]
  rma eval   [--split all|dev|heldout] [--repeats N] [--gateway ...] [--report docs/EVALUATION.md] [--json out.json]
  rma replay --log runs.jsonl            # M12: re-execute logged calls and compare
  rma baseline [--rubric R] [--submission S]   # B2 direct grading for comparison
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .eval import evaluate_corpus, write_markdown_report
from .gateway import build_gateway
from .pipeline import run_direct_baseline, run_pipeline
from .resources import resource_directory
from .store import RunLogger, replay_entry

DATASET = resource_directory("dataset")


def _resolve(kind: str, name: str) -> Path:
    p = Path(name)
    if p.exists():
        return p
    folder = DATASET / ("rubrics" if kind == "rubric" else "submissions")
    for ext in (".md", ".txt", ".pdf"):
        cand = folder / f"{name}{ext}"
        if cand.exists():
            return cand
    sys.exit(f"{kind} not found: {name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rma", description="Evidence-first rubric marking agent")
    parser.add_argument("--gateway", default=None, help="fixture (default), fixture:<fail_mode>, ollama:<model> (local server), openrouter[:model] (RMA_OPENROUTER_API_KEY), or live (RMA_* env)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    demo = sub.add_parser("demo", help="Run the agent path on one rubric + submission")
    demo.add_argument("--rubric", default="engineering_report")
    demo.add_argument("--submission", default="s1_standard")
    demo.add_argument("--k", type=int, default=5)
    demo.add_argument("--evidence-mode", choices=["bm25", "full_context"], default="bm25")
    demo.add_argument("--auto-accept", action="store_true", help="accept every suggestion and print the export")
    demo.add_argument("--log", type=Path, default=None, help="append run log JSONL here")

    ev = sub.add_parser("eval", help="Score the labelled corpus (M1–M8, M12, M13, M16, M17)")
    ev.add_argument("--split", choices=["all", "dev", "heldout"], default="all")
    ev.add_argument("--repeats", type=int, default=3)
    ev.add_argument("--k", type=int, default=5)
    ev.add_argument("--evidence-mode", choices=["bm25", "full_context"], default="bm25",
                    help="bm25 retrieval or B3 full-context ablation with the same citation/validation rules")
    ev.add_argument("--no-baseline", action="store_true")
    ev.add_argument("--labels", default="labels.json",
                    help="label file inside the dataset directory (default labels.json; labels_v2.json holds the "
                         "reviewed dev-split sufficiency corrections, see dataset/LABELS_V2_CHANGES.md)")
    ev.add_argument("--report", type=Path, default=None, help="write Markdown report here")
    ev.add_argument("--json", type=Path, default=None, help="write raw JSON here")
    ev.add_argument("--log", type=Path, default=None)

    rp = sub.add_parser("replay", help="Re-execute logged calls and report repeatability")
    rp.add_argument("--log", type=Path, required=True)

    bl = sub.add_parser("baseline", help="Baseline B2: direct whole-document grading")
    bl.add_argument("--rubric", default="engineering_report")
    bl.add_argument("--submission", default="s1_standard")

    args = parser.parse_args(argv)
    if args.cmd in {"demo", "eval"} and args.k < 1:
        parser.error("--k must be positive")
    if args.cmd == "eval" and args.repeats < 1:
        parser.error("--repeats must be positive")
    gateway = build_gateway(args.gateway)

    if args.cmd == "demo":
        rubric = _resolve("rubric", args.rubric)
        submission = _resolve("submission", args.submission)
        logger = RunLogger(args.log) if args.log else None
        result = run_pipeline(rubric, submission, gateway=gateway, k=args.k,
                              test_case_id=submission.stem, logger=logger, rubric_id=rubric.stem,
                              evidence_mode=args.evidence_mode)
        print(f"gateway={gateway.name} rubric={result.rubric.title!r} ({result.rubric.source_format}) "
              f"criteria={len(result.rubric.criteria)} units={len(result.units)} latency_ms={result.latency_ms:.1f}")
        for item in result.assessments:
            d = item.draft
            flag = "" if item.accepted else "  ⚠ " + "; ".join(item.warnings)
            if "revised_once" in d.flags:
                flag += "  ↻ corrected once after validator feedback"
            print(f"{d.criterion_id:<4} {d.sufficiency:<12} score={d.provisional_score!s:<5} of {d.score_max:<4} "
                  f"evidence={d.evidence_ids}{flag}")
            print(f"     {d.explanation}")
            if d.draft_feedback:
                print(f"     feedback: {d.draft_feedback}")
            for u in result.retrieved.get(d.criterion_id, []):
                if u.id in d.evidence_ids:
                    print(f"     {u.id} {u.locator}: {u.text[:110]}…")
        if args.auto_accept:
            session = result.review_session()
            for item in result.assessments:
                cid = item.draft.criterion_id
                can_accept = item.accepted and item.draft.provisional_score is not None and item.draft.sufficiency != "insufficient"
                session.decide(cid, "accepted" if can_accept else "rejected", comment="auto")
            print(session.export_json())
        return 0

    if args.cmd == "eval":
        report = evaluate_corpus(DATASET, gateway=gateway, k=args.k, repeats=args.repeats, split=args.split,
                                 log_path=args.log, with_baseline=not args.no_baseline, evidence_mode=args.evidence_mode,
                                 labels_path=DATASET / args.labels)
        if args.json:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        if args.report:
            write_markdown_report(report, args.report)
            print(f"wrote {args.report}")
        if not args.report and not args.json:
            print(json.dumps(report, indent=2))
        else:
            failing = [k for k, v in report["pass"].items() if v is False]
            unmeasured = [k for k, v in report["pass"].items() if v is None]
            print("all measured targets pass" if not failing else f"failing targets: {', '.join(failing)}")
            if unmeasured:
                print(f"unmeasured targets: {', '.join(unmeasured)}")
        return 0

    if args.cmd == "replay":
        entries = RunLogger(args.log).read()
        if not entries:
            sys.exit("empty log")
        ok = 0
        for e in entries:
            out = replay_entry(e, gateway=gateway)
            good = out.same_top1 and out.within_tolerance
            ok += int(good)
            print(f"{e.test_case_id:<20} {e.criterion_id:<4} top1_same={out.same_top1} cited_same={out.same_cited} "
                  f"drift={out.score_drift if out.score_drift is None else round(out.score_drift, 3)} {'OK' if good else 'DIFF'}")
        print(f"repeatable {ok}/{len(entries)} = {ok / len(entries):.3f} (target ≥ 0.90)")
        return 0 if ok / len(entries) >= 0.90 else 1

    if args.cmd == "baseline":
        rubric = _resolve("rubric", args.rubric)
        submission = _resolve("submission", args.submission)
        _, drafts = run_direct_baseline(rubric, submission, gateway=gateway, rubric_id=rubric.stem)
        print(f"B2 direct grading with {gateway.name} (no evidence IDs, whole document in one call)")
        for d in drafts:
            print(f"{d.criterion_id:<4} {d.sufficiency:<12} score={d.provisional_score!s:<5} {d.explanation}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

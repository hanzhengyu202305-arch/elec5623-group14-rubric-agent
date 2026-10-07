# Named team delivery plan

Updated 7 October 2026. **Piece 4 is claimed. The other four pieces are
still a proposal, pending each member's confirmation.** Nothing here says the
work is done, or that anyone has authored the remaining evidence. What has
actually been committed is
generated from git history in `CONTRIBUTIONS.md`; read that for the record and
this for the plan. The A2 rubric awards group marks, so this is work
prioritisation, not an individual mark guarantee.

Everyone commits under their own GitHub account, so each person's contribution
appears in the history under their own name. Nobody commits on anyone else's
behalf. The repository is public; uploading a finished annotation sheet is
still a write, so the uploader needs collaborator access.

Code, the frozen campaign and the robustness run are already done and
disclosed as AI-assisted. They are not one of the five tasks below. What
remains is human work, split into five pieces of about two hours. **Piece 4
is claimed; the paper note is not written.** The other four pieces have no
names until someone claims one in the group chat. One person, one piece.

## What the tutor still marks

The build, the frozen configuration and the development-corpus campaign are already in the repository. They cover product completeness, the GenAI architecture and Track A. Haolin Jin's proposal comments, and the A2 rubric in `ELEC5623_A2.pdf`, still require the evidence below. The five pieces are that evidence. If one piece is missing, the report has to say "not measured" for the corresponding marks.

| A2 criterion | Marks | Piece that supplies it | Not acceptable as a substitute |
|---|---:|---|---|
| Evaluation, evidence and critical analysis | 4 | 1 and 2, then the frozen final-test run; piece 5's citation check | fixture numbers, the September run, or labels written by the model |
| Product quality and user workflow | 2 | 3, with both the tool arm and the rubric-only arm | a demo with no timed person |
| Novelty and positioning | 3 | 4, checked against the papers rather than the report's own summary | a claim that evidence-first scoring is ours |
| Documentation and team delivery | 1 | 5's snag log, plus each person committing under their own account | a table of names with no file behind it |

GenAI engineering (4) and Track A alignment (2) are already demonstrated by the frozen system. They do not need a sixth piece. After the five pieces exist, the report is updated from those files: new numbers replace the development-corpus table, missed targets stay missed, and §10 names only people who committed something. That update is disclosed AI assistance. It is not a substitute for the five pieces.

## The five open tasks

| Piece | About | Hours | What to hand in |
|---|---|---:|---|
| **1. 标注 A** | Read 6 short reports and fill 27 rows. Sufficiency and score are separate questions. Do not look at any model output or at the other sheet. | 2 | `dataset/final_test/annotation/annotator_A.csv`, your name and dates in `REGISTER.md` |
| **2. 标注 B** | The same 27 rows, filled alone. Same rules. | 2 | `annotator_B.csv`, your name and dates in `REGISTER.md` |
| **3. 试用** | Two people use the review screen. Time each person twice: once with the tool, once with the rubric only. Save both times, how often they changed a score, and screenshots of the current screen. Say they are classmates, not professional markers. | 2 | `docs/sessions/*.json` plus the screenshots. Instructions: `docs/MARKER_SESSIONS.md` |
| **4. 核对论文** | Claimed by Yutong Liu (`yliu0744@uni.sydney.edu.au`); the note is not written. Open Evidence-First Scoring, GradeAgentOps and RULERS from the links in `docs/RELATED_WORK.md`. Check that report §3 matches each paper. Write what overlaps and what is only ours. Do not write that we beat those papers. | 2 | a short note committed under her own account, and the ability to say that note aloud on 4 November |
| **5. 跑通并核对引用** | On your own laptop, follow `README.md` only and log every snag. Then fill `docs/faithfulness/sample_blank.csv`: for each of the 30 sentences, does the cited passage actually support that sentence? Judge the passage, not whether the score feels right. | 2 | the snag log and the completed faithfulness sheet, under your account |

### Claims

Only piece 4 has a name. Pieces 1, 2, 3 and 5 are unclaimed.

**Piece 4 — Yutong Liu** (`yliu0744@uni.sydney.edu.au`), pending her acceptance of the GitHub collaborator invite. The email is matched to her from the unikey: `yliu0744` is `yliu` plus digits, which fits Yutong Liu. The other women in Group 14 are Yuchun Zheng and Zhaoxinyi Zhou, whose unikeys would not start with `yliu`. GitHub matched that email to the account **Yutong-Liu-07** and the invite grants write access, which is permission to push. Accepting the invite is not the paper note. She still has to open Evidence-First Scoring, GradeAgentOps and RULERS herself and commit a short note under her own account. That note must not say this project beats those papers.

Pieces 1 and 2 must be two different people. Fill the sheet before you can
see the other one. Do not post either CSV in the group chat. Tell the chat
only that you are finished, send the file privately to Zhengyu Han, and upload
it after both sheets exist. Agreement is computed from those untouched files
before anyone discusses a disagreement.

Showing up at the Week 10 oral, the Week 12 oral and the 4 November
presentation is separate. Those are individual, and AI is not allowed in the
room. Picking a piece above does not replace being able to say, in one
sentence, what this tool does.

## Why the two annotation sheets stay apart

The two annotations are independent only if neither person can see the other's
answers. The agreement statistic is the only independent evidence this project
will have about its reference labels. The repository is public, so uploading
one sheet immediately shows it to the other person. Send the file privately
first. Upload both only after both exist, then compute agreement before any
discussion.

1. Two different people complete the two sheets offline.
2. Each sends the CSV privately to Zhengyu Han and says "done" in the chat, without attaching it.
3. Both files are uploaded, then `scripts/adjudicate_annotations.py agreement` runs on the untouched originals. `agreement.json` is committed before anyone discusses a disagreement.
4. Adjudication, then `build`, then the frozen final-test campaign.

A packaged copy of the blank sheet and a Chinese instruction sheet lives
outside the repository at `5623/标注包_final_test/`. The sheet survives Excel's
"CSV UTF-8" byte-order mark, which is tested.

## Each piece, in enough detail to start

**1 and 2 — the two sheets.** Read `annotation/INSTRUCTIONS.txt` once, then fill `sufficiency`, `score` and `rationale` for all 27 rows. Sufficiency is about whether the evidence lets a marker pick a descriptor, not about whether the work is good. Clearly documented weak work is `sufficient` evidence for a **low** score. Do not look at any model output or at the development corpus labels. Do not use an AI to choose the labels.

**3 — sessions.** `docs/MARKER_SESSIONS.md` has the protocol, the consent note to read verbatim, and the questionnaire. Each participant must **also** mark a submission with the rubric alone, timed, or M10 cannot be computed at all. Record sessions as `docs/sessions/<participant>_<arm>.json` from `TEMPLATE.json`, then run `scripts/summarise_sessions.py`.

**4 — the three papers.** Claimed by Yutong Liu; the note is not written. See Claims above. Open Evidence-First Scoring (Cai 2026), GradeAgentOps (Anghel et al. 2026) and RULERS (Hong et al. 2026a/b) from the links in `RELATED_WORK.md`. The proposal lost a mark for claiming novelty that prior work already had. The useful result is a correction, not a bigger claim. She opens the papers herself. The note must not say this project beats those papers.

**5 — another computer, then the 30 sentences.** Follow the README exactly. The CI break fixed on 7 October was this class of defect (`pytest` behaved differently from `python -m pytest`). Report what happened rather than working around it silently. The faithfulness sheet is `docs/faithfulness/sample_blank.csv`. A yes means the cited passage supports the sentence. Do not use a model to answer, and do not treat a matching evidence id as enough.

## What an AI assistant cannot supply

Stated plainly because the rest of the build is AI-assisted and disclosed, and
the boundary is what makes the disclosure meaningful.

- **Independent human labels.** Two people must read the 27 pairs separately.
  An AI filling either sheet would destroy the only independent evidence about
  our reference labels.
- **The manual faithfulness judgements.** `docs/faithfulness/sample_blank.csv`
  is deliberately blank. A model judging whether its own citation supports its
  own claim is not human evidence.
- **Real marker timings and observations.** A stopwatch on a real person.
- **Teammates' acceptance of these roles.** Piece 4 has a claimant. The other
  four pieces stay a proposal until that person says yes.
- **The live assessments.** AI is prohibited in the Week 10, Week 12 and Week 13
  rooms, so the explanation has to be genuinely understood.

## Proposed milestones (internal targets, not school deadlines)

| Target | Output | Who |
|---|---|---|
| ~~7 Oct~~ **done** | code and prompts frozen (`FREEZE.md`); A/B2/B3 campaign run; robustness experiment predeclared and run; CheckList cited | Han |
| 10 Oct | both annotators have claimed pieces 1 and 2 and started offline | whoever claims them |
| 14 Oct | both sheets received privately; `agreement.json` committed from the untouched originals, before any discussion | the two annotators, then Han runs agreement |
| 21 Oct | piece 3 sessions, piece 4 paper note, piece 5 snag log and faithfulness sheet | piece 4: Yutong Liu; pieces 3 and 5: whoever claims them |
| 24 Oct | frozen final-test campaign on the adjudicated labels; report §§7–10 rewritten from the new files only | disclosed AI assistance, after the five pieces, not instead of them |
| 29 Oct | contribution register regenerated; each named person matches a commit | all five |
| 1 Nov | clean-clone rehearsal on the submission package; demo rehearsal without AI | all five |
| 3 Nov 23:59 | source plus report submitted | Han |
| 4 Nov | presentation and Q&A, no AI | all five |

Week 10 (14 Oct) and Week 12 (28 Oct) labs hold interactive orals. Confirm
their scope with the tutor; AI is prohibited in them.

The A2 brief states source code plus one report due 3 November 2026 23:59, and
presentation/Q&A on 4 November. Recheck the final Canvas brief before
submission, since the presentation format was to be released separately.

## Actual contribution register

**Do not hand-write this table.** It is generated from git history:

```sh
.venv/bin/python scripts/contribution_register.py --markdown   # writes docs/CONTRIBUTIONS.md
```

`docs/CONTRIBUTIONS.md` lists, per member, the number of commits, the files
touched, the ownership areas those files fall into, and every commit SHA with
its date and subject. A marker can check any line of it with `git show`. This
is the answer to the proposal comment that work was not assigned to named
people: not a better-worded table, a verifiable one.

As of 7 October 2026 the register shows **all commits under one identity,
Zhengyu Han**. The other four members have no committed contribution evidence
in this repository yet. That is the honest state, and it is what the report
must say until it changes.

### How each member creates evidence

A task assignment is not evidence. An AI-generated file is not evidence that
the assigned person did the work. Do not commit under another person's name.

| Piece | What produces verifiable evidence |
|---|---|
| 1 and 2 | the completed sheet plus the person's name and dates in `REGISTER.md`, committed by that person |
| 3 | `docs/sessions/*.json` for both arms, and screenshots, committed by the facilitator |
| 4 | a note naming the three papers and the sentences checked, committed by that person |
| 5 | a snag log and `docs/faithfulness/sample_blank.csv` with `supported` filled, committed by that person |
| Already done | the frozen build, under Zhengyu Han, disclosed as AI-assisted in `AI_USE.md` |

Work that leaves no commit still counts, but it has to leave *some* artifact:
an annotation sheet, a session record, a campaign manifest. Each of those names
a person, and each is referenced from the report.

### First step for the other four

Each member clones the repository, configures their own `user.name` and
`user.email`, does their piece on a branch, and pushes it. Then add their git
identity to `MEMBERS` in `scripts/contribution_register.py` and regenerate.
Until their identity is listed there, their commits appear under "unmapped git
identities" rather than being silently credited to anyone.

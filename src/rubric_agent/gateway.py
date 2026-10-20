"""Model gateway: the only place a language model is called (Constraint C5).

Two implementations share one interface:

* `FixtureGateway` – deterministic, offline. Used by tests, CI and the default
  demo. It is a stand-in for a model, not a model; numbers produced with it
  demonstrate the *harness*, not model quality.
* `OpenAICompatibleGateway` – any `/chat/completions` endpoint (OpenAI, Azure
  AI Foundry, Ollama, vLLM, OpenRouter, ...). Configured from environment
  variables so the key never lives in code or logs. All failures are
  fail-closed: a bad response becomes an `insufficient` record with a flag,
  never a score.

Both expose `assess()` (agent path, per criterion, evidence only) and
`grade_direct()` (baseline B2: whole rubric + whole document in one call).
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from collections.abc import Callable

from pydantic import ValidationError

from . import PROMPT_VERSION
from .resources import resource_directory
from .schemas import AssessmentDraft, Criterion, EvidenceUnit, Rubric
from .textutil import citation_ids, sentences
from .textutil import stemmed_tokens as content_tokens

PROMPTS_DIR = resource_directory("prompts")

NEGATION_CUES = (
    " does not ", " do not ", " did not ", " is not ", " are not ", " no ", " not ",
    " without a ", " without an ", " without specifying", " without describing", " without discussion",
    " without priority", " omitted", " only as a keyword", " somehow", " pending", " is empty",
    " anecdotal", " hinted", " drifts", " decoy", " unrelated", " must not be treated",
)

Transport = Callable[[str, dict[str, str], bytes, float], str]


class ModelGateway(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def assess(self, criterion: Criterion, evidence: list[EvidenceUnit]) -> AssessmentDraft: ...

    @abstractmethod
    def grade_direct(self, rubric: Rubric, full_text: str) -> list[AssessmentDraft]: ...

    def revise(
        self,
        criterion: Criterion,
        evidence: list[EvidenceUnit],
        previous: AssessmentDraft,
        warnings: list[str],
    ) -> AssessmentDraft | None:
        """Optional single corrective round after a validator rejection.

        Returns a new draft, or None when the gateway cannot revise (fixture).
        The pipeline validates the revision again; nothing is trusted on faith.
        """
        return None


def rejected(criterion: Criterion, reason: str, flag: str) -> AssessmentDraft:
    """Fail-closed record used whenever the model output cannot be trusted."""
    return AssessmentDraft(
        criterion_id=criterion.id,
        evidence_ids=[],
        sufficiency="insufficient",
        provisional_score=None,
        score_max=criterion.max_mark,
        explanation=f"Insufficient evidence: model output rejected ({reason}).",
        flags=[flag],
    )


def snap(value: float, criterion: Criterion) -> float:
    step = criterion.granularity
    snapped = round(round(value / step) * step, 4)
    return max(0.0, min(criterion.max_mark, snapped))


# --- Fixture ------------------------------------------------------------------


class FixtureGateway(ModelGateway):
    """Descriptor-matching heuristic. Deterministic; never sees gold labels.

    For each criterion it compares the retrieved evidence against every level
    descriptor and picks the level whose wording is best matched by sentences
    that do not contain a negation cue. `fail_mode` reproduces S6 faults.
    """

    def __init__(self, *, fail_mode: str | None = None, name: str = "fixture-descriptor-v2") -> None:
        self.fail_mode = fail_mode
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    # -- agent path -----------------------------------------------------------

    def assess(self, criterion: Criterion, evidence: list[EvidenceUnit]) -> AssessmentDraft:
        if self.fail_mode == "unknown_id":
            return AssessmentDraft(
                criterion_id=criterion.id, evidence_ids=["E-999"], sufficiency="sufficient",
                provisional_score=criterion.max_mark, score_max=criterion.max_mark,
                explanation="Supported by [E-999].",
            )
        if self.fail_mode == "out_of_range":
            eid = evidence[0].id if evidence else "E-001"
            return AssessmentDraft(
                criterion_id=criterion.id, evidence_ids=[eid], sufficiency="sufficient",
                provisional_score=criterion.max_mark + 2, score_max=criterion.max_mark,
                explanation=f"Over-scored using [{eid}].",
            )
        if self.fail_mode == "uncited_claim":
            eid = evidence[0].id if evidence else "E-001"
            return AssessmentDraft(
                criterion_id=criterion.id, evidence_ids=[eid], sufficiency="sufficient",
                provisional_score=criterion.max_mark, score_max=criterion.max_mark,
                explanation="The submission fully addresses this criterion. It is excellent.",
            )
        if self.fail_mode == "invalid_json":
            return rejected(criterion, "not valid JSON", "invalid_model_output")
        if not evidence:
            return AssessmentDraft(
                criterion_id=criterion.id, evidence_ids=[], sufficiency="insufficient",
                provisional_score=None, score_max=criterion.max_mark,
                explanation="No relevant evidence found for this criterion.",
                flags=["no_relevant_evidence"],
            )
        return self._descriptor_match(criterion, evidence)

    def _descriptor_match(self, criterion: Criterion, evidence: list[EvidenceUnit]) -> AssessmentDraft:
        name_terms = set(content_tokens(criterion.name))
        # Support per unit = overlap of *affirmative* sentences with upper descriptors.
        level_hits: dict[float, set[str]] = {d.score: set() for d in criterion.descriptors}
        unit_support: list[tuple[float, EvidenceUnit]] = []
        for unit in evidence:
            affirm = [s for s in sentences(unit.text) if not _negated(s)]
            affirm_terms = set(content_tokens(" ".join(affirm)))
            best_here = 0.0
            for d in criterion.descriptors:
                if d.score <= 0:
                    continue
                d_terms = set(content_tokens(d.text)) - name_terms
                if not d_terms:
                    continue
                hit = affirm_terms & d_terms
                if hit:
                    level_hits[d.score] |= hit
                    best_here = max(best_here, len(hit) / len(d_terms))
            unit_support.append((best_here, unit))

        supported = sorted([(s, u) for s, u in unit_support if s > 0], key=lambda x: (-x[0], x[1].id))
        if not supported:
            return AssessmentDraft(
                criterion_id=criterion.id, evidence_ids=[], sufficiency="insufficient",
                provisional_score=None, score_max=criterion.max_mark,
                explanation=f"Insufficient evidence: the retrieved units do not address {criterion.name.lower()}.",
                flags=["insufficient_evidence"],
            )
        cited = [u.id for _, u in supported[:3]]
        cites = " ".join(f"[{i}]" for i in cited)
        # Level = highest descriptor whose distinctive wording is at least half covered.
        chosen: float = 0.0
        for d in sorted(criterion.descriptors, key=lambda d: d.score):
            d_terms = set(content_tokens(d.text)) - name_terms
            if d.score > 0 and d_terms and len(level_hits[d.score]) / len(d_terms) >= 0.5:
                chosen = d.score
        if chosen <= 0:
            chosen = snap(criterion.max_mark * 0.5, criterion) if supported[0][0] >= 0.25 else snap(criterion.granularity, criterion)
        sufficiency = "sufficient" if chosen >= criterion.max_mark else "partial"
        level_text = next((d.text for d in criterion.descriptors if d.score == chosen), "")
        level_text = level_text.rstrip(".").split(";")[0][:120]
        return AssessmentDraft(
            criterion_id=criterion.id, evidence_ids=cited, sufficiency=sufficiency,
            provisional_score=chosen, score_max=criterion.max_mark,
            explanation=f"The submission addresses {criterion.name.lower()} in {cites}. "
                        f"The evidence best matches the level '{level_text}' {cites}.",
            draft_feedback=f"For {criterion.name.lower()}, build on {cites}"
                           + ("" if sufficiency == "sufficient" else " and address the higher-level descriptor.") ,
        )

    # -- baseline B2 ------------------------------------------------------------

    def grade_direct(self, rubric: Rubric, full_text: str) -> list[AssessmentDraft]:
        """Whole-document keyword grader: no evidence IDs, no negation handling.

        Mimics what a naive one-shot 'grade this' prompt tends to do, and gives
        the harness something to compare the agent's grounding against (M6, M8).
        """
        doc_terms = set(content_tokens(full_text))
        out = []
        for c in rubric.criteria:
            name_terms = set(content_tokens(c.name))
            chosen = 0.0
            for d in sorted(c.descriptors, key=lambda d: d.score):
                d_terms = set(content_tokens(d.text)) - name_terms
                if d.score > 0 and d_terms and len(doc_terms & d_terms) / len(d_terms) >= 0.5:
                    chosen = d.score
            if chosen <= 0:
                chosen = snap(c.granularity, c) if name_terms & doc_terms else 0.0
            suff = "sufficient" if chosen >= c.max_mark else ("partial" if chosen > 0 else "insufficient")
            out.append(AssessmentDraft(
                criterion_id=c.id, evidence_ids=[], sufficiency=suff,
                provisional_score=chosen if suff != "insufficient" else None, score_max=c.max_mark,
                explanation=f"The document covers {c.name.lower()} at level {chosen}. The relevant material is present in the report.",
            ))
        return out


def _negated(sentence: str) -> bool:
    low = f" {sentence.lower()} "
    return any(cue in low for cue in NEGATION_CUES)


# --- Live, OpenAI-compatible ------------------------------------------------------


def _urllib_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> str:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (endpoint is operator-configured)
        return resp.read().decode("utf-8")


class OpenAICompatibleGateway(ModelGateway):
    """Chat-completions client for hosted (OpenAI/Azure) or local (Ollama/vLLM) models.

    Environment variables (see docs/GOVERNANCE.md):
      RMA_MODEL_ENDPOINT   base URL, e.g. https://api.openai.com/v1
                           or https://<res>.openai.azure.com/openai/deployments/<dep>
                           or http://localhost:11434/v1
      RMA_MODEL            model / deployment name
      RMA_MODEL_API_KEY    secret; read once, never logged
      RMA_API_KEY_HEADER   'authorization' (default) or 'api-key' (Azure)
      RMA_API_VERSION      appended as ?api-version= (Azure only)
    """

    def __init__(
        self,
        *,
        endpoint: str,
        model: str,
        api_key: str | None,
        key_header: str = "authorization",
        api_version: str | None = None,
        temperature: float = 0.0,
        timeout: float = 180.0,
        max_tokens: int = 700,
        max_retries: int = 1,
        transport: Transport | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self._api_key = api_key
        self.key_header = key_header.lower()
        self.api_version = api_version
        self.temperature = temperature
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self._transport = transport or _urllib_transport
        self.last_error: str | None = None
        self.last_attempts = 0
        self._last_raw = ""

    @property
    def name(self) -> str:
        host = re.sub(r"^https?://", "", self.endpoint).split("/")[0]
        return f"{self.model}@{host}"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None, **kw) -> OpenAICompatibleGateway:
        env = env if env is not None else os.environ
        endpoint = env.get("RMA_MODEL_ENDPOINT")
        model = env.get("RMA_MODEL")
        if not endpoint or not model:
            raise RuntimeError("RMA_MODEL_ENDPOINT and RMA_MODEL must be set for a live gateway")
        return cls(
            endpoint=endpoint,
            model=model,
            api_key=env.get("RMA_MODEL_API_KEY"),
            key_header=env.get("RMA_API_KEY_HEADER", "authorization"),
            api_version=env.get("RMA_API_VERSION") or None,
            **kw,
        )

    # -- prompt construction ------------------------------------------------------

    @staticmethod
    def render_assessment_prompt(criterion: Criterion, evidence: list[EvidenceUnit]) -> tuple[str, str]:
        system = (PROMPTS_DIR / f"{PROMPT_VERSION}.md").read_text(encoding="utf-8")
        payload = {
            "criterion": {
                "id": criterion.id,
                "name": criterion.name,
                "max_mark": criterion.max_mark,
                "granularity": criterion.granularity,
                "levels": [{"score": d.score, "descriptor": d.text} for d in criterion.descriptors],
            },
            "evidence": [
                {"id": u.id, "page": u.page, "section": u.section, "text": u.text} for u in evidence
            ],
            "allowed_evidence_ids": [u.id for u in evidence],
            "output_schema": {
                "criterion_id": "string, must equal criterion.id",
                "evidence_ids": "array of strings drawn only from allowed_evidence_ids",
                "sufficiency": "one of: sufficient, partial, insufficient",
                "provisional_score": "number on the rubric scale (multiple of granularity, <= max_mark), or null when insufficient",
                "score_max": "number, must equal criterion.max_mark",
                "explanation": "string; every sentence that asserts something about the submission ends with one or more [E-00N] citations",
                "draft_feedback": "string or null",
                "flags": "array of strings, usually empty",
            },
            "format_example_for_a_DIFFERENT_criterion": {
                "_note": "Shows the shape only. Write your own explanation about THIS criterion and THIS evidence.",
                "criterion_id": "X9",
                "evidence_ids": ["E-042", "E-043"],
                "sufficiency": "partial",
                "provisional_score": 1.0,
                "score_max": 3.0,
                "explanation": "The safety section lists two hazards [E-042]. No mitigation is described for either hazard [E-043].",
                "draft_feedback": "Add a mitigation for each hazard listed in [E-042].",
                "flags": [],
            },
        }
        return system, json.dumps(payload, ensure_ascii=False, indent=1)

    MAX_DIRECT_CHARS = 48_000  # ~12k tokens; longer documents are truncated, as a one-shot grader would be

    @classmethod
    def render_direct_prompt(cls, rubric: Rubric, full_text: str) -> tuple[str, str]:
        system = (PROMPTS_DIR / "direct_grading_v1.md").read_text(encoding="utf-8")
        if len(full_text) > cls.MAX_DIRECT_CHARS:
            full_text = full_text[: cls.MAX_DIRECT_CHARS] + "\n[document truncated for context length]"
        payload = {
            "criterion_ids": [c.id for c in rubric.criteria],
            "rubric": [
                {"id": c.id, "name": c.name, "max_mark": c.max_mark,
                 "levels": [{"score": d.score, "descriptor": d.text} for d in c.descriptors]}
                for c in rubric.criteria
            ],
            "submission": full_text,
        }
        return system, json.dumps(payload, ensure_ascii=False)

    # -- calls ----------------------------------------------------------------------

    def _chat(self, system: str, user: str, *, extra_messages: list[dict] | None = None) -> str:
        url = f"{self.endpoint}/chat/completions"
        if self.api_version:
            url += f"?api-version={self.api_version}"
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            if self.key_header == "api-key":
                headers["api-key"] = self._api_key
            else:
                headers["Authorization"] = f"Bearer {self._api_key}"
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}, *(extra_messages or [])]
        body = json.dumps({
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
            "messages": messages,
        }).encode("utf-8")
        raw = self._transport(url, headers, body, self.timeout)
        data = json.loads(raw)
        return data["choices"][0]["message"]["content"]

    def assess(self, criterion: Criterion, evidence: list[EvidenceUnit]) -> AssessmentDraft:
        """One call, plus at most one corrective retry when the output violates the schema.

        The retry feeds the rejection reason back as a message (Lab 6: preserve
        the error). If the second answer is also invalid the record stays rejected.
        """
        self.last_error = None
        self.last_attempts = 0
        system, user = self.render_assessment_prompt(criterion, evidence)
        extra: list[dict] = []
        draft = rejected(criterion, "no attempt", "provider_error")
        for _ in range(1 + self.max_retries):
            self.last_attempts += 1
            try:
                content = self._chat(system, user, extra_messages=extra)
            except (urllib.error.URLError, OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
                self.last_error = f"{type(exc).__name__}"
                return rejected(criterion, f"provider error: {type(exc).__name__}", "provider_error")
            draft = parse_model_json(content, criterion)
            if "invalid_model_output" not in draft.flags:
                break
            extra = [
                {"role": "assistant", "content": content},
                {"role": "user", "content": f"Rejected: {draft.explanation} Return only the JSON object that matches output_schema."},
            ]
        self._last_raw = content if "content" in locals() else ""
        return draft

    def revise(self, criterion, evidence, previous, warnings):
        system, user = self.render_assessment_prompt(criterion, evidence)
        problems = "; ".join(warnings)
        feedback = (
            f"The validator rejected your answer: {problems}. "
            "Fix only these problems: cite an allowed [E-00N] at the end of every sentence that asserts something about "
            "the submission, use only IDs from allowed_evidence_ids, keep the score on the rubric scale, and return "
            "insufficient with a null score if the evidence does not support the criterion. Return only the JSON object."
        )
        extra = [
            {"role": "assistant", "content": previous.model_dump_json()},
            {"role": "user", "content": feedback},
        ]
        try:
            content = self._chat(system, user, extra_messages=extra)
        except (urllib.error.URLError, OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
            self.last_error = f"{type(exc).__name__}"
            return None
        self.last_attempts += 1
        return parse_model_json(content, criterion)

    def grade_direct(self, rubric: Rubric, full_text: str) -> list[AssessmentDraft]:
        system, user = self.render_direct_prompt(rubric, full_text)
        try:
            content = self._chat(system, user)
            items = _direct_items(json.loads(_strip_fences(content)))
            if len(items) < len(rubric.criteria):  # one re-ask, same as the agent path
                content = self._chat(system, user, extra_messages=[
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": f"Rejected: expected {len(rubric.criteria)} items, one per criterion id, "
                                                "inside {\"criteria\": [...]}. Return only that JSON object."},
                ])
                items = _direct_items(json.loads(_strip_fences(content)))
            out = []
            for c in rubric.criteria:
                item = next((i for i in items if isinstance(i, dict) and str(i.get("criterion_id")) == c.id), None)
                if item is None:
                    out.append(rejected(c, "criterion missing from direct output", "invalid_model_output"))
                    continue
                item.setdefault("evidence_ids", [])
                item.setdefault("score_max", c.max_mark)
                out.append(parse_model_json(json.dumps(item), c))
            return out
        except Exception as exc:  # noqa: BLE001 - baseline must never crash an evaluation
            return [rejected(c, f"provider error: {type(exc).__name__}", "provider_error") for c in rubric.criteria]


def _direct_items(data: object) -> list[dict]:
    """Accept the shapes one-shot graders actually return for B2.

    `{"criteria": [...]}` (requested), a bare list, a single criterion object,
    or a dict keyed by criterion id.
    """
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("criteria", "assessments", "results", "items"):
        if isinstance(data.get(key), list):
            return [d for d in data[key] if isinstance(d, dict)]
    if "criterion_id" in data:
        return [data]
    out = []
    for key, value in data.items():
        if isinstance(value, dict):
            out.append({"criterion_id": value.get("criterion_id", key), **value})
    return out


def _strip_fences(content: str) -> str:
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    return re.sub(r"\s*```$", "", content)


def parse_model_json(content: str, criterion: Criterion) -> AssessmentDraft:
    """Strict Listing 6.1 parse. Anything else is rejected (S6)."""
    try:
        data = json.loads(_strip_fences(content))
    except json.JSONDecodeError:
        return rejected(criterion, "not valid JSON", "invalid_model_output")
    if not isinstance(data, dict):
        return rejected(criterion, "JSON is not an object", "invalid_model_output")
    data.setdefault("criterion_id", criterion.id)
    data.setdefault("score_max", criterion.max_mark)
    data.setdefault("flags", [])
    if data.get("draft_feedback") in ("", "optional"):
        data["draft_feedback"] = None
    try:
        draft = AssessmentDraft.model_validate(data)
    except ValidationError as exc:
        field = exc.errors()[0].get("loc", ("?",))[0]
        return rejected(criterion, f"schema violation at '{field}'", "invalid_model_output")
    if draft.criterion_id != criterion.id:
        return rejected(criterion, "criterion_id mismatch", "invalid_model_output")
    return draft


# --- Factory -----------------------------------------------------------------------


OLLAMA_URL = "http://localhost:11434"
OPENROUTER_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"


def build_gateway(spec: str | None = None, *, env: dict[str, str] | None = None) -> ModelGateway:
    """`fixture`, `fixture:<fail_mode>`, `live` (RMA_* env), `ollama:<model>`, or `openrouter[:model]`.

    OpenRouter reads `RMA_OPENROUTER_API_KEY` at runtime. `RMA_OPENROUTER_MODEL`
    overrides the placeholder default; `--gateway openrouter:<model>` wins over that.
    """
    env = env if env is not None else os.environ
    spec = spec or env.get("RMA_GATEWAY", "fixture")
    if spec.startswith("fixture"):
        _, _, mode = spec.partition(":")
        return FixtureGateway(fail_mode=mode or None)
    if spec.startswith("ollama:"):
        model = spec.partition(":")[2]
        return OpenAICompatibleGateway(endpoint=env.get("RMA_OLLAMA_URL", OLLAMA_URL) + "/v1", model=model, api_key=None)
    if spec == "openrouter" or spec.startswith("openrouter:"):
        api_key = (env.get("RMA_OPENROUTER_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("RMA_OPENROUTER_API_KEY must be set for the OpenRouter gateway")
        model = spec.partition(":")[2].strip() or (env.get("RMA_OPENROUTER_MODEL") or "").strip() or DEFAULT_OPENROUTER_MODEL
        return OpenAICompatibleGateway(endpoint=OPENROUTER_URL, model=model, api_key=api_key)
    if spec in {"live", "openai", "azure", "ollama"}:
        return OpenAICompatibleGateway.from_env(env)
    raise ValueError(f"unknown gateway spec: {spec}")


def local_ollama_models(url: str = OLLAMA_URL, timeout: float = 1.0) -> list[str]:
    """Names of models served by a local Ollama instance; empty when none is running."""
    try:
        with urllib.request.urlopen(f"{url}/api/tags", timeout=timeout) as resp:  # noqa: S310 - fixed localhost URL
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return []
    return sorted(m.get("name", "") for m in data.get("models", []) if m.get("name"))


def explanations_grounded(draft: AssessmentDraft, allowed: set[str]) -> bool:
    cited = set(citation_ids(draft.explanation))
    extra = cited - allowed
    return not extra and (draft.sufficiency == "insufficient" or bool(cited))

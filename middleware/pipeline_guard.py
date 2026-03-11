"""
middleware/pipeline_guard.py — Safety guardrails for iterative pipelines.

Enforces hard limits on pipeline execution to prevent runaway loops,
unbounded cloud spend, and filesystem escape.

Heimdall Sprint 4 — these guardrails are imported by the pipeline plugin
and model-router plugin to enforce safety invariants.

Usage by plugins:
    from middleware.pipeline_guard import PipelineGuard, guard

    # At pipeline creation:
    g = guard.create_pipeline("pipeline-123", max_iterations=10)

    # Before each iteration:
    guard.check_iteration("pipeline-123")  # raises GuardError if exceeded

    # Before each stage:
    guard.check_stage_timeout("pipeline-123", "build")  # raises if overdue

    # Before cloud API call:
    guard.check_token_budget("pipeline-123", estimated_tokens=2000)

    # Validate build output path:
    guard.validate_build_path("/path/to/output", "pipeline-123")
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger("heimdall.pipeline_guard")


# ---------------------------------------------------------------------------
# Defaults (overridden by valhalla.yaml pipeline_guard section)
# ---------------------------------------------------------------------------

DEFAULT_MAX_ITERATIONS = 25           # Hard cap — no pipeline loops more than this
ABSOLUTE_MAX_ITERATIONS = 100         # Even config can't exceed this
DEFAULT_TOKEN_BUDGET = 500_000        # 500K tokens per pipeline (cloud calls)
DEFAULT_STAGE_TIMEOUT_S = 600         # 10 minutes per stage
DEFAULT_PIPELINE_TIMEOUT_S = 7200     # 2 hours total pipeline
MAX_ACTIVE_PIPELINES = 10             # Concurrency cap


class GuardError(Exception):
    """Raised when a safety invariant is violated."""
    pass


class IterationLimitError(GuardError):
    pass


class TokenBudgetError(GuardError):
    pass


class StageTimeoutError(GuardError):
    pass


class PipelineLimitError(GuardError):
    pass


class FilesystemEscapeError(GuardError):
    pass


# ---------------------------------------------------------------------------
# Pipeline tracking
# ---------------------------------------------------------------------------

class PipelineState:
    """Track iteration count, token spend, and timing for one pipeline."""

    def __init__(
        self,
        pipeline_id: str,
        max_iterations: int,
        token_budget: int,
        stage_timeout_s: int,
        pipeline_timeout_s: int,
        project_dir: Optional[Path] = None,
    ):
        self.pipeline_id = pipeline_id
        self.max_iterations = min(max_iterations, ABSOLUTE_MAX_ITERATIONS)
        self.token_budget = token_budget
        self.stage_timeout_s = stage_timeout_s
        self.pipeline_timeout_s = pipeline_timeout_s
        self.project_dir = project_dir

        self.iteration_count = 0
        self.tokens_used = 0
        self.created_at = time.monotonic()
        self.current_stage: Optional[str] = None
        self.stage_started_at: Optional[float] = None
        self.killed = False
        self.kill_reason: Optional[str] = None

    def to_dict(self) -> dict:
        elapsed = time.monotonic() - self.created_at
        return {
            "pipeline_id": self.pipeline_id,
            "iterations": self.iteration_count,
            "max_iterations": self.max_iterations,
            "tokens_used": self.tokens_used,
            "token_budget": self.token_budget,
            "elapsed_s": round(elapsed, 1),
            "pipeline_timeout_s": self.pipeline_timeout_s,
            "current_stage": self.current_stage,
            "killed": self.killed,
            "kill_reason": self.kill_reason,
        }


# ---------------------------------------------------------------------------
# Singleton guard
# ---------------------------------------------------------------------------

class PipelineGuard:
    """Central guardrail enforcer for all active pipelines."""

    def __init__(self):
        self._lock = threading.Lock()
        self._pipelines: dict[str, PipelineState] = {}
        self._config: dict = {}

    def configure(self, config: dict) -> None:
        """Load guard settings from valhalla.yaml."""
        self._config = config.get("pipeline_guard", {})
        log.info("[guard] Configured: max_iter=%d, token_budget=%d, stage_timeout=%ds",
                 self._get_max_iterations(),
                 self._get_token_budget(),
                 self._get_stage_timeout())

    def _get_max_iterations(self) -> int:
        v = self._config.get("max_iterations", DEFAULT_MAX_ITERATIONS)
        return min(int(v), ABSOLUTE_MAX_ITERATIONS)

    def _get_token_budget(self) -> int:
        return int(self._config.get("token_budget", DEFAULT_TOKEN_BUDGET))

    def _get_stage_timeout(self) -> int:
        return int(self._config.get("stage_timeout_seconds", DEFAULT_STAGE_TIMEOUT_S))

    def _get_pipeline_timeout(self) -> int:
        return int(self._config.get("pipeline_timeout_seconds", DEFAULT_PIPELINE_TIMEOUT_S))

    # --- Pipeline lifecycle ---

    def create_pipeline(
        self,
        pipeline_id: str,
        max_iterations: Optional[int] = None,
        token_budget: Optional[int] = None,
        project_dir: Optional[Path] = None,
    ) -> PipelineState:
        """Register a new pipeline with guardrails. Raises if concurrency limit hit."""
        with self._lock:
            active = sum(1 for p in self._pipelines.values() if not p.killed)
            if active >= MAX_ACTIVE_PIPELINES:
                raise PipelineLimitError(
                    f"Max {MAX_ACTIVE_PIPELINES} concurrent pipelines. "
                    f"Currently active: {active}"
                )

            max_iter = min(
                max_iterations or self._get_max_iterations(),
                ABSOLUTE_MAX_ITERATIONS,
            )

            state = PipelineState(
                pipeline_id=pipeline_id,
                max_iterations=max_iter,
                token_budget=token_budget or self._get_token_budget(),
                stage_timeout_s=self._get_stage_timeout(),
                pipeline_timeout_s=self._get_pipeline_timeout(),
                project_dir=project_dir,
            )
            self._pipelines[pipeline_id] = state

        log.info("[guard] Pipeline %s created (max_iter=%d, budget=%d tokens)",
                 pipeline_id, state.max_iterations, state.token_budget)
        return state

    def remove_pipeline(self, pipeline_id: str) -> None:
        """Clean up after pipeline completes or is cancelled."""
        with self._lock:
            self._pipelines.pop(pipeline_id, None)

    # --- Iteration check ---

    def check_iteration(self, pipeline_id: str) -> int:
        """Increment and check iteration count. Raises IterationLimitError if exceeded."""
        with self._lock:
            state = self._pipelines.get(pipeline_id)
            if not state:
                raise GuardError(f"Unknown pipeline: {pipeline_id}")

            if state.killed:
                raise GuardError(f"Pipeline {pipeline_id} already killed: {state.kill_reason}")

            state.iteration_count += 1

            if state.iteration_count > state.max_iterations:
                state.killed = True
                state.kill_reason = (
                    f"Iteration limit exceeded ({state.iteration_count}/{state.max_iterations})"
                )
                log.critical("[guard] 🔴 KILLED pipeline %s — %s",
                            pipeline_id, state.kill_reason)
                raise IterationLimitError(state.kill_reason)

            # Also check total pipeline timeout
            elapsed = time.monotonic() - state.created_at
            if elapsed > state.pipeline_timeout_s:
                state.killed = True
                state.kill_reason = (
                    f"Pipeline timeout exceeded ({elapsed:.0f}s > {state.pipeline_timeout_s}s)"
                )
                log.critical("[guard] 🔴 KILLED pipeline %s — %s",
                            pipeline_id, state.kill_reason)
                raise StageTimeoutError(state.kill_reason)

        return state.iteration_count

    # --- Stage timeout ---

    def start_stage(self, pipeline_id: str, stage_name: str) -> None:
        """Mark the start of a pipeline stage."""
        with self._lock:
            state = self._pipelines.get(pipeline_id)
            if state:
                state.current_stage = stage_name
                state.stage_started_at = time.monotonic()

    def check_stage_timeout(self, pipeline_id: str, stage_name: str) -> None:
        """Check if current stage has exceeded its timeout. Raises StageTimeoutError."""
        with self._lock:
            state = self._pipelines.get(pipeline_id)
            if not state or not state.stage_started_at:
                return

            elapsed = time.monotonic() - state.stage_started_at
            if elapsed > state.stage_timeout_s:
                state.killed = True
                state.kill_reason = (
                    f"Stage '{stage_name}' timeout ({elapsed:.0f}s > {state.stage_timeout_s}s)"
                )
                log.critical("[guard] 🔴 KILLED pipeline %s — %s",
                            pipeline_id, state.kill_reason)
                raise StageTimeoutError(state.kill_reason)

    # --- Token budget ---

    def check_token_budget(
        self, pipeline_id: str, estimated_tokens: int
    ) -> int:
        """Check that token spend hasn't exceeded budget. Returns remaining tokens."""
        with self._lock:
            state = self._pipelines.get(pipeline_id)
            if not state:
                raise GuardError(f"Unknown pipeline: {pipeline_id}")

            projected = state.tokens_used + estimated_tokens
            if projected > state.token_budget:
                state.killed = True
                state.kill_reason = (
                    f"Token budget exceeded ({projected:,} > {state.token_budget:,})"
                )
                log.critical("[guard] 🔴 KILLED pipeline %s — %s",
                            pipeline_id, state.kill_reason)
                raise TokenBudgetError(state.kill_reason)

            return state.token_budget - state.tokens_used

    def record_tokens(self, pipeline_id: str, tokens: int) -> None:
        """Record tokens consumed by a pipeline stage."""
        with self._lock:
            state = self._pipelines.get(pipeline_id)
            if state:
                state.tokens_used += tokens

    # --- Filesystem sandbox ---

    def validate_build_path(
        self, path: str, pipeline_id: str
    ) -> Path:
        """Validate that a build output path is within the project directory.

        Raises FilesystemEscapeError if the path escapes the sandbox.
        Returns the resolved absolute path.
        """
        with self._lock:
            state = self._pipelines.get(pipeline_id)
            if not state:
                raise GuardError(f"Unknown pipeline: {pipeline_id}")

        project_dir = state.project_dir
        if not project_dir:
            raise FilesystemEscapeError(
                f"No project_dir set for pipeline {pipeline_id}"
            )

        resolved = (project_dir / path).resolve()
        project_resolved = project_dir.resolve()

        # Check containment
        try:
            resolved.relative_to(project_resolved)
        except ValueError:
            log.critical(
                "[guard] 🔴 FILESYSTEM ESCAPE in pipeline %s: %s escapes %s",
                pipeline_id, resolved, project_resolved,
            )
            raise FilesystemEscapeError(
                f"Path '{path}' resolves to {resolved}, which is outside "
                f"project dir {project_resolved}"
            )

        # Block sensitive paths even within project
        BLOCKED_NAMES = {
            "valhalla.yaml", "config.json", ".env", ".git",
            "ca-key.pem", "ca.pem",
        }
        if resolved.name in BLOCKED_NAMES:
            raise FilesystemEscapeError(
                f"Path '{resolved.name}' is a protected file"
            )

        return resolved

    # --- Status ---

    def get_status(self) -> dict:
        """Return status of all tracked pipelines."""
        with self._lock:
            return {
                "active": sum(1 for p in self._pipelines.values() if not p.killed),
                "killed": sum(1 for p in self._pipelines.values() if p.killed),
                "max_concurrent": MAX_ACTIVE_PIPELINES,
                "pipelines": {
                    pid: state.to_dict()
                    for pid, state in self._pipelines.items()
                },
            }

    def is_killed(self, pipeline_id: str) -> bool:
        """Check if a pipeline has been killed."""
        with self._lock:
            state = self._pipelines.get(pipeline_id)
            return state.killed if state else False


# ---------------------------------------------------------------------------
# Crucible security helpers
# ---------------------------------------------------------------------------

# Patterns that indicate prompt injection in procedure text
_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "ignore the above",
    "disregard your instructions",
    "system prompt",
    "you are now",
    "act as",
    "pretend you are",
    "reveal your",
    "output your",
    "print your",
    "show me your",
    "repeat back",
    "what are your instructions",
    "what is your system",
    "```system",
    "[SYSTEM]",
    "\\n\\nHuman:",
    "\\n\\nAssistant:",
]

_INJECTION_PATTERNS_LOWER = [p.lower() for p in _INJECTION_PATTERNS]


def check_prompt_injection(text: str) -> tuple:
    """Check text for prompt injection patterns.

    Returns (is_suspicious: bool, matched_patterns: list[str]).
    """
    text_lower = text.lower()
    matched = [
        p for p in _INJECTION_PATTERNS
        if p.lower() in text_lower
    ]
    return bool(matched), matched


def validate_crucible_procedure(procedure: dict) -> tuple:
    """Validate a crucible procedure for security issues.

    Returns (is_safe: bool, issues: list[str]).
    """
    issues = []

    # Check procedure name
    name = procedure.get("name", "")
    if not name or len(name) > 256:
        issues.append("Invalid procedure name (empty or too long)")

    # Check procedure text for injection
    text = procedure.get("text", "") or procedure.get("description", "")
    is_suspicious, patterns = check_prompt_injection(text)
    if is_suspicious:
        issues.append(f"Prompt injection detected: {patterns}")

    # Check edge cases length
    edge_cases = procedure.get("edge_cases", [])
    if len(edge_cases) > 50:
        issues.append(f"Too many edge cases ({len(edge_cases)} > 50)")
    for i, ec in enumerate(edge_cases):
        if isinstance(ec, str) and len(ec) > 2000:
            issues.append(f"Edge case {i} too long ({len(ec)} chars)")
        if isinstance(ec, str):
            suspicious, _ = check_prompt_injection(ec)
            if suspicious:
                issues.append(f"Edge case {i} contains prompt injection")

    return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# Model Router security helpers
# ---------------------------------------------------------------------------

def validate_model_router_config(config: dict) -> tuple:
    """Validate model_router config for security issues.

    Returns (is_safe: bool, issues: list[str]).
    """
    issues = []
    router = config.get("model_router", {})

    # Check routing entries
    routing = router.get("routing", {})
    for task_type, model_spec in routing.items():
        if not isinstance(model_spec, str):
            issues.append(f"Invalid model spec for {task_type}: must be string")
            continue
        # Validate format: "provider/model" or "local/default"
        if "/" not in model_spec:
            issues.append(f"Invalid model spec '{model_spec}': must be provider/model")

    # Check that cloud API keys are NOT in the routing config
    # (they should only be in models.providers.*.key)
    router_str = str(router).lower()
    for pattern in ["api_key", "apikey", "secret", "password", "token"]:
        if pattern in router_str:
            issues.append(f"Potential API key in model_router config (found '{pattern}')")

    return len(issues) == 0, issues


def redact_api_keys(config: dict) -> dict:
    """Return a copy of config with API keys redacted for safe dashboard display.

    Used by GET /api/v1/model-router/stats to prevent key leakage.
    """
    import copy
    safe = copy.deepcopy(config)

    # Redact models.providers.*.key
    providers = safe.get("models", {}).get("providers", {})
    for name, provider in providers.items():
        if "key" in provider and provider["key"] not in ("local", ""):
            provider["key"] = "***REDACTED***"

    # Redact mesh.auth_token
    mesh = safe.get("mesh", {})
    if "auth_token" in mesh:
        mesh["auth_token"] = "***REDACTED***"

    # Redact dashboard.auth_key
    dash = safe.get("dashboard", {})
    if "auth_key" in dash:
        dash["auth_key"] = "***REDACTED***"

    return safe


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

guard = PipelineGuard()

"""
pipeline_templates.py — Template engine for customizable pipeline workflows.

Ships 3 built-in presets (Coding, Research, General) that work out of the box.
Users can create custom templates in ~/.valhalla/pipelines/*.yaml.

Templates use ROLES not agent names:
  - Multi-node: role → best mesh node via bot/router.py
  - Single-node: role → system prompt personality (sub-agent)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("valhalla.templates")

# ---------------------------------------------------------------------------
# Built-in presets — these ship by default
# ---------------------------------------------------------------------------

BUILTIN_TEMPLATES: dict[str, dict] = {
    "coding": {
        "name": "Coding",
        "version": 1,
        "description": "Build software with parallel backend/frontend and QA review",
        "icon": "⚡",
        "on_fail": "retry",  # default for all stages
        "stages": [
            {
                "name": "spec",
                "role": "planner",
                "prompt": (
                    "Generate a concise build spec for this project. Include: "
                    "1) File structure with exact paths "
                    "2) Key functions each file should contain "
                    "3) Any API contracts between components "
                    "4) Exact design values if UI is involved. "
                    "Keep under 400 words."
                ),
            },
            {
                "name": "build",
                "parallel": [
                    {
                        "role": "backend",
                        "prompt": "Build the backend following the spec. Report FILES and STATUS: DONE when complete.",
                    },
                    {
                        "role": "frontend",
                        "prompt": "Build the frontend following the spec. Report FILES and STATUS: DONE when complete.",
                    },
                ],
            },
            {
                "name": "test",
                "role": "tester",
                "on_fail": "goto:build",  # if tests fail, rebuild
                "prompt": (
                    "Run all tests and verify code quality. "
                    "End with VERDICT: PASS (all good) or VERDICT: FAIL (list each bug)."
                ),
            },
            {
                "name": "review",
                "role": "reviewer",
                "debate": True,
                "on_fail": "goto:test",  # if review fails, re-test
                "prompt": (
                    "Final quality review. Check completeness, edge cases, "
                    "and code quality. End with VERDICT: SHIP or VERDICT: IMPROVE."
                ),
            },
        ],
        "max_iterations": 3,
    },

    "research": {
        "name": "Research",
        "version": 1,
        "description": "Gather information, analyze patterns, write a clear summary",
        "icon": "🔍",
        "on_fail": "retry",
        "stages": [
            {
                "name": "gather",
                "role": "researcher",
                "prompt": (
                    "Research the topic thoroughly. Collect key facts, "
                    "data points, and different perspectives. Cite sources."
                ),
            },
            {
                "name": "analyze",
                "role": "analyst",
                "on_fail": "goto:gather",  # if analysis fails, re-research
                "prompt": (
                    "Analyze the gathered information. Identify patterns, "
                    "contradictions, and key insights. Be objective."
                ),
            },
            {
                "name": "write",
                "role": "writer",
                "prompt": (
                    "Write a clear, well-structured summary of findings. "
                    "Include key takeaways at the top. End with VERDICT: SHIP."
                ),
            },
        ],
        "max_iterations": 2,
    },

    "general": {
        "name": "General",
        "version": 1,
        "description": "Plan, execute, and review any task",
        "icon": "📋",
        "on_fail": "retry",
        "stages": [
            {
                "name": "plan",
                "role": "planner",
                "prompt": (
                    "Break this task into 2-4 concrete sub-tasks. For each, "
                    "specify what's needed and what the output should be."
                ),
            },
            {
                "name": "execute",
                "role": "executor",
                "prompt": (
                    "Execute each sub-task from the plan. Be thorough but concise. "
                    "Report what you did for each."
                ),
            },
            {
                "name": "review",
                "role": "reviewer",
                "debate": True,
                "on_fail": "goto:execute",  # if review fails, re-execute
                "prompt": (
                    "Review the execution results. Check for completeness and "
                    "accuracy. End with VERDICT: SHIP or VERDICT: FAIL."
                ),
            },
        ],
        "max_iterations": 2,
    },

    "drafting": {
        "name": "Drafting",
        "version": 1,
        "description": "Draft letters, emails, proposals, or documents",
        "icon": "✉️",
        "on_fail": "retry",
        "stages": [
            {
                "name": "context",
                "role": "researcher",
                "prompt": (
                    "Gather context for this document: who is the audience, "
                    "what is the purpose, what tone is appropriate, and what "
                    "key points must be included."
                ),
            },
            {
                "name": "draft",
                "role": "writer",
                "prompt": (
                    "Write the draft based on the context gathered. Match the "
                    "appropriate tone, be clear and professional. Include all "
                    "key points."
                ),
            },
            {
                "name": "review",
                "role": "reviewer",
                "debate": True,
                "on_fail": "goto:draft",
                "prompt": (
                    "Review the draft for tone, clarity, completeness, and "
                    "professionalism. Check for errors. End with VERDICT: SHIP "
                    "or VERDICT: IMPROVE with specific fixes."
                ),
            },
        ],
        "max_iterations": 2,
    },

    "presentation": {
        "name": "Presentation",
        "version": 1,
        "description": "Create presentations, slide decks, and pitch materials",
        "icon": "📊",
        "on_fail": "retry",
        "stages": [
            {
                "name": "outline",
                "role": "planner",
                "prompt": (
                    "Create a presentation outline: story arc, key slides, "
                    "main message per slide, and suggested data/visuals. "
                    "Think about the audience and what they need to take away."
                ),
            },
            {
                "name": "content",
                "role": "writer",
                "prompt": (
                    "Write the content for each slide: headlines, bullet points, "
                    "speaker notes, and data callouts. Keep slides concise — "
                    "max 5 bullets per slide."
                ),
            },
            {
                "name": "design",
                "role": "designer",
                "prompt": (
                    "Suggest visual design for each slide: layout type, "
                    "chart specifications, color emphasis, and image descriptions. "
                    "Focus on visual clarity and impact."
                ),
            },
            {
                "name": "review",
                "role": "reviewer",
                "debate": True,
                "on_fail": "goto:content",
                "prompt": (
                    "Review the full presentation for flow, messaging consistency, "
                    "and impact. End with VERDICT: SHIP or VERDICT: IMPROVE."
                ),
            },
        ],
        "max_iterations": 2,
    },

    "analysis": {
        "name": "Analysis",
        "version": 1,
        "description": "Analyze data, identify patterns, and produce reports",
        "icon": "📈",
        "on_fail": "retry",
        "stages": [
            {
                "name": "gather",
                "role": "researcher",
                "prompt": (
                    "Identify data sources, collect relevant data points, "
                    "and organize the raw information. Note data quality issues."
                ),
            },
            {
                "name": "analyze",
                "role": "data_analyst",
                "prompt": (
                    "Analyze the data: identify trends, patterns, outliers, "
                    "and statistical significance. Create charts and tables "
                    "where helpful."
                ),
            },
            {
                "name": "insights",
                "role": "analyst",
                "on_fail": "goto:analyze",
                "prompt": (
                    "Extract actionable insights from the analysis. What do "
                    "the numbers mean? What should the reader do differently? "
                    "Prioritize by impact."
                ),
            },
            {
                "name": "report",
                "role": "writer",
                "prompt": (
                    "Write an executive summary with key findings, supporting "
                    "data, and recommendations. Lead with the most important "
                    "insight. End with VERDICT: SHIP."
                ),
            },
        ],
        "max_iterations": 2,
    },
}

# ---------------------------------------------------------------------------
# Role → system prompt mapping (single-node sub-agent mode)
# ---------------------------------------------------------------------------

ROLE_PROMPTS: dict[str, str] = {
    "planner": (
        "You are a planning specialist. You break complex tasks into clear, "
        "actionable sub-tasks. You think about dependencies, order of operations, "
        "and potential blockers. Be structured and concise."
    ),
    "backend": (
        "You are a backend engineer. You build APIs, databases, server logic, "
        "and data pipelines. You write clean, testable code with proper error "
        "handling. You think about edge cases and security."
    ),
    "frontend": (
        "You are a frontend engineer. You build user interfaces, components, "
        "and client-side logic. You care about UX, accessibility, and "
        "responsive design. You write clean, maintainable code."
    ),
    "tester": (
        "You are a QA engineer. You test code thoroughly — unit tests, "
        "integration tests, edge cases, error handling. You report bugs "
        "precisely with file paths and line numbers."
    ),
    "reviewer": (
        "You are a quality reviewer. You check for completeness, accuracy, "
        "clarity, and professionalism. You provide actionable feedback with "
        "specific fixes, not vague criticism."
    ),
    "researcher": (
        "You are a research specialist. You find relevant information from "
        "multiple angles, evaluate source credibility, and organize findings "
        "systematically. You cite your sources."
    ),
    "analyst": (
        "You are a strategic analyst. You identify patterns, trends, and insights "
        "in information. You think critically, spot contradictions, and "
        "distinguish correlation from causation."
    ),
    "data_analyst": (
        "You are a data analyst. You work with numbers — statistics, trends, "
        "distributions, correlations. You create clear visualizations and "
        "tables. You flag data quality issues and confidence levels."
    ),
    "writer": (
        "You are a writing specialist. You produce clear, well-structured "
        "content. You lead with key takeaways, use concrete examples, "
        "and keep prose concise. You match tone to audience."
    ),
    "designer": (
        "You are a design specialist. You think visually — layouts, color, "
        "typography, visual hierarchy. You suggest specific design decisions "
        "and explain why they work for the audience."
    ),
    "executor": (
        "You are an execution specialist. You take plans and implement them "
        "efficiently. You handle each sub-task methodically, report progress, "
        "and flag blockers early."
    ),
}

# ---------------------------------------------------------------------------
# Template auto-detection — user just talks, system picks the right flow
# ---------------------------------------------------------------------------

_CODING_SIGNALS = [
    "build", "code", "implement", "develop",
    "api", "app", "website", "dashboard", "backend", "frontend",
    "database", "server", "endpoint", "component", "feature",
    "bug", "fix", "refactor", "migrate", "deploy", "test",
    "function", "class", "module", "library",
]

_RESEARCH_SIGNALS = [
    "research", "investigate", "find out", "what is", "how does",
    "compare", "study", "review the literature",
    "deep dive", "explore", "pros and cons", "evaluate options",
]

_DRAFTING_SIGNALS = [
    "draft", "write a letter", "write an email", "write a message",
    "compose", "proposal", "memo", "response to", "reply to",
    "cover letter", "resignation", "formal letter", "follow up",
    "apology", "thank you note", "invitation",
]

_PRESENTATION_SIGNALS = [
    "presentation", "slide", "deck", "powerpoint", "pitch",
    "keynote", "talk about", "present to", "board meeting",
    "stakeholder", "walkthrough", "demo for",
]

_ANALYSIS_SIGNALS = [
    "analyze data", "data analysis", "report on the numbers",
    "metrics", "kpi", "dashboard report", "quarterly",
    "trends", "sentiment", "performance review",
    "breakdown", "insights from", "forecast",
]


def classify_template(task: str) -> str:
    """Auto-detect the best template for a task. Zero latency.

    The user just talks — this picks the right pipeline automatically.
    """
    lower = task.lower().strip()

    scores = {
        "coding": sum(1 for s in _CODING_SIGNALS if s in lower),
        "research": sum(1 for s in _RESEARCH_SIGNALS if s in lower),
        "drafting": sum(1 for s in _DRAFTING_SIGNALS if s in lower),
        "presentation": sum(1 for s in _PRESENTATION_SIGNALS if s in lower),
        "analysis": sum(1 for s in _ANALYSIS_SIGNALS if s in lower),
    }

    # Pick the highest-scoring category
    best = max(scores, key=scores.get)
    if scores[best] >= 1:
        return best

    return "general"


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

def get_template(name: str) -> Optional[dict]:
    """Get a template by name. Checks user custom first, then built-in."""
    # User custom templates
    custom_dir = Path.home() / ".valhalla" / "pipelines"
    if custom_dir.exists():
        # Check for JSON
        json_path = custom_dir / f"{name}.json"
        if json_path.exists():
            try:
                return json.loads(json_path.read_text(encoding="utf-8"))
            except Exception as e:
                log.warning("Failed to load custom template %s: %s", name, e)

        # Check for YAML (if PyYAML available)
        yaml_path = custom_dir / f"{name}.yaml"
        if yaml_path.exists():
            try:
                import yaml
                return yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            except ImportError:
                # Try JSON-style YAML (subset that json can parse)
                log.debug("PyYAML not installed, skipping %s", yaml_path)
            except Exception as e:
                log.warning("Failed to load custom template %s: %s", name, e)

    # Built-in templates
    return BUILTIN_TEMPLATES.get(name)


def list_templates() -> list[dict]:
    """List all available templates (built-in + user custom).

    Returns list of {name, description, icon, stages_count, source} dicts.
    """
    results = []

    # Built-in
    for key, tmpl in BUILTIN_TEMPLATES.items():
        results.append({
            "name": key,
            "display_name": tmpl["name"],
            "description": tmpl["description"],
            "icon": tmpl["icon"],
            "stages": len(tmpl["stages"]),
            "max_iterations": tmpl.get("max_iterations", 3),
            "version": tmpl.get("version", 1),
            "source": "builtin",
        })

    # User custom
    custom_dir = Path.home() / ".valhalla" / "pipelines"
    if custom_dir.exists():
        for f in sorted(custom_dir.glob("*.json")) + sorted(custom_dir.glob("*.yaml")):
            name = f.stem
            if name in BUILTIN_TEMPLATES:
                continue  # user override — already listed
            try:
                tmpl = get_template(name)
                if tmpl:
                    results.append({
                        "name": name,
                        "display_name": tmpl.get("name", name),
                        "description": tmpl.get("description", "Custom template"),
                        "icon": tmpl.get("icon", "🔧"),
                        "stages": len(tmpl.get("stages", [])),
                        "max_iterations": tmpl.get("max_iterations", 3),
                        "source": "custom",
                    })
            except Exception:
                pass

    return results


def resolve_stages(template: dict, mode: str = "single") -> list[dict]:
    """Resolve template roles into concrete agent assignments or prompts.

    mode='single': roles become system prompt personalities (sub-agents)
    mode='mesh': roles stay as-is for bot/router.py to resolve to nodes
    """
    resolved = []
    for stage in template.get("stages", []):
        s = dict(stage)

        if "parallel" in s:
            # Resolve each parallel sub-stage
            s["parallel"] = [
                _resolve_one(p, mode) for p in s["parallel"]
            ]
        else:
            s = _resolve_one(s, mode)

        resolved.append(s)

    return resolved


def _resolve_one(stage: dict, mode: str) -> dict:
    """Resolve a single stage's role into agent assignment or system prompt."""
    s = dict(stage)
    role = s.get("role", "executor")

    if mode == "single":
        # Single-node: role → system prompt personality
        s["agent"] = "local"
        s["system_prompt"] = ROLE_PROMPTS.get(role, ROLE_PROMPTS["executor"])
        s["task_type"] = _role_to_task_type(role)
    else:
        # Mesh mode: keep role for router to resolve
        s["agent"] = role  # router.route() will map to best node
        s["task_type"] = _role_to_task_type(role)

    return s


def _role_to_task_type(role: str) -> str:
    """Map a role to a pipeline task type (for cloud model selection)."""
    mapping = {
        "planner": "spec",
        "backend": "build",
        "frontend": "build",
        "tester": "review",
        "reviewer": "review",
        "researcher": "spec",
        "analyst": "spec",
        "writer": "build",
        "executor": "build",
    }
    return mapping.get(role, "default")


def validate_template(template: dict) -> tuple[bool, str]:
    """Validate a template structure. Returns (is_valid, error_message)."""
    if not template:
        return False, "Template is empty"
    if "name" not in template:
        return False, "Missing 'name' field"
    stages = template.get("stages", [])
    if len(stages) < 2:
        return False, f"Template needs at least 2 stages, got {len(stages)}"

    for i, stage in enumerate(stages):
        if "name" not in stage:
            return False, f"Stage {i} missing 'name'"
        if "parallel" not in stage and "role" not in stage:
            return False, f"Stage '{stage['name']}' needs 'role' or 'parallel'"
        if "parallel" in stage:
            for j, p in enumerate(stage["parallel"]):
                if "role" not in p:
                    return False, f"Parallel sub-stage {j} in '{stage['name']}' missing 'role'"

        # Validate on_fail references
        on_fail = stage.get("on_fail", "")
        if on_fail.startswith("goto:"):
            target = on_fail[5:]
            stage_names = [s["name"] for s in stages]
            if target not in stage_names:
                return False, f"on_fail target '{target}' not found in stages"

    return True, ""

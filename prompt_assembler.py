"""
prompt_assembler.py — Builds the final system prompt from soul files + traits.

Merges:
  - SOUL.md     (core personality / how AI should behave)
  - IDENTITY.md (name, traits, communication style)
  - USER.md     (who the user is)
  - Active skills context

Used by the chat endpoint to replace the hardcoded system prompt.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("valhalla.prompt_assembler")

_SOULS_DIR = Path(__file__).parent / "souls"


# ---------------------------------------------------------------------------
# Trait descriptors — maps slider value (0–100) to natural language
# ---------------------------------------------------------------------------

def _describe_trait(label: str, value: int) -> str:
    """Convert a trait slider value into a natural language instruction."""
    if label == "Warmth":
        if value >= 80: return "Be very warm, caring, and emotionally present."
        if value >= 50: return "Be friendly and approachable."
        return "Be professional and measured. Don't over-emote."
    elif label == "Humor":
        if value >= 80: return "Use humor freely — jokes, wit, playful banter."
        if value >= 50: return "Add light humor when appropriate."
        return "Stay serious and focused. Minimal humor."
    elif label == "Directness":
        if value >= 80: return "Be very direct. Say what you mean without hedging."
        if value >= 50: return "Be clear and straightforward, but diplomatic."
        return "Be gentle and diplomatic. Soften direct statements."
    elif label == "Curiosity":
        if value >= 80: return "Ask follow-up questions. Explore tangents. Be genuinely curious."
        if value >= 50: return "Ask clarifying questions when helpful."
        return "Stay focused on the topic. Don't wander."
    elif label == "Formality":
        if value >= 80: return "Use formal, professional language."
        if value >= 50: return "Use a balanced, natural tone."
        return "Be casual and conversational. Use contractions. Talk like a friend."
    return ""


# ---------------------------------------------------------------------------
# Communication style descriptors
# ---------------------------------------------------------------------------

STYLE_PROMPTS = {
    "casual": "Speak casually, like texting a friend. Short sentences. Contractions. Emoji occasionally.",
    "balanced": "Use a natural, balanced tone. Not too formal, not too casual.",
    "professional": "Use professional language. Clear, structured, and polished.",
    "academic": "Use precise, academic language. Cite reasoning. Be thorough and methodical.",
}


# ---------------------------------------------------------------------------
# Assembler
# ---------------------------------------------------------------------------

def assemble_system_prompt(
    soul_dir: Optional[Path] = None,
    agent_name: str = "Atlas",
    user_name: str = "",
    active_skills: Optional[list[str]] = None,
    memories: Optional[list[str]] = None,
) -> str:
    """Build the complete system prompt from all personality sources.

    Priority: SOUL.md > trait modifiers > user context > skills > memories
    """
    sdir = soul_dir or _SOULS_DIR / "default"

    parts: list[str] = []

    # 1. Core personality (SOUL.md)
    soul_path = sdir / "SOUL.md"
    if soul_path.exists():
        soul_content = soul_path.read_text(encoding="utf-8").strip()
        parts.append(soul_content)
    else:
        parts.append(
            f"You are {agent_name}, a helpful, warm AI companion. "
            "You speak naturally and remember context from past conversations."
        )

    # 2. Identity + Traits (IDENTITY.md)
    identity_path = sdir / "IDENTITY.md"
    trait_section = []
    if identity_path.exists():
        identity_content = identity_path.read_text(encoding="utf-8").strip()
        # Parse structured traits
        in_traits = False
        for line in identity_content.split("\n"):
            if line.strip().startswith("## Traits"):
                in_traits = True
                continue
            if line.strip().startswith("## ") and in_traits:
                in_traits = False
                continue
            if in_traits and line.strip().startswith("- "):
                # Parse "- Warmth: 80" → descriptor
                parts_line = line.strip("- ").split(":")
                if len(parts_line) == 2:
                    label = parts_line[0].strip()
                    try:
                        value = int(parts_line[1].strip())
                        desc = _describe_trait(label, value)
                        if desc:
                            trait_section.append(desc)
                    except ValueError:
                        pass

        # Parse communication style
        for line in identity_content.split("\n"):
            if line.strip().startswith("- ") and not line.strip().startswith("- Warmth"):
                style_name = line.strip("- ").strip().lower()
                if style_name in STYLE_PROMPTS:
                    trait_section.append(STYLE_PROMPTS[style_name])
                    break

    if trait_section:
        parts.append("\n## Communication Guidelines (internal)\n" + "\n".join(f"- {t}" for t in trait_section))

    # 3. User context (USER.md)
    user_path = sdir / "USER.md"
    if user_path.exists():
        user_content = user_path.read_text(encoding="utf-8").strip()
        if user_content and "About the User" in user_content:
            parts.append(f"\n## About the Person You're Talking To\n{user_content}")
    elif user_name:
        parts.append(f"\n## About the Person You're Talking To\nTheir name is {user_name}.")

    # 4. Active skills context
    if active_skills:
        skill_descriptions = {
            "working-memory": "You have long-term memory. Reference past conversations when relevant.",
            "adaptive-thinking": "Use chain-of-thought reasoning for complex questions. Think step by step.",
            "self-model": "Be aware of your own strengths and limitations. Say when you're uncertain.",
            "browse": "You can browse the web. If the user asks about current events, offer to look it up.",
            "terminal": "You can run terminal commands when asked. Always ask permission first.",
            "voice": "The user may be speaking to you via voice. Keep responses conversational and concise.",
            "alerts": "You can send proactive notifications. If you notice something important, mention it.",
        }
        active_descs = [skill_descriptions[s] for s in active_skills if s in skill_descriptions]
        if active_descs:
            parts.append("\n## Your Active Capabilities\n" + "\n".join(f"- {d}" for d in active_descs))

    # 5. Retrieved memories (injected by memory plugin)
    if memories:
        parts.append("\n## Relevant Memories\n" + "\n".join(f"- {m}" for m in memories[:10]))

    prompt = "\n\n".join(parts)
    log.debug("[prompt] Assembled system prompt (%d chars)", len(prompt))
    return prompt


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(assemble_system_prompt(agent_name="Atlas", user_name="Jordan"))

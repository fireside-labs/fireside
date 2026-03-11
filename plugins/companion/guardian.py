"""
companion/guardian.py — Message Guardian Engine.

Pre-send interception: analyzes messages before they're sent.

Features:
  1. Sentiment classification: angry / sad / neutral / happy
  2. Regret detection heuristics:
     - Time-of-day (2am flag)
     - Recipient category (ex flag)
     - All-caps detection
     - Reply-all detection
     - Profanity density
  3. Returns: { risk_level, suggestion, softer_version }

No external dependencies — pure heuristic + pattern matching.
Works fully offline.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

log = logging.getLogger("valhalla.companion.guardian")

# ---------------------------------------------------------------------------
# Sentiment classifier (keyword-based, <50MB, fully offline)
# ---------------------------------------------------------------------------

SENTIMENT_WORDS = {
    "angry": [
        "fuck", "shit", "damn", "hell", "hate", "stupid", "idiot", "moron",
        "furious", "pissed", "angry", "rage", "screw", "bastard", "ass",
        "wtf", "stfu", "terrible", "worst", "disgusting", "pathetic",
        "never again", "done with",
    ],
    "sad": [
        "sorry", "sad", "miss", "lonely", "hurt", "crying", "depressed",
        "wish", "regret", "heartbroken", "lost", "empty", "alone",
        "disappointed", "failed", "hopeless", "give up",
    ],
    "happy": [
        "love", "amazing", "wonderful", "great", "happy", "excited",
        "awesome", "beautiful", "perfect", "best", "brilliant", "fantastic",
        "thank", "grateful", "blessed", "incredible", "joy",
    ],
}


def classify_sentiment(text: str) -> dict:
    """Classify text sentiment. Returns label + confidence."""
    text_lower = text.lower()
    words = set(re.findall(r'\b\w+\b', text_lower))

    scores = {"angry": 0, "sad": 0, "happy": 0, "neutral": 0}

    for sentiment, markers in SENTIMENT_WORDS.items():
        for marker in markers:
            if marker in text_lower:
                scores[sentiment] += 1

    # If no strong signal, it's neutral
    max_score = max(scores.values())
    if max_score == 0:
        return {"label": "neutral", "confidence": 0.8, "scores": scores}

    label = max(scores, key=scores.get)
    total = sum(scores.values()) or 1
    confidence = round(scores[label] / total, 2)

    return {"label": label, "confidence": confidence, "scores": scores}


# ---------------------------------------------------------------------------
# Regret detection heuristics
# ---------------------------------------------------------------------------

# Risky recipient patterns
EX_PATTERNS = [
    r"\bex\b", r"\bex-", r"ex girlfriend", r"ex boyfriend", r"ex wife",
    r"ex husband", r"my ex", r"old flame", r"former partner",
]

REPLY_ALL_PATTERNS = [
    r"reply.?all", r"@everyone", r"@all", r"@channel", r"@here",
    r"all hands", r"entire team",
]


def detect_regret_flags(text: str, hour: int = -1, recipient: str = "") -> list:
    """Detect regret indicators in a message.

    Args:
        text: The message text
        hour: Hour of day (0-23). -1 = don't check time.
        recipient: Who the message is for (optional)

    Returns:
        List of risk flags with explanations.
    """
    flags = []
    text_lower = text.lower()

    # 1. Late night (midnight - 5am)
    if 0 <= hour <= 5:
        flags.append({
            "type": "late_night",
            "severity": "medium",
            "reason": "It's late. Messages sent between midnight and 5am have a higher regret rate.",
        })

    # 2. All-caps detection
    alpha_chars = [c for c in text if c.isalpha()]
    if alpha_chars:
        caps_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
        if caps_ratio > 0.7 and len(text) > 10:
            flags.append({
                "type": "all_caps",
                "severity": "medium",
                "reason": "ALL CAPS can come across as shouting.",
            })

    # 3. Ex-partner recipient
    recipient_lower = recipient.lower()
    for pattern in EX_PATTERNS:
        if re.search(pattern, recipient_lower) or re.search(pattern, text_lower):
            flags.append({
                "type": "ex_partner",
                "severity": "high",
                "reason": "This might be going to an ex. Sleep on it?",
            })
            break

    # 4. Reply-all detection
    for pattern in REPLY_ALL_PATTERNS:
        if re.search(pattern, text_lower):
            flags.append({
                "type": "reply_all",
                "severity": "high",
                "reason": "This looks like a reply-all or broadcast. Everyone gets this.",
            })
            break

    # 5. Profanity density
    profanity = ["fuck", "shit", "damn", "hell", "ass", "bitch", "bastard", "crap"]
    word_count = max(len(text.split()), 1)
    profanity_count = sum(1 for p in profanity if p in text_lower)
    if profanity_count >= 2 or (profanity_count / word_count > 0.1):
        flags.append({
            "type": "profanity",
            "severity": "medium",
            "reason": "High profanity density. Might want to cool down first.",
        })

    # 6. Exclamation density
    if text.count("!") >= 3:
        flags.append({
            "type": "exclamation_heavy",
            "severity": "low",
            "reason": "Lots of exclamation marks. High energy detected.",
        })

    # 7. Message length + anger
    if len(text) > 500:
        sentiment = classify_sentiment(text)
        if sentiment["label"] == "angry":
            flags.append({
                "type": "angry_wall",
                "severity": "high",
                "reason": "Long angry message. These rarely land well. Consider a bullet-point version.",
            })

    return flags


# ---------------------------------------------------------------------------
# Softer rewrites (rule-based suggestions)
# ---------------------------------------------------------------------------

SOFTENERS = [
    (r"\byou always\b", "it sometimes feels like"),
    (r"\byou never\b", "I wish"),
    (r"\byou're wrong\b", "I see it differently"),
    (r"\bthat's stupid\b", "I'm not sure about that approach"),
    (r"\bI hate\b", "I'm frustrated with"),
    (r"\bshut up\b", "let me finish"),
    (r"\bwhatever\b", "I need a moment"),
    (r"\bI don't care\b", "I need to think about this"),
    (r"\bleave me alone\b", "I need some space right now"),
]


def suggest_softer(text: str) -> str:
    """Suggest a softer version of the message."""
    result = text
    for pattern, replacement in SOFTENERS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


# ---------------------------------------------------------------------------
# Main analysis function
# ---------------------------------------------------------------------------

def analyze_message(
    text: str,
    hour: int = -1,
    recipient: str = "",
    species: str = "cat",
) -> dict:
    """Full message analysis — sentiment + regret detection + softer version.

    Returns structured advice for the MessageGuardian UI.
    """
    if not text or not text.strip():
        return {"risk_level": "none", "flags": [], "suggestion": ""}

    sentiment = classify_sentiment(text)
    flags = detect_regret_flags(text, hour, recipient)

    # Calculate overall risk
    severity_scores = {"low": 1, "medium": 2, "high": 3}
    total_risk = sum(severity_scores.get(f["severity"], 0) for f in flags)

    if total_risk >= 5:
        risk_level = "high"
    elif total_risk >= 2:
        risk_level = "medium"
    elif total_risk >= 1:
        risk_level = "low"
    else:
        risk_level = "none"

    # Per-species warning
    SPECIES_WARNINGS = {
        "cat": {
            "high": "Are you sure? This sounds like 2am energy.",
            "medium": "Hmm. I'd sleep on this one.",
            "low": "Just checking — you good?",
        },
        "dog": {
            "high": "Hey buddy... are we sure about this one? 🥺",
            "medium": "Want to take a walk first? Clear your head?",
            "low": "I believe in you! But maybe re-read it?",
        },
        "penguin": {
            "high": "Sir. I must advise against this correspondence.",
            "medium": "Perhaps a more... measured approach?",
            "low": "Noted. Proceed with mild caution.",
        },
        "fox": {
            "high": "My instincts say wait. Trust the instincts.",
            "medium": "There's a smarter play here. Want to think on it?",
            "low": "Looks fine, but I'm watching.",
        },
        "owl": {
            "high": "Historically, messages like this have a 78% regret rate.",
            "medium": "The data suggests a 15-minute cooling period.",
            "low": "Minor risk detected. Proceeding is acceptable.",
        },
        "dragon": {
            "high": "I RESPECT THE ENERGY but your boss might not.",
            "medium": "Save the fire for something worth burning.",
            "low": "This is fine. Probably. SEND IT.",
        },
    }

    species_msgs = SPECIES_WARNINGS.get(species, SPECIES_WARNINGS["cat"])
    warning = species_msgs.get(risk_level, "")

    # Softer version
    softer = suggest_softer(text) if risk_level in ("medium", "high") else ""

    return {
        "risk_level": risk_level,
        "sentiment": sentiment,
        "flags": flags,
        "warning": warning,
        "softer_version": softer if softer != text else "",
        "suggestion": warning,
        "actions": ["send_anyway", "edit", "save_draft"] if risk_level != "none" else ["send"],
    }

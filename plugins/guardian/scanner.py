"""
guardian/scanner.py — Scam & phishing detection engine.

Analyzes messages, emails, and texts for scam indicators.
Runs entirely locally — no data leaves the device.

Threat levels:
    🟢 SAFE     — Known contact, normal content
    🟡 SUSPECT  — Unusual sender, urgency language, suspicious links
    🔴 SCAM     — Phishing link, fake urgency, money request, known scam pattern

Usage:
    from plugins.guardian.scanner import scan_message
    result = scan_message("You've won $1M! Click here: bit.ly/xxx")
    # → {"threat": "scam", "score": 0.95, "reasons": [...], "color": "red"}
"""
from __future__ import annotations

import logging
import re
from typing import Optional
from urllib.parse import urlparse

log = logging.getLogger("valhalla.guardian")


# ═══════════════════════════════════════════════════════════════
# Threat Levels
# ═══════════════════════════════════════════════════════════════

SAFE = "safe"         # 🟢
SUSPECT = "suspect"   # 🟡
SCAM = "scam"         # 🔴

COLORS = {
    SAFE: "#22c55e",      # green-500
    SUSPECT: "#eab308",   # yellow-500
    SCAM: "#ef4444",      # red-500
}

LABELS = {
    SAFE: "✅ Safe",
    SUSPECT: "⚠️ Suspicious",
    SCAM: "🚨 Scam Detected",
}

ADVICE = {
    SAFE: "This message looks safe.",
    SUSPECT: "Be careful with this one. Don't click links or send money without verifying.",
    SCAM: "This is almost certainly a scam. Delete it. Don't click anything.",
}


# ═══════════════════════════════════════════════════════════════
# Known Scam Patterns (fast detection, no LLM needed)
# ═══════════════════════════════════════════════════════════════

# Urgency / pressure phrases
URGENCY_PHRASES = [
    r"act now",
    r"immediate(ly)?( action)?",
    r"urgent",
    r"last chance",
    r"limited time",
    r"expires? (today|soon|in \d+)",
    r"your account (will be |has been )?(suspended|closed|locked|deactivated)",
    r"verify your (account|identity|information)",
    r"confirm your (payment|details|identity)",
    r"failure to (respond|act|verify)",
    r"within \d+ hours",
    r"don'?t ignore",
    r"respond immediately",
]

# Money / financial scam phrases
MONEY_PHRASES = [
    r"you('ve| have) won",
    r"prize",
    r"lottery",
    r"inheritance",
    r"unclaimed (funds|money|reward)",
    r"wire transfer",
    r"send (money|\$|payment|gift card)",
    r"gift card",
    r"bitcoin",
    r"crypto",
    r"investment opportunity",
    r"guaranteed (return|profit|income)",
    r"double your money",
    r"nigerian prince",
    r"bank of nigeria",
    r"western union",
    r"moneygram",
    r"cash app .*(send|transfer)",
    r"venmo .*(send|transfer)",
    r"zelle .*(send|transfer)",
]

# Impersonation phrases
IMPERSONATION_PHRASES = [
    r"(this is|i am|calling from) (the )?(irs|fbi|ssa|social security|medicare|police)",
    r"(your |the )?(apple|amazon|microsoft|google|paypal|netflix) (account|support|team)",
    r"(dear |hello )?(customer|user|account holder|valued member)",
    r"tech(nical)? support",
    r"geek squad",
    r"warrant for your arrest",
]

# Suspicious link patterns
SUSPICIOUS_DOMAINS = [
    r"bit\.ly",
    r"tinyurl\.com",
    r"t\.co",
    r"goo\.gl",
    r"rb\.gy",
    r"shorturl\.at",
    r"is\.gd",
    r"cutt\.ly",
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",   # raw IP
    r"[a-z]+-[a-z]+-[a-z]+\.(com|xyz|top|tk|ml|ga|cf)",  # random-word domains
]

# Compile all patterns
_urgency_re = [re.compile(p, re.IGNORECASE) for p in URGENCY_PHRASES]
_money_re = [re.compile(p, re.IGNORECASE) for p in MONEY_PHRASES]
_impersonation_re = [re.compile(p, re.IGNORECASE) for p in IMPERSONATION_PHRASES]
_suspicious_link_re = [re.compile(p, re.IGNORECASE) for p in SUSPICIOUS_DOMAINS]


# ═══════════════════════════════════════════════════════════════
# URL extraction & analysis
# ═══════════════════════════════════════════════════════════════

URL_PATTERN = re.compile(
    r"(https?://[^\s<>\"')\]]+|www\.[^\s<>\"')\]]+)",
    re.IGNORECASE,
)


def _extract_urls(text: str) -> list[str]:
    """Extract URLs from message text."""
    return URL_PATTERN.findall(text)


def _analyze_url(url: str) -> dict:
    """Check a URL for suspicious indicators."""
    flags = []
    try:
        parsed = urlparse(url if url.startswith("http") else f"http://{url}")
        domain = parsed.netloc.lower()

        # Check against suspicious domain patterns
        for pattern in _suspicious_link_re:
            if pattern.search(domain) or pattern.search(url):
                flags.append(f"Suspicious shortened/random URL: {domain}")
                break

        # Homograph detection (lookalike characters)
        lookalikes = {"0": "o", "1": "l", "рa": "pa", "аp": "ap"}
        for fake, real in lookalikes.items():
            if fake in domain:
                flags.append(f"Possible lookalike domain: '{domain}' may be impersonating a real site")

        # Too many subdomains
        parts = domain.split(".")
        if len(parts) > 3:
            flags.append(f"Unusual number of subdomains: {domain}")

        # Unusual TLDs
        suspicious_tlds = [".xyz", ".top", ".tk", ".ml", ".ga", ".cf", ".buzz", ".click", ".link"]
        for tld in suspicious_tlds:
            if domain.endswith(tld):
                flags.append(f"Suspicious TLD: {tld}")
                break

    except Exception:
        flags.append("Could not parse URL")

    return {"url": url, "flags": flags, "suspicious": len(flags) > 0}


# ═══════════════════════════════════════════════════════════════
# Core Scanner
# ═══════════════════════════════════════════════════════════════

def scan_message(
    text: str,
    sender: str = "",
    known_contacts: Optional[list[str]] = None,
    message_type: str = "sms",  # "sms", "email", "chat"
) -> dict:
    """
    Scan a message for scam indicators.

    Returns:
        {
            "threat": "safe" | "suspect" | "scam",
            "score": 0.0 - 1.0,
            "color": "#hex",
            "label": "✅ Safe",
            "advice": "This message looks safe.",
            "reasons": ["list of why"],
            "urls": [{"url": "...", "flags": [...]}],
        }
    """
    if not text or not text.strip():
        return _result(SAFE, 0.0, [])

    reasons = []
    score = 0.0
    text_lower = text.lower()

    # ── Check sender ──
    is_known = False
    if known_contacts and sender:
        sender_lower = sender.lower()
        is_known = any(
            c.lower() in sender_lower or sender_lower in c.lower()
            for c in known_contacts
        )

    if is_known:
        score -= 0.3  # known contacts get a trust bonus

    if sender and not is_known:
        reasons.append(f"Unknown sender: {sender}")
        score += 0.1

    # ── Urgency detection ──
    urgency_hits = []
    for pattern in _urgency_re:
        match = pattern.search(text)
        if match:
            urgency_hits.append(match.group())
    if urgency_hits:
        reasons.append(f"Urgency/pressure language: {', '.join(urgency_hits[:3])}")
        score += 0.15 * len(urgency_hits)

    # ── Money/financial scam detection ──
    money_hits = []
    for pattern in _money_re:
        match = pattern.search(text)
        if match:
            money_hits.append(match.group())
    if money_hits:
        reasons.append(f"Financial scam language: {', '.join(money_hits[:3])}")
        score += 0.25 * len(money_hits)

    # ── Impersonation detection ──
    impersonation_hits = []
    for pattern in _impersonation_re:
        match = pattern.search(text)
        if match:
            impersonation_hits.append(match.group())
    if impersonation_hits:
        reasons.append(f"Possible impersonation: {', '.join(impersonation_hits[:2])}")
        score += 0.3

    # ── URL analysis ──
    urls = _extract_urls(text)
    url_analyses = [_analyze_url(u) for u in urls]
    suspicious_urls = [u for u in url_analyses if u["suspicious"]]

    if suspicious_urls:
        for u in suspicious_urls:
            reasons.extend(u["flags"])
        score += 0.2 * len(suspicious_urls)

    # Extra: links in short messages are more suspicious
    if urls and len(text) < 100:
        reasons.append("Short message with link — common in SMS phishing")
        score += 0.15

    # ── Grammar / formatting red flags ──
    if text.isupper() and len(text) > 20:
        reasons.append("ALL CAPS message — common in scam texts")
        score += 0.1

    excessive_emoji = len(re.findall(r"[💰🎉🏆🎁💵💲🤑⚠️🚨❗]", text))
    if excessive_emoji >= 3:
        reasons.append("Excessive money/prize emojis")
        score += 0.1

    excessive_exclamation = text.count("!")
    if excessive_exclamation >= 3:
        reasons.append("Excessive exclamation marks")
        score += 0.05

    # ── Phone number in text (callback scam) ──
    phone_in_text = re.findall(r"(?:call|text|dial|phone)\s*:?\s*[\d\-\(\)\+\s]{7,}", text_lower)
    if phone_in_text:
        reasons.append("Contains phone number to call back — possible callback scam")
        score += 0.15

    # Clamp score
    score = max(0.0, min(1.0, score))

    # Determine threat level
    if score >= 0.6:
        threat = SCAM
    elif score >= 0.25:
        threat = SUSPECT
    else:
        threat = SAFE

    return _result(threat, round(score, 2), reasons, url_analyses)


def scan_email(
    subject: str,
    body: str,
    sender: str = "",
    known_contacts: Optional[list[str]] = None,
) -> dict:
    """Scan an email (subject + body) for scam indicators."""
    # Combine subject and body for full analysis
    full_text = f"Subject: {subject}\n\n{body}"
    result = scan_message(full_text, sender=sender,
                          known_contacts=known_contacts, message_type="email")

    # Extra email-specific checks
    extra_reasons = []

    # Mismatched sender display name vs email
    if sender and "@" in sender:
        email_domain = sender.split("@")[-1].lower()
        # Check if subject claims to be from a big brand but email is from random domain
        big_brands = ["apple", "amazon", "google", "microsoft", "paypal",
                      "netflix", "bank", "chase", "wells fargo", "citi"]
        subject_lower = subject.lower()
        for brand in big_brands:
            if brand in subject_lower and brand not in email_domain:
                extra_reasons.append(
                    f"Email claims to be from {brand} but sent from {email_domain}"
                )
                result["score"] = min(1.0, result["score"] + 0.3)

    if extra_reasons:
        result["reasons"].extend(extra_reasons)
        # Re-evaluate threat level
        if result["score"] >= 0.6:
            result["threat"] = SCAM
            result["color"] = COLORS[SCAM]
            result["label"] = LABELS[SCAM]
            result["advice"] = ADVICE[SCAM]

    return result


def scan_batch(messages: list[dict]) -> list[dict]:
    """Scan multiple messages at once. Each should have 'text' and optionally 'sender'."""
    return [
        scan_message(
            text=msg.get("text", ""),
            sender=msg.get("sender", ""),
            known_contacts=msg.get("known_contacts"),
            message_type=msg.get("type", "sms"),
        )
        for msg in messages
    ]


# ═══════════════════════════════════════════════════════════════
# LLM Deep Analysis (optional, for borderline cases)
# ═══════════════════════════════════════════════════════════════

async def deep_scan(text: str, llm_fn=None) -> dict:
    """
    For borderline cases (🟡 SUSPECT), ask the local LLM for deeper analysis.

    This runs entirely locally — no data leaves the device.
    """
    # First do the fast pattern scan
    fast_result = scan_message(text)

    # Only use LLM for borderline cases
    if fast_result["threat"] != SUSPECT or llm_fn is None:
        return fast_result

    prompt = (
        "You are a scam detection expert. Analyze this message and determine "
        "if it is a scam, suspicious, or safe. Be direct.\n\n"
        f"Message: \"{text}\"\n\n"
        "Respond in this exact format:\n"
        "VERDICT: SAFE or SUSPECT or SCAM\n"
        "REASON: one-line explanation\n"
        "CONFIDENCE: 0.0 to 1.0"
    )

    try:
        response = await llm_fn(prompt)
        response_upper = response.upper()

        if "VERDICT: SCAM" in response_upper:
            fast_result["threat"] = SCAM
            fast_result["color"] = COLORS[SCAM]
            fast_result["label"] = LABELS[SCAM]
            fast_result["advice"] = ADVICE[SCAM]
            fast_result["score"] = min(1.0, fast_result["score"] + 0.2)
        elif "VERDICT: SAFE" in response_upper:
            fast_result["threat"] = SAFE
            fast_result["color"] = COLORS[SAFE]
            fast_result["label"] = LABELS[SAFE]
            fast_result["advice"] = ADVICE[SAFE]
            fast_result["score"] = max(0.0, fast_result["score"] - 0.2)

        fast_result["llm_analysis"] = response.strip()
        fast_result["deep_scanned"] = True

    except Exception as e:
        log.warning("[guardian] LLM deep scan failed: %s", e)
        fast_result["deep_scanned"] = False

    return fast_result


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _result(threat: str, score: float, reasons: list,
            urls: list = None) -> dict:
    return {
        "threat": threat,
        "score": score,
        "color": COLORS[threat],
        "label": LABELS[threat],
        "advice": ADVICE[threat],
        "reasons": reasons,
        "urls": urls or [],
    }

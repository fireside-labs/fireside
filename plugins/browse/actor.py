"""
browse/actor.py — Playwright-powered browser controller.

Uses the Pico interactive tree (parse_interactive) to present a compact
numbered list of actionable elements to the LLM, and executes actions
(click, type, select) via Playwright.

The browser launches with the user's existing Chrome/Edge profile so their
saved logins (DoorDash, Amazon, Starbucks, etc.) are already active.

Usage:
    actor = BrowserActor()
    await actor.open("https://www.doordash.com")
    page_state = actor.get_action_tree()  # compact text for LLM
    await actor.click(3)                  # click element [3]
    await actor.type_text(1, "cold brew") # type into element [1]
    await actor.close()
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
from pathlib import Path
from typing import Optional

log = logging.getLogger("valhalla.browse.actor")

try:
    from plugins.browse.parser import parse_interactive, InteractivePage
except ImportError:
    from parser import parse_interactive, InteractivePage

# Try to import Playwright
try:
    from playwright.async_api import async_playwright, Browser, Page
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    log.warning("[actor] Playwright not installed. Run: pip install playwright && python -m playwright install chromium")


# ---------------------------------------------------------------------------
# Browser profile detection
# ---------------------------------------------------------------------------

def _find_chrome_profile() -> Optional[str]:
    """Find the user's Chrome/Edge profile directory for cookie reuse."""
    system = platform.system()

    candidates = []
    if system == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            candidates = [
                Path(local) / "Google" / "Chrome" / "User Data",
                Path(local) / "Microsoft" / "Edge" / "User Data",
                Path(local) / "BraveSoftware" / "Brave-Browser" / "User Data",
            ]
    elif system == "Darwin":
        home = Path.home()
        candidates = [
            home / "Library" / "Application Support" / "Google" / "Chrome",
            home / "Library" / "Application Support" / "Microsoft Edge",
            home / "Library" / "Application Support" / "BraveSoftware" / "Brave-Browser",
        ]
    else:  # Linux
        home = Path.home()
        candidates = [
            home / ".config" / "google-chrome",
            home / ".config" / "microsoft-edge",
            home / ".config" / "BraveSoftware" / "Brave-Browser",
        ]

    for path in candidates:
        if path.exists():
            log.info("[actor] Found browser profile: %s", path)
            return str(path)

    return None


# ---------------------------------------------------------------------------
# Spending check hook
# ---------------------------------------------------------------------------

def _check_spending(description: str, estimated_cost: float) -> dict:
    """Check with the spending module before making a purchase."""
    try:
        from plugins.browse.spending import check_purchase
        return check_purchase(description, estimated_cost)
    except ImportError:
        # No spending module — allow by default
        return {"allowed": True, "reason": "No spending controls configured"}


# ---------------------------------------------------------------------------
# Browser Actor
# ---------------------------------------------------------------------------

MAX_STEPS = 25  # safety: max actions per session
ACTION_TIMEOUT_MS = 10_000  # 10s per action


class BrowserActor:
    """Playwright-powered browser that uses Pico action trees for navigation."""

    def __init__(self, headless: bool = True, use_profile: bool = True):
        self.headless = headless
        self.use_profile = use_profile
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._current_tree: Optional[InteractivePage] = None
        self._step_count = 0
        self._action_log: list[dict] = []

    async def open(self, url: str) -> dict:
        """Open a URL in the browser and return the interactive action tree."""
        if not HAS_PLAYWRIGHT:
            return {"ok": False, "error": "Playwright not installed. Run: pip install playwright && python -m playwright install chromium"}

        try:
            self._playwright = await async_playwright().start()

            # Launch with user profile if available
            launch_args = {
                "headless": self.headless,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            }

            if self.use_profile:
                profile_dir = _find_chrome_profile()
                if profile_dir:
                    # Use persistent context to keep cookies/logins
                    context = await self._playwright.chromium.launch_persistent_context(
                        user_data_dir=profile_dir,
                        headless=self.headless,
                        args=launch_args["args"],
                        channel="chrome",
                    )
                    self._page = context.pages[0] if context.pages else await context.new_page()
                    log.info("[actor] Launched with user profile: %s", profile_dir)
                else:
                    self._browser = await self._playwright.chromium.launch(**launch_args)
                    context = await self._browser.new_context()
                    self._page = await context.new_page()
                    log.info("[actor] Launched with fresh profile (no saved logins)")
            else:
                self._browser = await self._playwright.chromium.launch(**launch_args)
                context = await self._browser.new_context()
                self._page = await context.new_page()

            # Navigate
            await self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await self._page.wait_for_timeout(1000)  # let JS render

            # Parse the action tree
            html = await self._page.content()
            self._current_tree = parse_interactive(html, base_url=url)

            self._action_log.append({"action": "open", "url": url})
            self._step_count = 0

            return {
                "ok": True,
                "url": url,
                "title": self._current_tree.title,
                "action_tree": self._current_tree.to_action_text(),
                "stats": self._current_tree.summary_stats(),
            }

        except Exception as e:
            log.error("[actor] Failed to open %s: %s", url, e)
            return {"ok": False, "error": str(e)}

    async def click(self, element_idx: int) -> dict:
        """Click an interactive element by its index."""
        if not self._page or not self._current_tree:
            return {"ok": False, "error": "No page open. Call open() first."}

        if self._step_count >= MAX_STEPS:
            return {"ok": False, "error": f"Max steps ({MAX_STEPS}) reached. Session ended for safety."}

        element = self._current_tree.get_element(element_idx)
        if not element:
            return {"ok": False, "error": f"Element [{element_idx}] not found"}

        try:
            # Use the CSS selector if available, otherwise try text matching
            if element.selector:
                await self._page.click(element.selector, timeout=ACTION_TIMEOUT_MS)
            elif element.role == "link" and element.href:
                await self._page.goto(element.href, wait_until="domcontentloaded")
            else:
                # Fallback: click by text content
                await self._page.get_by_text(element.text, exact=False).first.click(timeout=ACTION_TIMEOUT_MS)

            await self._page.wait_for_timeout(1000)  # wait for page update

            # Re-parse the page
            html = await self._page.content()
            current_url = self._page.url
            self._current_tree = parse_interactive(html, base_url=current_url)

            self._step_count += 1
            self._action_log.append({"action": "click", "element": element_idx, "text": element.text})

            return {
                "ok": True,
                "clicked": element.text,
                "new_url": current_url,
                "action_tree": self._current_tree.to_action_text(),
                "steps_used": self._step_count,
                "steps_remaining": MAX_STEPS - self._step_count,
            }

        except Exception as e:
            log.warning("[actor] Click failed on [%d] %s: %s", element_idx, element.text, e)
            return {"ok": False, "error": str(e)}

    async def type_text(self, element_idx: int, text: str) -> dict:
        """Type text into an input element."""
        if not self._page or not self._current_tree:
            return {"ok": False, "error": "No page open."}

        if self._step_count >= MAX_STEPS:
            return {"ok": False, "error": f"Max steps ({MAX_STEPS}) reached."}

        element = self._current_tree.get_element(element_idx)
        if not element:
            return {"ok": False, "error": f"Element [{element_idx}] not found"}

        if element.role not in ("input", "textarea"):
            return {"ok": False, "error": f"Element [{element_idx}] is a {element.role}, not an input"}

        try:
            if element.selector:
                await self._page.fill(element.selector, text, timeout=ACTION_TIMEOUT_MS)
            else:
                await self._page.get_by_placeholder(element.text, exact=False).first.fill(text, timeout=ACTION_TIMEOUT_MS)

            self._step_count += 1
            self._action_log.append({"action": "type", "element": element_idx, "text": text[:50]})

            # Re-parse
            html = await self._page.content()
            self._current_tree = parse_interactive(html, base_url=self._page.url)

            return {
                "ok": True,
                "typed": text,
                "into": element.text,
                "steps_used": self._step_count,
            }

        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def select_option(self, element_idx: int, value: str) -> dict:
        """Select a dropdown option."""
        if not self._page or not self._current_tree:
            return {"ok": False, "error": "No page open."}

        element = self._current_tree.get_element(element_idx)
        if not element:
            return {"ok": False, "error": f"Element [{element_idx}] not found"}

        if element.role != "select":
            return {"ok": False, "error": f"Element [{element_idx}] is not a select"}

        try:
            if element.selector:
                await self._page.select_option(element.selector, label=value, timeout=ACTION_TIMEOUT_MS)
            self._step_count += 1
            self._action_log.append({"action": "select", "element": element_idx, "value": value})

            html = await self._page.content()
            self._current_tree = parse_interactive(html, base_url=self._page.url)

            return {"ok": True, "selected": value, "in": element.text}

        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def screenshot(self) -> dict:
        """Take a screenshot of the current page."""
        if not self._page:
            return {"ok": False, "error": "No page open."}

        try:
            output_dir = Path.home() / ".fireside" / "outputs"
            output_dir.mkdir(parents=True, exist_ok=True)
            path = output_dir / f"browse_screenshot_{self._step_count}.png"
            await self._page.screenshot(path=str(path), full_page=False)
            return {"ok": True, "path": str(path)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def confirm_purchase(self, description: str, estimated_cost: float) -> dict:
        """Check spending limits before confirming a purchase.

        Returns whether the purchase is allowed, needs approval, or is blocked.
        """
        result = _check_spending(description, estimated_cost)

        self._action_log.append({
            "action": "spending_check",
            "description": description,
            "cost": estimated_cost,
            "result": result,
        })

        return result

    def get_action_tree(self) -> str:
        """Return the current page's action tree as text for the LLM."""
        if not self._current_tree:
            return "No page loaded."
        return self._current_tree.to_action_text()

    def get_session_info(self) -> dict:
        """Return current session state."""
        return {
            "page_open": self._page is not None,
            "url": self._page.url if self._page else None,
            "title": self._current_tree.title if self._current_tree else None,
            "steps_used": self._step_count,
            "steps_remaining": MAX_STEPS - self._step_count,
            "action_log": self._action_log[-10:],  # last 10 actions
        }

    async def close(self):
        """Close the browser."""
        try:
            if self._page:
                await self._page.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            log.warning("[actor] Close error: %s", e)
        finally:
            self._page = None
            self._browser = None
            self._playwright = None
            self._current_tree = None

        log.info("[actor] Browser closed. %d actions performed.", self._step_count)


# ---------------------------------------------------------------------------
# Convenience: multi-step agent loop
# ---------------------------------------------------------------------------

async def browse_and_act(url: str, goal: str, llm_fn=None, max_rounds: int = 10) -> dict:
    """
    High-level: open a URL and let the LLM navigate toward a goal.

    The LLM sees the action tree and responds with commands like:
        click 3
        type 1 "cold brew"
        select 5 "Large"
        done
        confirm_purchase "Starbucks Cold Brew" 6.50

    Args:
        url: Starting URL
        goal: What the user wants (e.g., "Order a cold brew from Starbucks")
        llm_fn: async function(prompt) -> str — calls the brain
        max_rounds: Max interaction rounds

    Returns:
        dict with action log and final state
    """
    actor = BrowserActor(headless=True)

    try:
        open_result = await actor.open(url)
        if not open_result["ok"]:
            return open_result

        result = {
            "url": url,
            "goal": goal,
            "rounds": [],
            "status": "in_progress",
        }

        for round_num in range(max_rounds):
            action_tree = actor.get_action_tree()

            # Build prompt for LLM
            prompt = (
                f"You are navigating a website to accomplish this goal: {goal}\n\n"
                f"Current page state:\n{action_tree}\n\n"
                f"Round {round_num + 1}/{max_rounds}. "
                f"Respond with ONE command:\n"
                f"  click <n>           — click element [n]\n"
                f"  type <n> \"text\"     — type into element [n]\n"
                f"  select <n> \"value\"  — select dropdown option\n"
                f"  confirm_purchase \"description\" <cost> — check spending before buying\n"
                f"  done               — goal achieved\n"
                f"  abort              — cannot complete goal\n"
            )

            if llm_fn:
                response = await llm_fn(prompt)
            else:
                # No LLM available — return the tree for manual control
                result["status"] = "awaiting_command"
                result["action_tree"] = action_tree
                return result

            response = response.strip().lower()
            round_log = {"round": round_num + 1, "command": response}

            # Parse LLM response
            if response == "done":
                result["status"] = "completed"
                round_log["result"] = "Goal achieved"
                result["rounds"].append(round_log)
                break
            elif response == "abort":
                result["status"] = "aborted"
                round_log["result"] = "Cannot complete goal"
                result["rounds"].append(round_log)
                break
            elif response.startswith("click "):
                try:
                    idx = int(response.split()[1])
                    action_result = await actor.click(idx)
                    round_log["result"] = action_result
                except (IndexError, ValueError):
                    round_log["result"] = {"ok": False, "error": "Invalid click command"}
            elif response.startswith("type "):
                import re
                match = re.match(r'type (\d+) "(.+)"', response)
                if match:
                    idx, text = int(match.group(1)), match.group(2)
                    action_result = await actor.type_text(idx, text)
                    round_log["result"] = action_result
                else:
                    round_log["result"] = {"ok": False, "error": "Invalid type command"}
            elif response.startswith("select "):
                import re
                match = re.match(r'select (\d+) "(.+)"', response)
                if match:
                    idx, value = int(match.group(1)), match.group(2)
                    action_result = await actor.select_option(idx, value)
                    round_log["result"] = action_result
                else:
                    round_log["result"] = {"ok": False, "error": "Invalid select command"}
            elif response.startswith("confirm_purchase"):
                import re
                match = re.match(r'confirm_purchase "(.+)" ([\d.]+)', response)
                if match:
                    desc, cost = match.group(1), float(match.group(2))
                    spend_result = await actor.confirm_purchase(desc, cost)
                    round_log["result"] = spend_result
                    if not spend_result.get("allowed"):
                        result["status"] = "blocked_by_spending"
                        result["spending_check"] = spend_result
                        result["rounds"].append(round_log)
                        break
                else:
                    round_log["result"] = {"ok": False, "error": "Invalid confirm command"}
            else:
                round_log["result"] = {"ok": False, "error": f"Unknown command: {response}"}

            result["rounds"].append(round_log)

        if result["status"] == "in_progress":
            result["status"] = "max_rounds_reached"

        result["session"] = actor.get_session_info()
        return result

    finally:
        await actor.close()

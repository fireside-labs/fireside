"""
tests/test_sprint10_vision.py — Sprint 10: Two-Character System + Guild Hall

Validates Thor's 4 tasks:
  1. install.sh Step 4 (AI person: name + style)
  2. Config files include agent{} section
  3. GET /api/v1/agent/profile
  4. GET /api/v1/guildhall/agents

Run:  python -m pytest tests/test_sprint10_vision.py -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

REPO_ROOT = Path(__file__).parent.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Task 1 — install.sh Step 4 (AI Person)
# ---------------------------------------------------------------------------

class TestInstallStep4(unittest.TestCase):

    def test_step4_header(self):
        src = _read("install.sh")
        self.assertIn("STEP 4", src)

    def test_agent_name_prompt(self):
        src = _read("install.sh")
        self.assertIn("Give your AI a name", src)

    def test_default_atlas(self):
        src = _read("install.sh")
        self.assertIn("Atlas", src)

    def test_style_analytical(self):
        src = _read("install.sh")
        self.assertIn("Analytical", src)

    def test_style_creative(self):
        src = _read("install.sh")
        self.assertIn("Creative", src)

    def test_style_direct(self):
        src = _read("install.sh")
        self.assertIn("Direct", src)

    def test_style_warm(self):
        src = _read("install.sh")
        self.assertIn("Warm", src)

    def test_agent_name_variable(self):
        src = _read("install.sh")
        self.assertIn("AGENT_NAME", src)

    def test_agent_style_variable(self):
        src = _read("install.sh")
        self.assertIn("AGENT_STYLE", src)

    def test_running_the_show(self):
        src = _read("install.sh")
        self.assertIn("running the show at home", src)

    def test_fireside_message(self):
        src = _read("install.sh")
        self.assertIn("at the fireside", src)


# ---------------------------------------------------------------------------
# Task 2 — Config Files Include agent{}
# ---------------------------------------------------------------------------

class TestConfigAgent(unittest.TestCase):

    def test_yaml_agent_section(self):
        src = _read("install.sh")
        yaml_start = src.find("cat > valhalla.yaml")
        yaml_block = src[yaml_start:yaml_start + 1500]
        self.assertIn("agent:", yaml_block)

    def test_yaml_agent_name(self):
        src = _read("install.sh")
        yaml_start = src.find("cat > valhalla.yaml")
        yaml_block = src[yaml_start:yaml_start + 1500]
        self.assertIn("AGENT_NAME", yaml_block)

    def test_yaml_agent_style(self):
        src = _read("install.sh")
        yaml_start = src.find("cat > valhalla.yaml")
        yaml_block = src[yaml_start:yaml_start + 1500]
        self.assertIn("AGENT_STYLE", yaml_block)

    def test_companion_state_agent(self):
        src = _read("install.sh")
        # Find the heredoc block for companion_state.json
        state_start = src.find("companion_state.json")
        state_block = src[state_start:state_start + 800]
        self.assertIn('"agent"', state_block)

    def test_onboarding_agent(self):
        src = _read("install.sh")
        # Find the heredoc block for onboarding.json
        onboard_start = src.find("onboarding.json")
        onboard_block = src[onboard_start:onboard_start + 800]
        self.assertIn('"agent"', onboard_block)

    def test_confirmation_shows_ai(self):
        src = _read("install.sh")
        self.assertIn("STEP 5", src)
        confirm_start = src.find("STEP 5")
        confirm_block = src[confirm_start:confirm_start + 1000]
        self.assertIn("AGENT_NAME", confirm_block)


# ---------------------------------------------------------------------------
# Task 3 — Agent Profile API
# ---------------------------------------------------------------------------

class TestAgentProfileAPI(unittest.TestCase):

    def test_agent_profile_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/agent/profile", src)

    def test_agent_profile_get(self):
        src = _read("plugins/companion/handler.py")
        idx = src.find("/api/v1/agent/profile")
        before = src[max(0, idx - 200):idx]
        self.assertIn(".get(", before)

    def test_profile_returns_name(self):
        src = _read("plugins/companion/handler.py")
        profile_start = src.find("def api_agent_profile")
        profile_block = src[profile_start:profile_start + 3000]
        self.assertIn('"name"', profile_block)

    def test_profile_returns_style(self):
        src = _read("plugins/companion/handler.py")
        profile_start = src.find("def api_agent_profile")
        profile_block = src[profile_start:profile_start + 3000]
        self.assertIn('"style"', profile_block)

    def test_profile_returns_companion(self):
        src = _read("plugins/companion/handler.py")
        profile_start = src.find("def api_agent_profile")
        profile_block = src[profile_start:profile_start + 3000]
        self.assertIn('"companion"', profile_block)

    def test_profile_returns_uptime(self):
        src = _read("plugins/companion/handler.py")
        profile_start = src.find("def api_agent_profile")
        profile_block = src[profile_start:profile_start + 3000]
        self.assertIn('"uptime"', profile_block)

    def test_profile_returns_plugins(self):
        src = _read("plugins/companion/handler.py")
        profile_start = src.find("def api_agent_profile")
        profile_block = src[profile_start:profile_start + 3000]
        self.assertIn('"plugins_active"', profile_block)


# ---------------------------------------------------------------------------
# Task 4 — Guild Hall Real Data
# ---------------------------------------------------------------------------

class TestGuildHallAPI(unittest.TestCase):

    def test_guildhall_route(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/guildhall/agents", src)

    def test_guildhall_get(self):
        src = _read("plugins/companion/handler.py")
        idx = src.find("/api/v1/guildhall/agents")
        before = src[max(0, idx - 200):idx]
        self.assertIn(".get(", before)

    def test_guildhall_returns_agents(self):
        src = _read("plugins/companion/handler.py")
        guild_start = src.find("def api_guildhall_agents")
        guild_block = src[guild_start:guild_start + 5000]
        self.assertIn('"agents"', guild_block)

    def test_guildhall_ai_type(self):
        src = _read("plugins/companion/handler.py")
        guild_start = src.find("def api_guildhall_agents")
        guild_block = src[guild_start:guild_start + 5000]
        self.assertIn('"ai"', guild_block)

    def test_guildhall_companion_type(self):
        src = _read("plugins/companion/handler.py")
        guild_start = src.find("def api_guildhall_agents")
        guild_block = src[guild_start:guild_start + 5000]
        self.assertIn('"companion"', guild_block)

    def test_guildhall_activity_building(self):
        src = _read("plugins/companion/handler.py")
        guild_start = src.find("def api_guildhall_agents")
        guild_block = src[guild_start:guild_start + 5000]
        self.assertIn('"building"', guild_block)

    def test_guildhall_activity_researching(self):
        src = _read("plugins/companion/handler.py")
        guild_start = src.find("def api_guildhall_agents")
        guild_block = src[guild_start:guild_start + 5000]
        self.assertIn('"researching"', guild_block)

    def test_guildhall_activity_chatting(self):
        src = _read("plugins/companion/handler.py")
        guild_start = src.find("def api_guildhall_agents")
        guild_block = src[guild_start:guild_start + 5000]
        self.assertIn('"chatting"', guild_block)

    def test_guildhall_status_online(self):
        src = _read("plugins/companion/handler.py")
        guild_start = src.find("def api_guildhall_agents")
        guild_block = src[guild_start:guild_start + 5000]
        self.assertIn('"online"', guild_block)


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

class TestSprint10Regression(unittest.TestCase):

    def test_waitlist_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/waitlist", src)

    def test_query_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/query", src)

    def test_achievements_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/companion/achievements", src)

    def test_privacy_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/privacy-contact", src)


if __name__ == "__main__":
    unittest.main()

"""
tests/test_sprint12_native.py — Sprint 12: Ember Goes Native (iOS APIs + Siri)

Validates Thor's 5 tasks:
  1. NativeCalendar module (Swift + TS)
  2. NativeContacts module (Swift + TS)
  3. NativeHealth module (Swift + TS)
  4. ProactiveEngine.ts
  5. Siri AppIntents

Run:  python -m pytest tests/test_sprint12_native.py -v
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
# Task 1 — NativeCalendar
# ---------------------------------------------------------------------------

class TestNativeCalendar(unittest.TestCase):

    def test_swift_module_exists(self):
        self.assertTrue(
            (REPO_ROOT / "mobile" / "modules" / "native-calendar" / "ios" / "NativeCalendarModule.swift").exists()
        )

    def test_ts_bindings_exist(self):
        self.assertTrue(
            (REPO_ROOT / "mobile" / "modules" / "native-calendar" / "index.ts").exists()
        )

    def test_swift_eventkit_import(self):
        src = _read("mobile/modules/native-calendar/ios/NativeCalendarModule.swift")
        self.assertIn("import EventKit", src)

    def test_get_upcoming_events(self):
        src = _read("mobile/modules/native-calendar/ios/NativeCalendarModule.swift")
        self.assertIn("getUpcomingEvents", src)

    def test_get_next_event(self):
        src = _read("mobile/modules/native-calendar/ios/NativeCalendarModule.swift")
        self.assertIn("getNextEvent", src)

    def test_get_today_events(self):
        src = _read("mobile/modules/native-calendar/ios/NativeCalendarModule.swift")
        self.assertIn("getTodayEvents", src)

    def test_ts_calendar_event_interface(self):
        src = _read("mobile/modules/native-calendar/index.ts")
        self.assertIn("CalendarEvent", src)

    def test_expo_module_config(self):
        self.assertTrue(
            (REPO_ROOT / "mobile" / "modules" / "native-calendar" / "expo-module.config.json").exists()
        )


# ---------------------------------------------------------------------------
# Task 2 — NativeContacts
# ---------------------------------------------------------------------------

class TestNativeContacts(unittest.TestCase):

    def test_swift_module_exists(self):
        self.assertTrue(
            (REPO_ROOT / "mobile" / "modules" / "native-contacts" / "ios" / "NativeContactsModule.swift").exists()
        )

    def test_ts_bindings_exist(self):
        self.assertTrue(
            (REPO_ROOT / "mobile" / "modules" / "native-contacts" / "index.ts").exists()
        )

    def test_swift_contacts_import(self):
        src = _read("mobile/modules/native-contacts/ios/NativeContactsModule.swift")
        self.assertIn("import Contacts", src)

    def test_search_by_name(self):
        src = _read("mobile/modules/native-contacts/ios/NativeContactsModule.swift")
        self.assertIn("searchByName", src)

    def test_get_recent(self):
        src = _read("mobile/modules/native-contacts/ios/NativeContactsModule.swift")
        self.assertIn("getRecent", src)

    def test_ts_contact_interface(self):
        src = _read("mobile/modules/native-contacts/index.ts")
        self.assertIn("Contact", src)

    def test_expo_module_config(self):
        self.assertTrue(
            (REPO_ROOT / "mobile" / "modules" / "native-contacts" / "expo-module.config.json").exists()
        )


# ---------------------------------------------------------------------------
# Task 3 — NativeHealth
# ---------------------------------------------------------------------------

class TestNativeHealth(unittest.TestCase):

    def test_swift_module_exists(self):
        self.assertTrue(
            (REPO_ROOT / "mobile" / "modules" / "native-health" / "ios" / "NativeHealthModule.swift").exists()
        )

    def test_ts_bindings_exist(self):
        self.assertTrue(
            (REPO_ROOT / "mobile" / "modules" / "native-health" / "index.ts").exists()
        )

    def test_swift_healthkit_import(self):
        src = _read("mobile/modules/native-health/ios/NativeHealthModule.swift")
        self.assertIn("import HealthKit", src)

    def test_get_steps(self):
        src = _read("mobile/modules/native-health/ios/NativeHealthModule.swift")
        self.assertIn("getSteps", src)

    def test_get_sleep_hours(self):
        src = _read("mobile/modules/native-health/ios/NativeHealthModule.swift")
        self.assertIn("getSleepHours", src)

    def test_get_activity_summary(self):
        src = _read("mobile/modules/native-health/ios/NativeHealthModule.swift")
        self.assertIn("getActivitySummary", src)

    def test_read_only_no_write(self):
        src = _read("mobile/modules/native-health/ios/NativeHealthModule.swift")
        # Only toShare: nil — never writes
        self.assertIn("toShare: nil", src)

    def test_ts_activity_summary_interface(self):
        src = _read("mobile/modules/native-health/index.ts")
        self.assertIn("ActivitySummary", src)

    def test_expo_module_config(self):
        self.assertTrue(
            (REPO_ROOT / "mobile" / "modules" / "native-health" / "expo-module.config.json").exists()
        )


# ---------------------------------------------------------------------------
# Task 4 — ProactiveEngine
# ---------------------------------------------------------------------------

class TestProactiveEngine(unittest.TestCase):

    def test_file_exists(self):
        self.assertTrue(
            (REPO_ROOT / "mobile" / "src" / "ProactiveEngine.ts").exists()
        )

    def test_meeting_prep(self):
        src = _read("mobile/src/ProactiveEngine.ts")
        self.assertIn("meeting_prep", src)

    def test_guardian_time(self):
        src = _read("mobile/src/ProactiveEngine.ts")
        self.assertIn("guardian_time", src)

    def test_morning_briefing(self):
        src = _read("mobile/src/ProactiveEngine.ts")
        self.assertIn("morning_briefing", src)

    def test_step_goal(self):
        src = _read("mobile/src/ProactiveEngine.ts")
        self.assertIn("step_goal", src)

    def test_sleep_check(self):
        src = _read("mobile/src/ProactiveEngine.ts")
        self.assertIn("sleep_check", src)

    def test_run_proactive_checks(self):
        src = _read("mobile/src/ProactiveEngine.ts")
        self.assertIn("runProactiveChecks", src)

    def test_get_greeting(self):
        src = _read("mobile/src/ProactiveEngine.ts")
        self.assertIn("getGreeting", src)

    def test_uses_native_calendar(self):
        src = _read("mobile/src/ProactiveEngine.ts")
        self.assertIn("NativeCalendar", src)

    def test_uses_native_health(self):
        src = _read("mobile/src/ProactiveEngine.ts")
        self.assertIn("NativeHealth", src)


# ---------------------------------------------------------------------------
# Task 5 — Siri Intents
# ---------------------------------------------------------------------------

class TestSiriIntents(unittest.TestCase):

    def test_file_exists(self):
        self.assertTrue(
            (REPO_ROOT / "mobile" / "modules" / "siri-intents" / "ios" / "FiresideIntents.swift").exists()
        )

    def test_ask_ember_intent(self):
        src = _read("mobile/modules/siri-intents/ios/FiresideIntents.swift")
        self.assertIn("AskEmberIntent", src)

    def test_remember_intent(self):
        src = _read("mobile/modules/siri-intents/ios/FiresideIntents.swift")
        self.assertIn("RememberIntent", src)

    def test_steps_intent(self):
        src = _read("mobile/modules/siri-intents/ios/FiresideIntents.swift")
        self.assertIn("StepsIntent", src)

    def test_app_shortcuts_provider(self):
        src = _read("mobile/modules/siri-intents/ios/FiresideIntents.swift")
        self.assertIn("AppShortcutsProvider", src)

    def test_siri_phrases(self):
        src = _read("mobile/modules/siri-intents/ios/FiresideIntents.swift")
        self.assertIn("Ask Ember", src)

    def test_remember_queues_locally(self):
        src = _read("mobile/modules/siri-intents/ios/FiresideIntents.swift")
        self.assertIn("siri_remember_queue", src)

    def test_remember_checks_atlas(self):
        src = _read("mobile/modules/siri-intents/ios/FiresideIntents.swift")
        self.assertIn("checkAtlasConnection", src)


# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------

class TestSprint12Regression(unittest.TestCase):

    def test_network_status_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/network/status", src)

    def test_guildhall_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/guildhall/agents", src)

    def test_agent_profile_preserved(self):
        src = _read("plugins/companion/handler.py")
        self.assertIn("/api/v1/agent/profile", src)


if __name__ == "__main__":
    unittest.main()

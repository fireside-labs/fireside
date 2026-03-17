"""
tests/test_thor_backend.py — Thor Sprint: Backend Infrastructure Verification

Validates all 5 tasks:
  T1. llamacpp.py Windows CUDA binary URL
  T2. LanceDB integration in working-memory
  T3. P0 plugin route registration audit
  T4. SQLite chat persistence
  T5. Installer onboarding sequence

Run:  python -m pytest tests/test_thor_backend.py -v
"""
import sys
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))
REPO_ROOT = Path(__file__).parent.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


# ===========================================================================
# T1 — llamacpp.py Windows CUDA binary URL
# ===========================================================================

class TestLlamaCppWindows(unittest.TestCase):

    def test_windows_branch_exists(self):
        src = _read("plugins/brain-installer/installers/llamacpp.py")
        self.assertIn('system == "windows"', src)

    def test_windows_cuda_url(self):
        src = _read("plugins/brain-installer/installers/llamacpp.py")
        self.assertIn("bin-win-cuda-cu12.4-x64.zip", src)

    def test_exe_detection(self):
        src = _read("plugins/brain-installer/installers/llamacpp.py")
        self.assertIn("llama-server.exe", src)

    def test_platform_string_updated(self):
        src = _read("plugins/brain-installer/installers/llamacpp.py")
        self.assertIn("Windows/Linux/Mac", src)

    def test_no_chmod_on_windows(self):
        src = _read("plugins/brain-installer/installers/llamacpp.py")
        self.assertIn('system != "windows"', src)


# ===========================================================================
# T2 — LanceDB integration in working-memory
# ===========================================================================

class TestWorkingMemoryLanceDB(unittest.TestCase):

    def test_lancedb_store_class_exists(self):
        src = _read("plugins/working-memory/handler.py")
        self.assertIn("class LanceDBStore", src)

    def test_sentence_transformer_embedder_exists(self):
        src = _read("plugins/working-memory/handler.py")
        self.assertIn("class _SentenceTransformerEmbedder", src)
        self.assertIn("all-MiniLM-L6-v2", src)

    def test_bag_of_words_fallback_exists(self):
        src = _read("plugins/working-memory/handler.py")
        self.assertIn("class _BagOfWordsEmbedder", src)
        self.assertIn("_create_embedder", src)

    def test_search_endpoint_registered(self):
        src = _read("plugins/working-memory/handler.py")
        self.assertIn("/api/v1/working-memory/search", src)

    def test_vector_search_method(self):
        src = _read("plugins/working-memory/handler.py")
        self.assertIn("def vector_search", src)

    def test_graceful_fallback(self):
        src = _read("plugins/working-memory/handler.py")
        self.assertIn("lancedb not installed", src)
        self.assertIn("in-memory-only mode", src)

    def test_observe_persists_to_lance(self):
        src = _read("plugins/working-memory/handler.py")
        # Observe should write to LanceDB
        observe_fn = src[src.find("def observe("):]
        observe_fn = observe_fn[:observe_fn.find("\n    def ")]
        self.assertIn("lance.upsert", observe_fn)

    def test_in_memory_still_works(self):
        """Verify in-memory working memory operates without LanceDB."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "wm_handler",
            str(REPO_ROOT / "plugins" / "working-memory" / "handler.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception:
            # LanceDB init may fail in test env — that's OK
            pass
        wm = mod.WorkingMemory(max_items=5, lance_store=None)
        key = wm.observe("test content", importance=0.8, source="test")
        self.assertTrue(key)
        results = wm.recall("test")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["content"], "test content")


# ===========================================================================
# T3 — P0 plugin route registration audit
# ===========================================================================

class TestP0PluginRegistration(unittest.TestCase):

    def _check_handler(self, path: str, router_name: str = "router"):
        src = _read(path)
        self.assertIn("def register_routes(", src,
                       f"Missing register_routes in {path}")
        self.assertIn("app.include_router(", src,
                       f"Missing app.include_router in {path}")

    def test_working_memory(self):
        self._check_handler("plugins/working-memory/handler.py")

    def test_companion(self):
        self._check_handler("plugins/companion/handler.py")

    def test_consumer_api(self):
        self._check_handler("plugins/consumer-api/handler.py")

    def test_brain_installer(self):
        self._check_handler("plugins/brain-installer/handler.py")

    def test_task_persistence(self):
        self._check_handler("plugins/task-persistence/handler.py")


# ===========================================================================
# T4 — SQLite chat persistence
# ===========================================================================

class TestChatPersistence(unittest.TestCase):

    def test_chat_endpoints_exist(self):
        src = _read("plugins/task-persistence/handler.py")
        self.assertIn("/api/v1/chat/history", src)
        self.assertIn("/api/v1/chat/sessions", src)

    def test_chat_db_class_exists(self):
        src = _read("plugins/task-persistence/handler.py")
        self.assertIn("class ChatDB", src)

    def test_sqlite_import(self):
        src = _read("plugins/task-persistence/handler.py")
        self.assertIn("import sqlite3", src)

    def test_chat_db_crud(self):
        """Verify ChatDB CRUD operations with a temp database."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tp_handler",
            str(REPO_ROOT / "plugins" / "task-persistence" / "handler.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ChatDB = mod.ChatDB

        import shutil
        tmp_dir = tempfile.mkdtemp()
        db_path = Path(tmp_dir) / "test_chat.db"

        db = ChatDB(db_path=db_path)

        # Save a message
        msg = db.save_message("session-1", "user", "Hello world")
        self.assertTrue(msg["id"])
        self.assertEqual(msg["session_id"], "session-1")
        self.assertEqual(msg["role"], "user")

        # Save another
        db.save_message("session-1", "assistant", "Hi there!")
        db.save_message("session-2", "user", "Different session")

        # Get history for a session
        history = db.get_history("session-1")
        self.assertEqual(len(history), 2)

        # Get all history
        all_history = db.get_history()
        self.assertEqual(len(all_history), 3)

        # List sessions
        sessions = db.list_sessions()
        self.assertEqual(len(sessions), 2)

        # Delete session
        deleted = db.delete_session("session-1")
        self.assertEqual(deleted, 2)

        # Verify deletion
        after = db.get_history("session-1")
        self.assertEqual(len(after), 0)

        # Total
        self.assertEqual(db.total_messages(), 1)

        # Cleanup (ignore Windows WAL file locking)
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

    def test_existing_task_endpoints_preserved(self):
        src = _read("plugins/task-persistence/handler.py")
        self.assertIn("/api/v1/tasks", src)
        self.assertIn("def save_task", src)
        self.assertIn("def checkpoint", src)


# ===========================================================================
# T3b — oMLX installer audit
# ===========================================================================

class TestOMLXInstaller(unittest.TestCase):

    def test_uses_sys_executable(self):
        src = _read("plugins/brain-installer/installers/omlx.py")
        self.assertIn("sys.executable", src)

    def test_no_bare_python3(self):
        """Verify no bare 'python3' subprocess calls remain."""
        src = _read("plugins/brain-installer/installers/omlx.py")
        # sys.executable should be used instead of python3 or pip3
        self.assertNotIn('"python3"', src)
        self.assertNotIn('"pip3"', src)

    def test_host_flag_in_start_server(self):
        src = _read("plugins/brain-installer/installers/omlx.py")
        self.assertIn('"--host"', src)
        self.assertIn("0.0.0.0", src)

    def test_importlib_find_spec(self):
        src = _read("plugins/brain-installer/installers/omlx.py")
        self.assertIn("find_spec", src)
        self.assertNotIn("--help", src)

    def test_get_install_info(self):
        src = _read("plugins/brain-installer/installers/omlx.py")
        self.assertIn("Apple Silicon", src)


# ===========================================================================
# T5 — Installer onboarding sequence
# ===========================================================================

class TestOnboardingSequence(unittest.TestCase):

    def test_onboard_endpoint_exists(self):
        src = _read("plugins/brain-installer/handler.py")
        self.assertIn("/api/v1/brains/onboard", src)

    def test_seven_steps_defined(self):
        src = _read("plugins/brain-installer/handler.py")
        for step_name in ["detect_gpu", "install_runtime", "download_model",
                          "install_lancedb", "install_voice_deps",
                          "start_server", "health_check"]:
            self.assertIn(step_name, src,
                          f"Missing step: {step_name}")

    def test_health_check_with_retry(self):
        src = _read("plugins/brain-installer/handler.py")
        self.assertIn("for attempt in range(10)", src)

    def test_idempotent_markers(self):
        src = _read("plugins/brain-installer/handler.py")
        self.assertIn('"already_installed"', src)

    def test_existing_brain_endpoints_preserved(self):
        src = _read("plugins/brain-installer/handler.py")
        for endpoint in ["/api/v1/brains/available", "/api/v1/brains/install",
                         "/api/v1/brains/installed", "/api/v1/brains/restart"]:
            self.assertIn(endpoint, src)


# ===========================================================================
# Frontend API client
# ===========================================================================

class TestFrontendAPI(unittest.TestCase):

    def test_onboard_function(self):
        src = _read("dashboard/lib/api.ts")
        self.assertIn("onboardBrain", src)
        self.assertIn("OnboardResult", src)

    def test_chat_functions(self):
        src = _read("dashboard/lib/api.ts")
        self.assertIn("saveChatMessage", src)
        self.assertIn("getChatHistory", src)
        self.assertIn("getChatSessions", src)
        self.assertIn("deleteChatSession", src)

    def test_memory_search(self):
        src = _read("dashboard/lib/api.ts")
        self.assertIn("searchMemory", src)

    def test_chat_types(self):
        src = _read("dashboard/lib/api.ts")
        self.assertIn("ChatMessage", src)
        self.assertIn("ChatSession", src)


# ===========================================================================
# Regression — existing functionality preserved
# ===========================================================================

class TestRegression(unittest.TestCase):

    def test_existing_api_endpoints(self):
        src = _read("api/v1.py")
        for ep in ["/status/agent", "/brains/install", "/chat"]:
            self.assertIn(ep, src)

    def test_registry_intact(self):
        src = _read("plugins/brain-installer/registry.py")
        self.assertIn("llama-3.1-8b", src)
        self.assertIn("def get_available", src)


if __name__ == "__main__":
    unittest.main()

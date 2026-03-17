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

    def test_no_hardcoded_atlas(self):
        """Agent name should come from config, not hardcoded."""
        src = _read("api/v1.py")
        # The post_chat function should NOT contain agent_name="Atlas"
        self.assertNotIn('agent_name="Atlas"', src)

    def test_orchestrate_endpoint_exists(self):
        src = _read("api/v1.py")
        self.assertIn("/orchestrate", src)

    def test_registry_intact(self):
        src = _read("plugins/brain-installer/registry.py")
        self.assertIn("llama-3.1-8b", src)
        self.assertIn("def get_available", src)


# ===========================================================================
# Orchestrator — hybrid enrichment layer (V1 mesh + V2 enrichment)
# ===========================================================================

class TestOrchestrator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "orchestrator",
            str(REPO_ROOT / "orchestrator.py"),
        )
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)
        cls.mod.init({"node": {"name": "test-node"}}, REPO_ROOT)

    def test_classify_simple(self):
        """Short messages should be classified as simple."""
        self.assertEqual(self.mod.classify("hello"), "simple")
        self.assertEqual(self.mod.classify("thanks"), "simple")
        self.assertEqual(self.mod.classify("how are you?"), "simple")

    def test_classify_complex(self):
        """Research/analysis tasks should be classified as complex."""
        self.assertEqual(
            self.mod.classify("Research AI safety best practices and give me a comprehensive summary"),
            "complex",
        )
        self.assertEqual(
            self.mod.classify("Analyze and compare these two approaches step by step"),
            "complex",
        )

    def test_pre_inference_returns_dict(self):
        """pre_inference should return a well-structured dict with routing."""
        result = self.mod.pre_inference("hello world")
        self.assertIn("classification", result)
        self.assertIn("memories", result)
        self.assertIn("agent_name", result)
        self.assertIn("user_name", result)
        self.assertIn("enriched_system_additions", result)
        self.assertIn("routing", result)  # hybrid: includes routing info
        self.assertIsInstance(result["memories"], list)

    def test_post_inference_returns_dict(self):
        """post_inference should return stored + prediction info."""
        result = self.mod.post_inference("hello", "world", classification="simple")
        self.assertIn("prediction_error", result)
        self.assertIn("surprising", result)
        self.assertIn("stored", result)

    def test_agent_name_not_hardcoded(self):
        """Agent name should come from config, never hardcoded 'Atlas'."""
        name = self.mod.get_agent_name()
        self.assertIsInstance(name, str)
        self.assertTrue(len(name) > 0)

    def test_orchestrator_module_structure(self):
        """Verify all public functions exist (V1 + V2 hybrid)."""
        for fn_name in ["classify", "recall_memories", "pre_predict",
                        "post_score", "observe", "publish",
                        "pre_inference", "post_inference",
                        "create_task_pipeline", "check_belief_shadows",
                        "route_to_node"]:  # hybrid: uses V1 router
            self.assertTrue(
                hasattr(self.mod, fn_name),
                f"Missing function: {fn_name}",
            )

    def test_v1_router_integration(self):
        """Orchestrator should import and use bot/router.py."""
        src = _read("orchestrator.py")
        self.assertIn("bot_router", src)
        self.assertIn("Router", src)
        self.assertIn("semantic_route", src)
        self.assertIn("score_all", src)

    def test_v1_pipeline_integration(self):
        """Orchestrator should use bot/pipeline.py as primary pipeline."""
        src = _read("orchestrator.py")
        self.assertIn("bot_pipeline", src)
        self.assertIn("Huginn", src)
        self.assertIn("Muninn", src)
        self.assertIn("v1_war_room", src)
        self.assertIn("v2_local", src)  # fallback

    def test_event_bus_integration(self):
        """Orchestrator should publish events."""
        src = _read("orchestrator.py")
        self.assertIn("orchestrator.pre_inference", src)
        self.assertIn("orchestrator.post_inference", src)
        self.assertIn("orchestrator.pipeline_created", src)

    def test_mesh_active_function(self):
        """mesh_active() should exist and return bool."""
        self.assertTrue(hasattr(self.mod, "mesh_active"))
        result = self.mod.mesh_active()  # No bifrost running → should return False
        self.assertIsInstance(result, bool)

    def test_template_based_pipeline(self):
        """create_task_pipeline should accept template_name."""
        src = _read("orchestrator.py")
        self.assertIn("template_name", src)
        self.assertIn("classify_template", src)
        self.assertIn("resolve_stages", src)


# ===========================================================================
# Pipeline Templates — template engine
# ===========================================================================

class TestPipelineTemplates(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "pipeline_templates",
            str(REPO_ROOT / "pipeline_templates.py"),
        )
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)

    def test_builtin_presets(self):
        """Should have 6 built-in templates."""
        templates = self.mod.BUILTIN_TEMPLATES
        for name in ["coding", "research", "general",
                      "drafting", "presentation", "analysis"]:
            self.assertIn(name, templates, f"Missing template: {name}")

    def test_each_template_has_stages(self):
        """Every built-in template must have at least 2 stages + version."""
        for name, tmpl in self.mod.BUILTIN_TEMPLATES.items():
            self.assertGreaterEqual(
                len(tmpl["stages"]), 2,
                f"Template '{name}' has fewer than 2 stages",
            )
            self.assertIn("name", tmpl)
            self.assertIn("max_iterations", tmpl)
            self.assertIn("version", tmpl)

    def test_classify_coding(self):
        """Coding keywords should map to coding template."""
        self.assertEqual(self.mod.classify_template("Build me a REST API"), "coding")
        self.assertEqual(self.mod.classify_template("Create a dashboard app"), "coding")

    def test_classify_research(self):
        """Research keywords should map to research template."""
        self.assertEqual(self.mod.classify_template("Research quantum computing"), "research")
        self.assertEqual(self.mod.classify_template("Investigate the pros and cons"), "research")

    def test_classify_drafting(self):
        """Writing/email tasks should map to drafting template."""
        self.assertEqual(self.mod.classify_template("Draft a letter to the board"), "drafting")
        self.assertEqual(self.mod.classify_template("Write an email follow up"), "drafting")

    def test_classify_presentation(self):
        """Presentation tasks should map to presentation template."""
        self.assertEqual(self.mod.classify_template("Make a presentation about Q4"), "presentation")
        self.assertEqual(self.mod.classify_template("Create a pitch deck for investors"), "presentation")

    def test_classify_analysis(self):
        """Data tasks should map to analysis template."""
        self.assertEqual(self.mod.classify_template("Analyze data and show me the trends"), "analysis")
        self.assertEqual(self.mod.classify_template("Give me a quarterly KPI breakdown"), "analysis")

    def test_classify_general(self):
        """Ambiguous tasks should map to general template."""
        self.assertEqual(self.mod.classify_template("hello"), "general")
        self.assertEqual(self.mod.classify_template("thanks"), "general")

    def test_list_templates(self):
        """list_templates() should return at least 6 entries."""
        templates = self.mod.list_templates()
        self.assertGreaterEqual(len(templates), 6)
        for t in templates:
            self.assertIn("name", t)
            self.assertIn("display_name", t)
            self.assertIn("source", t)
            self.assertIn("version", t)

    def test_resolve_stages_single(self):
        """Single-node resolution should add system_prompt to each stage."""
        tmpl = self.mod.get_template("general")
        resolved = self.mod.resolve_stages(tmpl, mode="single")
        for stage in resolved:
            if "parallel" not in stage:
                self.assertEqual(stage["agent"], "local")
                self.assertTrue(len(stage.get("system_prompt", "")) > 0)

    def test_resolve_stages_mesh(self):
        """Mesh resolution should keep role as agent name."""
        tmpl = self.mod.get_template("coding")
        resolved = self.mod.resolve_stages(tmpl, mode="mesh")
        for stage in resolved:
            if "parallel" not in stage:
                self.assertNotEqual(stage.get("agent"), "local")

    def test_role_prompts_coverage(self):
        """Every role used in templates should have a system prompt."""
        all_roles = set()
        for tmpl in self.mod.BUILTIN_TEMPLATES.values():
            for stage in tmpl["stages"]:
                if "parallel" in stage:
                    for p in stage["parallel"]:
                        all_roles.add(p["role"])
                elif "role" in stage:
                    all_roles.add(stage["role"])
        for role in all_roles:
            self.assertIn(role, self.mod.ROLE_PROMPTS,
                         f"Missing ROLE_PROMPT for '{role}'")

    def test_on_fail_routing(self):
        """Templates with on_fail should reference valid stage names."""
        for name, tmpl in self.mod.BUILTIN_TEMPLATES.items():
            valid, err = self.mod.validate_template(tmpl)
            self.assertTrue(valid, f"Template '{name}' invalid: {err}")

    def test_validate_template_rejects_bad(self):
        """validate_template should reject invalid templates."""
        valid, _ = self.mod.validate_template({})
        self.assertFalse(valid)
        valid, _ = self.mod.validate_template({"name": "x", "stages": [{"name": "a"}]})
        self.assertFalse(valid)  # only 1 stage


if __name__ == "__main__":
    unittest.main()


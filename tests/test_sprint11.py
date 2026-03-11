"""
Tests for Sprint 11 — GitHub Metadata + Rebrand.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(os.path.dirname(__file__)).parent


class TestRebrand:
    def test_readme_says_fireside(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        assert "Fireside" in readme

    def test_readme_no_valhalla_in_header(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        # First heading should be Fireside, not Valhalla
        lines = readme.split("\n")
        h1 = next(l for l in lines if l.startswith("# "))
        assert "Fireside" in h1
        assert "Valhalla" not in h1

    def test_install_url_updated(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        assert "getfireside.ai" in readme

    def test_badges_present(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        assert "img.shields.io" in readme
        assert "License" in readme

    def test_cta_fireside(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        assert "Start a Fireside" in readme

    def test_12_sprints_in_footer(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        assert "12 sprints" in readme

"""Tests for repository specifier classification."""

from __future__ import annotations

from pathlib import Path

import pytest

from anvil.classify import classify_all, classify_specifier
from anvil.exceptions import DuplicateRepoNameError
from anvil.models import SpecifierType


class TestClassifySpecifier:
    def test_existing_local_path_is_path_type(self, tmp_path: Path) -> None:
        repo_dir = tmp_path / "myrepo"
        repo_dir.mkdir()
        spec = classify_specifier(str(repo_dir))
        assert spec.specifier_type == SpecifierType.PATH
        assert spec.name == "myrepo"

    def test_nonexistent_path_is_url_type(self) -> None:
        spec = classify_specifier("https://github.com/org/myrepo.git")
        assert spec.specifier_type == SpecifierType.URL
        assert spec.name == "myrepo"

    def test_specifier_preserved(self, tmp_path: Path) -> None:
        repo_dir = tmp_path / "myrepo"
        repo_dir.mkdir()
        spec = classify_specifier(str(repo_dir))
        assert spec.specifier == str(repo_dir)


class TestClassifyAll:
    def test_duplicate_names_raises(self, tmp_path: Path) -> None:
        dir_a = tmp_path / "myrepo"
        dir_a.mkdir()
        # Two specifiers that derive the same name
        with pytest.raises(DuplicateRepoNameError) as exc_info:
            classify_all([str(dir_a), "https://github.com/org/myrepo.git"])
        assert "myrepo" in str(exc_info.value)

    def test_unique_names_ok(self, tmp_path: Path) -> None:
        dir_a = tmp_path / "repo-a"
        dir_a.mkdir()
        specs = classify_all([str(dir_a), "https://github.com/org/repo-b.git"])
        assert len(specs) == 2
        assert specs[0].name == "repo-a"
        assert specs[1].name == "repo-b"

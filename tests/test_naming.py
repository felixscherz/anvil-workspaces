"""Tests for branch name sanitization and repository name derivation."""

from __future__ import annotations

from pathlib import Path

import pytest

from anvil.exceptions import EmptyBranchNameError, EmptyRepoNameError
from anvil.naming import (
    derive_repo_name_from_specifier,
    infer_branch_name,
)


class TestInferBranchName:
    def test_simple_name(self, tmp_path: Path) -> None:
        target = tmp_path / "feature-abc"
        assert infer_branch_name(target) == "feature-abc"

    def test_uppercase_converted_to_lowercase(self, tmp_path: Path) -> None:
        target = tmp_path / "Feature-ABC"
        assert infer_branch_name(target) == "feature-abc"

    def test_spaces_replaced_with_dash(self, tmp_path: Path) -> None:
        target = tmp_path / "my feature"
        assert infer_branch_name(target) == "my-feature"

    def test_repeated_separators_collapsed(self, tmp_path: Path) -> None:
        target = tmp_path / "foo--bar"
        assert infer_branch_name(target) == "foo-bar"

    def test_leading_trailing_dashes_trimmed(self, tmp_path: Path) -> None:
        target = tmp_path / "-feature-"
        assert infer_branch_name(target) == "feature"

    def test_invalid_chars_replaced(self, tmp_path: Path) -> None:
        target = tmp_path / "feat@ure"
        result = infer_branch_name(target)
        assert "@" not in result

    def test_raises_on_empty_result(self, tmp_path: Path) -> None:
        # A name that sanitizes to empty (e.g., all invalid chars)
        target = tmp_path / "---"
        with pytest.raises(EmptyBranchNameError):
            infer_branch_name(target)


class TestDeriveRepoNameFromSpecifier:
    def test_https_url(self) -> None:
        assert (
            derive_repo_name_from_specifier("https://github.com/org/myrepo.git")
            == "myrepo"
        )

    def test_https_url_no_git_suffix(self) -> None:
        assert (
            derive_repo_name_from_specifier("https://github.com/org/myrepo") == "myrepo"
        )

    def test_ssh_url(self) -> None:
        assert (
            derive_repo_name_from_specifier("git@github.com:org/myrepo.git") == "myrepo"
        )

    def test_ssh_url_no_git_suffix(self) -> None:
        assert derive_repo_name_from_specifier("git@github.com:org/myrepo") == "myrepo"

    def test_trailing_slash_stripped(self) -> None:
        assert (
            derive_repo_name_from_specifier("https://github.com/org/myrepo/")
            == "myrepo"
        )

    def test_raises_on_empty(self) -> None:
        with pytest.raises(EmptyRepoNameError):
            derive_repo_name_from_specifier("")

"""Integration tests for the create workflow."""

from __future__ import annotations

from pathlib import Path

import pytest

from anvil.classify import classify_all
from anvil.create import run_create, validate_target
from anvil.exceptions import (
    BranchAlreadyExistsError,
    TargetNotEmptyError,
    TargetParentMissingError,
)
from anvil.manifest import read_manifest
from anvil.models import CreationMode


class TestValidateTarget:
    def test_target_parent_missing_raises(self, tmp_path: Path) -> None:
        target = tmp_path / "missing_parent" / "workspace"
        with pytest.raises(TargetParentMissingError):
            validate_target(target)

    def test_target_exists_and_nonempty_raises(self, tmp_path: Path) -> None:
        target = tmp_path / "workspace"
        target.mkdir()
        (target / "file.txt").write_text("hi")
        with pytest.raises(TargetNotEmptyError):
            validate_target(target)

    def test_target_nonexistent_ok(self, tmp_path: Path) -> None:
        target = tmp_path / "workspace"
        validate_target(target)  # no exception

    def test_target_exists_and_empty_ok(self, tmp_path: Path) -> None:
        target = tmp_path / "workspace"
        target.mkdir()
        validate_target(target)  # no exception


class TestCreateWithWorktree:
    def test_creates_worktree_and_manifest(
        self, tmp_path: Path, local_repo: Path
    ) -> None:
        target = tmp_path / "workspace"
        specs = classify_all([str(local_repo)])
        run_create(target, specs, "feature-test")

        assert target.exists()
        repo_path = target / local_repo.name
        assert repo_path.exists()
        assert (repo_path / "README.md").exists()

        # Manifest is written
        loaded = read_manifest(target)
        assert loaded.branch_name == "feature-test"
        assert len(loaded.repos) == 1
        assert loaded.repos[0].creation_mode == CreationMode.WORKTREE
        assert loaded.repos[0].branch == "feature-test"

    def test_fails_if_not_a_git_repo(self, tmp_path: Path) -> None:
        notgit = tmp_path / "notgit"
        notgit.mkdir()
        target = tmp_path / "workspace"
        specs = classify_all([str(notgit)])
        with pytest.raises(Exception):
            run_create(target, specs, "feature-test")

    def test_fails_if_no_origin_remote(self, tmp_path: Path) -> None:
        from tests.conftest import init_git_repo, make_initial_commit

        repo = tmp_path / "no_origin"
        init_git_repo(repo)
        make_initial_commit(repo)

        target = tmp_path / "workspace"
        specs = classify_all([str(repo)])
        with pytest.raises(Exception):
            run_create(target, specs, "feature-test")

    def test_rollback_on_failure(self, tmp_path: Path, local_repo: Path) -> None:
        """
        When the second repo fails, the first worktree should be rolled back.
        """
        notgit = tmp_path / "notgit"
        notgit.mkdir()
        target = tmp_path / "workspace"
        specs = classify_all([str(local_repo), str(notgit)])

        with pytest.raises(Exception):
            run_create(target, specs, "feature-rollback")

        # Worktree for local_repo should be cleaned up
        # The branch should not exist in the source repo
        import subprocess

        result = subprocess.run(
            ["git", "branch", "--list", "feature-rollback"],
            cwd=local_repo,
            capture_output=True,
            text=True,
        )
        assert "feature-rollback" not in result.stdout

    def test_manifest_not_written_on_partial_failure(
        self, tmp_path: Path, local_repo: Path
    ) -> None:
        notgit = tmp_path / "notgit"
        notgit.mkdir()
        target = tmp_path / "workspace"
        specs = classify_all([str(local_repo), str(notgit)])

        with pytest.raises(Exception):
            run_create(target, specs, "feature-x")

        from anvil.exceptions import ManifestNotFoundError

        with pytest.raises(ManifestNotFoundError):
            read_manifest(target)

    def test_branch_already_exists_fails(
        self, tmp_path: Path, local_repo: Path
    ) -> None:
        """Creating a worktree with an already-existing branch name should fail."""
        import subprocess

        from anvil.exceptions import CreateFailedError

        subprocess.run(
            ["git", "branch", "already-exists", "HEAD"],
            cwd=local_repo,
            check=True,
        )
        target = tmp_path / "workspace"
        specs = classify_all([str(local_repo)])
        with pytest.raises(CreateFailedError) as exc_info:
            run_create(target, specs, "already-exists")
        assert isinstance(exc_info.value.cause, BranchAlreadyExistsError)

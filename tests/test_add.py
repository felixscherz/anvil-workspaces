"""Tests for the add workflow."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from anvil.classify import classify_all
from anvil.cli import app
from anvil.create import run_add, run_create
from anvil.exceptions import (
    NotAnAnvilWorkspaceError,
    RepoAlreadyInWorkspaceError,
)
from anvil.manifest import read_manifest
from anvil.models import CreationMode

runner = CliRunner()


class TestRunAdd:
    def test_adds_repo_to_existing_workspace(
        self, tmp_path: Path, local_repo: Path, bare_remote: Path
    ) -> None:
        # Create a second local repo from the same bare remote
        second_repo = tmp_path / "second_repo"
        import subprocess

        subprocess.run(["git", "clone", str(bare_remote), str(second_repo)], check=True)
        subprocess.run(
            ["git", "remote", "set-head", "origin", "main"], cwd=second_repo, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@anvil.test"],
            cwd=second_repo,
            check=True,
        )

        target = tmp_path / "workspace"
        specs = classify_all([str(local_repo)])
        run_create(target, specs, "feature-add")

        add_specs = classify_all([str(second_repo)])
        manifest = run_add(target, add_specs)

        assert len(manifest.repos) == 2
        assert manifest.repos[1].name == second_repo.name
        assert manifest.repos[1].branch == "feature-add"
        assert manifest.repos[1].creation_mode == CreationMode.WORKTREE
        assert (target / second_repo.name).exists()

    def test_branch_name_taken_from_manifest(
        self, tmp_path: Path, local_repo: Path, bare_remote: Path
    ) -> None:
        """The branch on the added repo must match the workspace branch, not a re-derived name."""
        import subprocess

        second_repo = tmp_path / "second_repo"
        subprocess.run(["git", "clone", str(bare_remote), str(second_repo)], check=True)
        subprocess.run(
            ["git", "remote", "set-head", "origin", "main"], cwd=second_repo, check=True
        )

        # Create workspace with a branch name that differs from the target basename
        # by using a target whose basename would sanitize to something specific
        target = tmp_path / "my-task-123"
        specs = classify_all([str(local_repo)])
        run_create(target, specs, "my-task-123")

        add_specs = classify_all([str(second_repo)])
        manifest = run_add(target, add_specs)

        assert manifest.repos[1].branch == "my-task-123"

    def test_manifest_preserved_after_add(
        self, tmp_path: Path, local_repo: Path, bare_remote: Path
    ) -> None:
        import subprocess

        second_repo = tmp_path / "second_repo"
        subprocess.run(["git", "clone", str(bare_remote), str(second_repo)], check=True)
        subprocess.run(
            ["git", "remote", "set-head", "origin", "main"], cwd=second_repo, check=True
        )

        target = tmp_path / "workspace"
        specs = classify_all([str(local_repo)])
        original = run_create(target, specs, "feature-add")

        add_specs = classify_all([str(second_repo)])
        run_add(target, add_specs)

        reloaded = read_manifest(target)
        assert reloaded.branch_name == original.branch_name
        assert reloaded.created_at == original.created_at
        assert len(reloaded.repos) == 2

    def test_fails_on_nonexistent_workspace(
        self, tmp_path: Path, local_repo: Path
    ) -> None:
        specs = classify_all([str(local_repo)])
        with pytest.raises(NotAnAnvilWorkspaceError):
            run_add(tmp_path / "does-not-exist", specs)

    def test_fails_on_duplicate_name_in_workspace(
        self, tmp_path: Path, local_repo: Path
    ) -> None:
        target = tmp_path / "workspace"
        specs = classify_all([str(local_repo)])
        run_create(target, specs, "feature-dup")

        # Try to add the same repo again
        add_specs = classify_all([str(local_repo)])
        with pytest.raises(RepoAlreadyInWorkspaceError) as exc_info:
            run_add(target, add_specs)
        assert local_repo.name in str(exc_info.value)

    def test_rollback_on_add_failure(
        self, tmp_path: Path, local_repo: Path, bare_remote: Path
    ) -> None:
        import subprocess

        second_repo = tmp_path / "second_repo"
        subprocess.run(["git", "clone", str(bare_remote), str(second_repo)], check=True)
        subprocess.run(
            ["git", "remote", "set-head", "origin", "main"], cwd=second_repo, check=True
        )

        notgit = tmp_path / "notgit"
        notgit.mkdir()

        target = tmp_path / "workspace"
        specs = classify_all([str(local_repo)])
        run_create(target, specs, "feature-rollback-add")

        # Add second_repo (ok) and notgit (will fail) together
        add_specs = classify_all([str(second_repo), str(notgit)])
        with pytest.raises(Exception):
            run_add(target, add_specs)

        # Manifest should still only have the original repo
        reloaded = read_manifest(target)
        assert len(reloaded.repos) == 1

        # Branch on second_repo should have been rolled back
        result = subprocess.run(
            ["git", "branch", "--list", "feature-rollback-add"],
            cwd=second_repo,
            capture_output=True,
            text=True,
        )
        assert "feature-rollback-add" not in result.stdout


class TestAddCLI:
    def test_add_via_cli(
        self, tmp_path: Path, local_repo: Path, bare_remote: Path
    ) -> None:
        import subprocess

        second_repo = tmp_path / "second_repo"
        subprocess.run(["git", "clone", str(bare_remote), str(second_repo)], check=True)
        subprocess.run(
            ["git", "remote", "set-head", "origin", "main"], cwd=second_repo, check=True
        )

        target = tmp_path / "workspace"
        specs = classify_all([str(local_repo)])
        run_create(target, specs, "feature-cli-add")

        result = runner.invoke(app, ["add", "--target", str(target), str(second_repo)])
        assert result.exit_code == 0, result.output
        assert second_repo.name in result.output

    def test_add_no_repos_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["add", "--target", str(tmp_path)])
        assert result.exit_code != 0

    def test_add_nonexistent_workspace_fails(
        self, tmp_path: Path, local_repo: Path
    ) -> None:
        result = runner.invoke(
            app,
            ["add", "--target", str(tmp_path / "nope"), str(local_repo)],
        )
        assert result.exit_code != 0

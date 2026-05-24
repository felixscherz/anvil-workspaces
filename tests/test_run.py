"""Tests for anvil run command."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from anvil.cli import app
from anvil.classify import classify_all
from anvil.create import run_create
from anvil.run import run_command

runner = CliRunner()


@pytest.fixture
def workspace(tmp_path: Path, local_repo: Path) -> Path:
    """A minimal workspace with one repo."""
    target = tmp_path / "my-workspace"
    specs = classify_all([str(local_repo)])
    run_create(target, specs, "feature-run-tests")
    return target


@pytest.fixture
def two_repo_workspace(tmp_path: Path, bare_remote: Path) -> Path:
    """A workspace with two repos cloned from the same bare remote."""
    import subprocess

    # Create two local repos from the same bare remote
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    subprocess.run(
        ["git", "clone", str(bare_remote), str(repo_a)], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@anvil.test"],
        cwd=repo_a,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Anvil Test"],
        cwd=repo_a,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "remote", "set-head", "origin", "main"],
        cwd=repo_a,
        check=True,
        capture_output=True,
    )

    subprocess.run(
        ["git", "clone", str(bare_remote), str(repo_b)], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@anvil.test"],
        cwd=repo_b,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Anvil Test"],
        cwd=repo_b,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "remote", "set-head", "origin", "main"],
        cwd=repo_b,
        check=True,
        capture_output=True,
    )

    target = tmp_path / "my-workspace"
    specs = classify_all([str(repo_a), str(repo_b)])
    run_create(target, specs, "feature-two-repos")
    return target


class TestRunSequential:
    def test_successful_command_returns_zero(self, workspace: Path) -> None:
        rc = run_command(workspace, ["git", "status"])
        assert rc == 0

    def test_failing_command_returns_nonzero(self, workspace: Path) -> None:
        rc = run_command(workspace, ["git", "log", "--invalid-flag-xyz"])
        assert rc != 0

    def test_stops_on_first_failure(self, two_repo_workspace: Path) -> None:
        """Sequential mode: a failing command stops further execution."""
        # Use a command that will fail; only one repo's output should appear
        # We verify by counting prefix lines in stdout via the CLI
        result = runner.invoke(
            app,
            [
                "run",
                "--workspace",
                str(two_repo_workspace),
                "--",
                "git",
                "log",
                "--invalid-flag-xyz",
            ],
        )
        assert result.exit_code != 0
        # Only one [repo-name] prefix should appear (stopped after first failure)
        prefix_count = result.output.count("] $ git log")
        assert prefix_count == 1

    def test_all_repos_run_when_successful(self, two_repo_workspace: Path) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "--workspace",
                str(two_repo_workspace),
                "--",
                "git",
                "status",
            ],
        )
        assert result.exit_code == 0
        prefix_count = result.output.count("] $ git status")
        assert prefix_count == 2


class TestRunParallel:
    def test_successful_command_returns_zero(self, workspace: Path) -> None:
        rc = run_command(workspace, ["git", "status"], parallel=True)
        assert rc == 0

    def test_all_repos_run_even_on_failure(self, two_repo_workspace: Path) -> None:
        """Parallel mode: all repos run regardless of individual failures."""
        result = runner.invoke(
            app,
            [
                "run",
                "--workspace",
                str(two_repo_workspace),
                "--parallel",
                "--",
                "git",
                "log",
                "--invalid-flag-xyz",
            ],
        )
        assert result.exit_code != 0
        # Both repos should have been attempted
        prefix_count = result.output.count("] $ git log")
        assert prefix_count == 2

    def test_parallel_all_succeed(self, two_repo_workspace: Path) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "--workspace",
                str(two_repo_workspace),
                "--parallel",
                "--",
                "git",
                "status",
            ],
        )
        assert result.exit_code == 0
        prefix_count = result.output.count("] $ git status")
        assert prefix_count == 2


class TestRunCLI:
    def test_no_command_fails(self, workspace: Path) -> None:
        result = runner.invoke(
            app,
            ["run", "--workspace", str(workspace)],
        )
        assert result.exit_code != 0

    def test_invalid_workspace_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "--workspace",
                str(tmp_path / "nonexistent"),
                "--",
                "git",
                "status",
            ],
        )
        assert result.exit_code != 0

    def test_output_contains_repo_prefix(self, workspace: Path) -> None:
        result = runner.invoke(
            app,
            ["run", "--workspace", str(workspace), "--", "git", "status"],
        )
        assert result.exit_code == 0
        # Output should contain a [repo-name] prefix
        assert "] $ git status" in result.output

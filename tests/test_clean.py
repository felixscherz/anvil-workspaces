"""Integration tests for the clean workflow."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from anvil.classify import classify_all
from anvil.clean import run_clean
from anvil.cli import app
from anvil.create import run_create
from anvil.exceptions import ManifestNotFoundError


runner = CliRunner()


class TestClean:
    def test_clean_removes_workspace(self, tmp_path: Path, local_repo: Path) -> None:
        target = tmp_path / "workspace"
        specs = classify_all([str(local_repo)])
        run_create(target, specs, "feature-clean")

        # Worktree should exist
        assert (target / local_repo.name).exists()

        run_clean(target, yes=True)

        assert not target.exists()

    def test_clean_removes_worktree_branch(
        self, tmp_path: Path, local_repo: Path
    ) -> None:
        import subprocess

        target = tmp_path / "workspace"
        specs = classify_all([str(local_repo)])
        run_create(target, specs, "feature-branchclean")

        run_clean(target, yes=True)

        result = subprocess.run(
            ["git", "branch", "--list", "feature-branchclean"],
            cwd=local_repo,
            capture_output=True,
            text=True,
        )
        assert "feature-branchclean" not in result.stdout

    def test_clean_no_manifest_fails(self, tmp_path: Path) -> None:
        with pytest.raises(ManifestNotFoundError):
            run_clean(tmp_path / "no-workspace", yes=True)

    def test_clean_requires_confirmation_via_cli(
        self, tmp_path: Path, local_repo: Path
    ) -> None:
        target = tmp_path / "workspace"
        specs = classify_all([str(local_repo)])
        run_create(target, specs, "feature-confirm")

        # Provide 'N' to cancel
        result = runner.invoke(
            app,
            ["clean", "--target", str(target)],
            input="N\n",
        )
        # Should not have removed
        assert target.exists()
        assert result.exit_code == 0

    def test_clean_yes_flag_skips_prompt(
        self, tmp_path: Path, local_repo: Path
    ) -> None:
        target = tmp_path / "workspace"
        specs = classify_all([str(local_repo)])
        run_create(target, specs, "feature-yes")

        result = runner.invoke(
            app,
            ["clean", "--target", str(target), "--yes"],
        )
        assert result.exit_code == 0
        assert not target.exists()

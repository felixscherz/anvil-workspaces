"""CLI-level tests using CliRunner."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from anvil.cli import app

runner = CliRunner()


class TestCreateCLI:
    def test_create_no_repos_fails(self, tmp_path: Path) -> None:
        target = tmp_path / "workspace"
        result = runner.invoke(app, ["create", "--target", str(target)])
        assert result.exit_code != 0

    def test_create_nonempty_target_fails(self, tmp_path: Path) -> None:
        target = tmp_path / "workspace"
        target.mkdir()
        (target / "file.txt").write_text("hi")
        result = runner.invoke(
            app, ["create", "--target", str(target), "https://github.com/org/repo.git"]
        )
        assert result.exit_code != 0
        assert (
            "not empty" in result.output.lower()
            or "not empty" in (result.stderr or "").lower()
        )

    def test_create_missing_parent_fails(self, tmp_path: Path) -> None:
        target = tmp_path / "missing" / "workspace"
        result = runner.invoke(
            app, ["create", "--target", str(target), "https://github.com/org/repo.git"]
        )
        assert result.exit_code != 0

    def test_create_with_local_repo(self, tmp_path: Path, local_repo: Path) -> None:
        target = tmp_path / "workspace"
        result = runner.invoke(
            app, ["create", "--target", str(target), str(local_repo)]
        )
        assert result.exit_code == 0, result.output
        assert "Created Anvil workspace" in result.output
        assert local_repo.name in result.output

    def test_create_duplicate_repo_names_fails(
        self, tmp_path: Path, local_repo: Path
    ) -> None:
        target = tmp_path / "workspace"
        # Pass the same local repo twice (same derived name)
        result = runner.invoke(
            app,
            ["create", "--target", str(target), str(local_repo), str(local_repo)],
        )
        assert result.exit_code != 0


class TestCleanCLI:
    def test_clean_nonexistent_workspace_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app, ["clean", "--target", str(tmp_path / "nope"), "--yes"]
        )
        assert result.exit_code != 0

    def test_clean_with_yes(self, tmp_path: Path, local_repo: Path) -> None:
        from anvil.classify import classify_all
        from anvil.create import run_create

        target = tmp_path / "workspace"
        specs = classify_all([str(local_repo)])
        run_create(target, specs, "feature-cli-clean")

        result = runner.invoke(app, ["clean", "--target", str(target), "--yes"])
        assert result.exit_code == 0
        assert not target.exists()

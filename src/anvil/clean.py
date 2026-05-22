"""Workspace cleanup workflow."""

from __future__ import annotations

import shutil
from pathlib import Path

import typer

from anvil import git
from anvil.manifest import anvil_dir, manifest_path, read_manifest
from anvil.models import CreationMode, Manifest
from anvil.prompts import confirm_clean


def _clean_repo(entry: object, manifest: Manifest) -> None:
    from anvil.models import RepoEntry  # avoid circular at module level

    assert isinstance(entry, RepoEntry)
    if entry.creation_mode == CreationMode.WORKTREE:
        source = Path(entry.specifier)
        try:
            git.remove_worktree(source, entry.repo_path)
        except Exception as e:
            typer.echo(
                f"  Warning: could not remove worktree {entry.repo_path}: {e}", err=True
            )
        try:
            git.delete_branch(source, entry.branch)
        except Exception as e:
            typer.echo(
                f"  Warning: could not delete branch {entry.branch} in {source}: {e}",
                err=True,
            )
    elif entry.creation_mode == CreationMode.CLONE:
        if entry.repo_path.exists():
            shutil.rmtree(entry.repo_path)
        else:
            typer.echo(
                f"  Warning: clone path {entry.repo_path} not found, skipping.",
                err=True,
            )


def run_clean(target: Path, yes: bool = False) -> None:
    """Read the manifest and clean up the workspace."""
    manifest = read_manifest(target)

    typer.echo(f"Anvil workspace: {manifest.workspace_root}")
    typer.echo(f"Branch: {manifest.branch_name}")
    typer.echo(f"Repositories ({len(manifest.repos)}):")
    for entry in manifest.repos:
        typer.echo(
            f"  - {entry.name} ({entry.creation_mode.value}) -> {entry.repo_path}"
        )

    if not yes:
        confirmed = confirm_clean(str(manifest.workspace_root), len(manifest.repos))
        if not confirmed:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    for entry in manifest.repos:
        typer.echo(f"  Removing {entry.name}...")
        _clean_repo(entry, manifest)

    # Remove manifest and .anvil dir
    mp = manifest_path(target)
    if mp.exists():
        mp.unlink()
    ad = anvil_dir(target)
    if ad.exists():
        try:
            ad.rmdir()
        except OSError:
            shutil.rmtree(ad)

    # Remove target directory
    if target.exists():
        try:
            target.rmdir()
        except OSError:
            # Not empty (perhaps user added files); warn instead of force-removing
            typer.echo(
                f"Warning: workspace directory {target} is not empty, not removing it.",
                err=True,
            )

    typer.echo(f"Removed Anvil workspace: {manifest.workspace_root}")

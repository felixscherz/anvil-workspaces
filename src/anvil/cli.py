"""Typer CLI app and argument definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from anvil.classify import classify_all
from anvil.clean import run_clean
from anvil.create import run_add, run_create
from anvil.exceptions import AnvilError, NoRepoSpecifiersError
from anvil.naming import infer_branch_name

_BANNER = """\
 █████╗ ███╗   ██╗██╗   ██╗██╗██╗     
██╔══██╗████╗  ██║██║   ██║██║██║     
███████║██╔██╗ ██║██║   ██║██║██║     
██╔══██║██║╚██╗██║╚██╗ ██╔╝██║██║     
██║  ██║██║ ╚████║ ╚████╔╝ ██║███████╗
╚═╝  ╚═╝╚═╝  ╚═══╝  ╚═══╝  ╚═╝╚══════╝"""

_DESCRIPTION = "Create isolated multi-repository workspaces for engineering tasks."

app = typer.Typer(
    name="anvil",
    help=f"\b\n{_BANNER}\n\n{_DESCRIPTION}",
    add_completion=False,
    rich_markup_mode=None,
)


@app.command("create")
def create_command(
    target: Annotated[
        Path,
        typer.Option(
            "--target", help="Target workspace directory.", show_default=False
        ),
    ],
    repos: Annotated[
        list[str],
        typer.Argument(help="Repository specifiers (local paths or clone URLs)."),
    ],
) -> None:
    """Create a multi-repository workspace at TARGET."""
    try:
        if not repos:
            raise NoRepoSpecifiersError()

        from anvil.create import validate_target

        validate_target(target)

        branch = infer_branch_name(target)
        specs = classify_all(repos)

        typer.echo(f"Creating Anvil workspace: {target.resolve()}")
        typer.echo(f"Branch: {branch}")

        manifest = run_create(target.resolve(), specs, branch)

        typer.echo(f"\nCreated Anvil workspace: {manifest.workspace_root}")
        typer.echo(f"Branch: {manifest.branch_name}")
        for entry in manifest.repos:
            typer.echo(f"  - {entry.name} -> {entry.repo_path}")

    except AnvilError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command("clean")
def clean_command(
    target: Annotated[
        Path,
        typer.Option(
            "--target", help="Target workspace directory.", show_default=False
        ),
    ],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Remove the workspace described by the manifest at TARGET."""
    try:
        run_clean(target.resolve(), yes=yes)
    except AnvilError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command("add")
def add_command(
    target: Annotated[
        Path,
        typer.Option(
            "--target", help="Path to an existing Anvil workspace.", show_default=False
        ),
    ],
    repos: Annotated[
        list[str],
        typer.Argument(help="Repository specifiers (local paths or clone URLs)."),
    ],
) -> None:
    """Add repositories to an existing workspace at TARGET."""
    try:
        if not repos:
            raise NoRepoSpecifiersError()

        specs = classify_all(repos)
        manifest = run_add(target.resolve(), specs)

        typer.echo(f"\nUpdated Anvil workspace: {manifest.workspace_root}")
        typer.echo(f"Branch: {manifest.branch_name}")
        for entry in manifest.repos:
            typer.echo(f"  - {entry.name} -> {entry.repo_path}")

    except AnvilError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

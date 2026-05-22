"""Interactive confirmation helpers."""

from __future__ import annotations

import typer


def confirm_clean(workspace_root: str, repo_count: int) -> bool:
    """
    Prompt the user to confirm workspace removal.
    Returns True if the user confirms, False otherwise.
    """
    prompt = (
        f"Remove Anvil workspace at {workspace_root} "
        f"containing {repo_count} repositories? [y/N] "
    )
    response = typer.prompt(prompt, default="N", show_default=False)
    return response.strip().lower() in ("y", "yes")

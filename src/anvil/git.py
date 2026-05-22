"""Subprocess wrapper around Git commands."""

from __future__ import annotations

import subprocess
from pathlib import Path

from anvil.exceptions import GitCommandError


def run_git(
    args: list[str], cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """
    Run a git command and return the CompletedProcess result.

    Raises GitCommandError if the command exits with a non-zero status.
    """
    cmd = ["git"] + args
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitCommandError(
            args=cmd,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            cwd=cwd,
        )
    return result


def is_git_repository(path: Path) -> bool:
    """Return True if the given path is a Git repository."""
    try:
        run_git(["rev-parse", "--git-dir"], cwd=path)
        return True
    except GitCommandError:
        return False


def has_origin_remote(path: Path) -> bool:
    """Return True if the repository at path has an 'origin' remote."""
    try:
        run_git(["remote", "get-url", "origin"], cwd=path)
        return True
    except GitCommandError:
        return False


def get_remote_url(path: Path) -> str:
    """Get the origin remote URL for the repository at path."""
    result = run_git(["config", "--get", "remote.origin.url"], cwd=path)
    return result.stdout.strip()


def fetch_origin(path: Path) -> None:
    """Run git fetch origin in the repository at path."""
    run_git(["fetch", "origin"], cwd=path)


def resolve_default_branch(path: Path) -> str:
    """
    Resolve the default branch from refs/remotes/origin/HEAD.
    Returns the short branch name (e.g. 'main').
    """
    result = run_git(["symbolic-ref", "refs/remotes/origin/HEAD"], cwd=path)
    ref = result.stdout.strip()
    # ref is like refs/remotes/origin/main
    parts = ref.split("/")
    if len(parts) < 4:
        raise ValueError(f"Unexpected symbolic-ref output: {ref!r}")
    return "/".join(parts[3:])


def resolve_sha(path: Path, ref: str) -> str:
    """Resolve a ref to a full commit SHA."""
    result = run_git(["rev-parse", ref], cwd=path)
    return result.stdout.strip()


def branch_exists(path: Path, branch: str) -> bool:
    """Return True if a local branch exists in the repository."""
    try:
        run_git(["rev-parse", "--verify", f"refs/heads/{branch}"], cwd=path)
        return True
    except GitCommandError:
        return False


def add_worktree(
    source: Path, worktree_path: Path, branch: str, start_point: str
) -> None:
    """Create a new worktree with a new branch at start_point."""
    run_git(
        ["worktree", "add", "-b", branch, str(worktree_path), start_point],
        cwd=source,
    )


def remove_worktree(source: Path, worktree_path: Path) -> None:
    """Remove a worktree from the source repository."""
    run_git(["worktree", "remove", "--force", str(worktree_path)], cwd=source)


def delete_branch(path: Path, branch: str) -> None:
    """Force-delete a local branch."""
    run_git(["branch", "-D", branch], cwd=path)


def clone_repo(specifier: str, target_path: Path) -> None:
    """Clone a remote specifier into target_path."""
    run_git(["clone", specifier, str(target_path)])


def checkout_new_branch(path: Path, branch: str, start_point: str) -> None:
    """Create and check out a new branch from start_point."""
    run_git(["checkout", "-b", branch, start_point], cwd=path)

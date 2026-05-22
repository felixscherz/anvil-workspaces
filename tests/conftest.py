"""Shared pytest fixtures for Anvil tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True)


def init_git_repo(path: Path, bare: bool = False) -> Path:
    """Initialize a git repository at path. Returns path."""
    path.mkdir(parents=True, exist_ok=True)
    args = ["git", "init"]
    if bare:
        args.append("--bare")
    _run(args, cwd=path)
    if not bare:
        _run(["git", "config", "user.email", "test@anvil.test"], cwd=path)
        _run(["git", "config", "user.name", "Anvil Test"], cwd=path)
    return path


def make_initial_commit(repo: Path, branch: str = "main") -> str:
    """Create an initial commit in the repo and return its SHA."""
    readme = repo / "README.md"
    readme.write_text("# Test repo\n", encoding="utf-8")
    _run(["git", "add", "README.md"], cwd=repo)
    _run(["git", "commit", "-m", "Initial commit"], cwd=repo)
    # Rename the default branch to `branch`
    try:
        _run(["git", "branch", "-M", branch], cwd=repo)
    except subprocess.CalledProcessError:
        pass
    result = _run(["git", "rev-parse", "HEAD"], cwd=repo)
    return result.stdout.strip()


def add_origin_remote(repo: Path, remote_url: str) -> None:
    """Add an 'origin' remote to the repo."""
    _run(["git", "remote", "add", "origin", remote_url], cwd=repo)


@pytest.fixture
def bare_remote(tmp_path: Path) -> Path:
    """A bare git repository simulating a remote."""
    remote = tmp_path / "remote.git"
    init_git_repo(remote, bare=True)
    # Seed it with an initial commit via a temp clone
    seed = tmp_path / "seed"
    init_git_repo(seed)
    make_initial_commit(seed, branch="main")
    add_origin_remote(seed, str(remote))
    _run(["git", "push", "origin", "main"], cwd=seed)
    _run(["git", "remote", "set-head", "origin", "main"], cwd=seed)
    return remote


@pytest.fixture
def local_repo(tmp_path: Path, bare_remote: Path) -> Path:
    """A local git repository with origin pointing to bare_remote."""
    repo = tmp_path / "local_repo"
    _run(["git", "clone", str(bare_remote), str(repo)])
    _run(["git", "config", "user.email", "test@anvil.test"], cwd=repo)
    _run(["git", "config", "user.name", "Anvil Test"], cwd=repo)
    # Ensure origin/HEAD is set
    _run(["git", "remote", "set-head", "origin", "main"], cwd=repo)
    return repo

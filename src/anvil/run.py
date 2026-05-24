"""Logic for running arbitrary commands across all repos in a workspace."""

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from anvil.manifest import read_manifest
from anvil.models import Manifest, RepoEntry


@dataclass
class RepoResult:
    """Result of running a command in one repository."""

    repo: RepoEntry
    returncode: int
    stdout: str
    stderr: str


def _run_in_repo(repo: RepoEntry, command: list[str]) -> RepoResult:
    result = subprocess.run(
        command,
        cwd=repo.repo_path,
        text=True,
        capture_output=True,
    )
    return RepoResult(
        repo=repo,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _print_repo_output(result: RepoResult, command: list[str]) -> None:
    cmd_str = " ".join(command)
    prefix = f"[{result.repo.name}]"
    print(f"{prefix} $ {cmd_str}")
    for line in result.stdout.splitlines():
        print(f"{prefix} {line}")
    for line in result.stderr.splitlines():
        print(f"{prefix} {line}", file=sys.stderr)


def run_sequential(manifest: Manifest, command: list[str]) -> int:
    """
    Run command in each repo sequentially.

    Stops on first failure and returns its exit code.
    Returns 0 if all succeed.
    """
    for repo in manifest.repos:
        result = _run_in_repo(repo, command)
        _print_repo_output(result, command)
        if result.returncode != 0:
            return result.returncode
    return 0


def run_parallel(manifest: Manifest, command: list[str]) -> int:
    """
    Run command in all repos concurrently.

    All repos run regardless of individual failures.
    Returns the highest non-zero exit code, or 0 if all succeed.
    """
    results: list[RepoResult] = []

    with ThreadPoolExecutor() as executor:
        future_to_repo = {
            executor.submit(_run_in_repo, repo, command): repo
            for repo in manifest.repos
        }
        for future in as_completed(future_to_repo):
            results.append(future.result())

    # Sort output by manifest order for deterministic display
    name_to_result = {r.repo.name: r for r in results}
    overall_rc = 0
    for repo in manifest.repos:
        result = name_to_result[repo.name]
        _print_repo_output(result, command)
        if result.returncode != 0:
            overall_rc = result.returncode

    return overall_rc


def run_command(workspace: Path, command: list[str], *, parallel: bool = False) -> int:
    """
    Run an arbitrary command across all repos in the workspace.

    Returns the combined exit code (0 = all succeeded).
    """
    manifest = read_manifest(workspace)
    if parallel:
        return run_parallel(manifest, command)
    return run_sequential(manifest, command)

"""Create workflow: orchestration and rollback."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import typer

from anvil import git
from anvil.exceptions import (
    BranchAlreadyExistsError,
    CreateFailedError,
    DefaultBranchResolutionError,
    NoOriginRemoteError,
    NotAGitRepositoryError,
    NotAnAnvilWorkspaceError,
    RepoAlreadyInWorkspaceError,
    RollbackError,
    TargetNotEmptyError,
    TargetParentMissingError,
)
from anvil.manifest import anvil_dir, now_utc_iso, read_manifest, write_manifest
from anvil.models import CreationMode, Manifest, RepoEntry, RepoSpec, SpecifierType


@dataclass
class _CreatedWorktree:
    source: Path
    worktree_path: Path
    branch: str


@dataclass
class _CreatedClone:
    clone_path: Path


def validate_target(target: Path) -> None:
    if not target.parent.exists():
        raise TargetParentMissingError(target)
    if target.exists() and any(target.iterdir()):
        raise TargetNotEmptyError(target)


def _create_worktree_repo(
    spec: RepoSpec,
    target: Path,
    branch: str,
) -> RepoEntry:
    source = Path(spec.specifier).resolve()

    if not git.is_git_repository(source):
        raise NotAGitRepositoryError(source)

    if not git.has_origin_remote(source):
        raise NoOriginRemoteError(source)

    git.fetch_origin(source)

    try:
        default_branch = git.resolve_default_branch(source)
    except Exception as e:
        raise DefaultBranchResolutionError(spec.specifier) from e

    base_sha = git.resolve_sha(source, f"origin/{default_branch}")
    remote_url = git.get_remote_url(source)

    worktree_path = target / spec.name

    if git.branch_exists(source, branch):
        raise BranchAlreadyExistsError(branch, source)

    git.add_worktree(source, worktree_path, branch, f"origin/{default_branch}")

    return RepoEntry(
        name=spec.name,
        specifier=spec.specifier,
        specifier_type=spec.specifier_type,
        repo_path=worktree_path,
        remote_url=remote_url,
        default_branch=default_branch,
        base_sha=base_sha,
        branch=branch,
        creation_mode=CreationMode.WORKTREE,
    )


def _create_clone_repo(
    spec: RepoSpec,
    target: Path,
    branch: str,
) -> RepoEntry:
    clone_path = target / spec.name
    git.clone_repo(spec.specifier, clone_path)

    remote_url = git.get_remote_url(clone_path)

    try:
        default_branch = git.resolve_default_branch(clone_path)
    except Exception:
        # Fall back to current branch
        try:
            result = git.run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=clone_path)
            default_branch = result.stdout.strip()
            if not default_branch or default_branch == "HEAD":
                raise DefaultBranchResolutionError(spec.specifier)
        except Exception as e:
            raise DefaultBranchResolutionError(spec.specifier) from e

    base_sha = git.resolve_sha(clone_path, f"origin/{default_branch}")
    git.checkout_new_branch(clone_path, branch, f"origin/{default_branch}")

    return RepoEntry(
        name=spec.name,
        specifier=spec.specifier,
        specifier_type=spec.specifier_type,
        repo_path=clone_path,
        remote_url=remote_url,
        default_branch=default_branch,
        base_sha=base_sha,
        branch=branch,
        creation_mode=CreationMode.CLONE,
    )


def _rollback(
    created: list[_CreatedWorktree | _CreatedClone],
    target: Path,
    target_was_created: bool,
) -> None:
    errors: list[str] = []
    for item in reversed(created):
        try:
            if isinstance(item, _CreatedWorktree):
                try:
                    git.remove_worktree(item.source, item.worktree_path)
                except Exception as e:
                    errors.append(
                        f"Failed to remove worktree {item.worktree_path}: {e}"
                    )
                try:
                    git.delete_branch(item.source, item.branch)
                except Exception as e:
                    errors.append(
                        f"Failed to delete branch {item.branch} in {item.source}: {e}"
                    )
            elif isinstance(item, _CreatedClone):
                try:
                    shutil.rmtree(item.clone_path, ignore_errors=True)
                except Exception as e:
                    errors.append(f"Failed to remove clone {item.clone_path}: {e}")
        except Exception as e:
            errors.append(str(e))

    # Remove .anvil dir if it's empty
    anvil = anvil_dir(target)
    if anvil.exists():
        try:
            anvil.rmdir()
        except OSError:
            pass

    # Remove target if we created it and it's now empty
    if target_was_created and target.exists():
        try:
            target.rmdir()
        except OSError:
            pass

    if errors:
        raise RollbackError("\n".join(errors))


def run_create(
    target: Path,
    specs: list[RepoSpec],
    branch: str,
) -> Manifest:
    """
    Orchestrate creation of all repositories. Returns the written manifest.
    On any failure, rolls back what was created and re-raises.
    """
    target_was_created = not target.exists()
    target.mkdir(parents=False, exist_ok=True)

    created: list[_CreatedWorktree | _CreatedClone] = []
    entries: list[RepoEntry] = []

    for spec in specs:
        try:
            if spec.specifier_type == SpecifierType.PATH:
                entry = _create_worktree_repo(spec, target, branch)
                source = Path(spec.specifier).resolve()
                created.append(
                    _CreatedWorktree(
                        source=source, worktree_path=entry.repo_path, branch=branch
                    )
                )
            else:
                entry = _create_clone_repo(spec, target, branch)
                created.append(_CreatedClone(clone_path=entry.repo_path))

            entries.append(entry)
            typer.echo(f"  + {spec.name} -> {entry.repo_path}")

        except Exception as exc:
            typer.echo(f"Error processing '{spec.specifier}': {exc}", err=True)
            typer.echo("Rolling back...", err=True)
            rollback_errors: str | None = None
            try:
                _rollback(created, target, target_was_created)
            except RollbackError as re:
                rollback_errors = re.details
            if rollback_errors:
                typer.echo(f"Rollback errors:\n{rollback_errors}", err=True)
            raise CreateFailedError(spec.specifier, len(created), exc) from exc

    manifest = Manifest(
        version=Manifest.MANIFEST_VERSION,
        workspace_root=target,
        branch_name=branch,
        created_at=now_utc_iso(),
        repos=entries,
    )
    write_manifest(manifest)
    return manifest


def run_add(
    target: Path,
    specs: list[RepoSpec],
) -> Manifest:
    """
    Add repositories to an existing Anvil workspace.
    Reads the branch name from the manifest, creates the repos, and rewrites
    the manifest with the new entries appended.
    On any failure, rolls back only the repos created in this run.
    """

    if not target.exists():
        raise NotAnAnvilWorkspaceError(target)

    manifest = read_manifest(target)
    branch = manifest.branch_name
    existing_names = {r.name for r in manifest.repos}

    # Check for collisions against both the existing manifest and the new specs
    for spec in specs:
        if spec.name in existing_names:
            raise RepoAlreadyInWorkspaceError(spec.name, target)

    created: list[_CreatedWorktree | _CreatedClone] = []
    new_entries: list[RepoEntry] = []

    for spec in specs:
        try:
            if spec.specifier_type == SpecifierType.PATH:
                entry = _create_worktree_repo(spec, target, branch)
                source = Path(spec.specifier).resolve()
                created.append(
                    _CreatedWorktree(
                        source=source, worktree_path=entry.repo_path, branch=branch
                    )
                )
            else:
                entry = _create_clone_repo(spec, target, branch)
                created.append(_CreatedClone(clone_path=entry.repo_path))

            new_entries.append(entry)
            typer.echo(f"  + {spec.name} -> {entry.repo_path}")

        except Exception as exc:
            typer.echo(f"Error processing '{spec.specifier}': {exc}", err=True)
            typer.echo("Rolling back...", err=True)
            rollback_errors: str | None = None
            try:
                # target_was_created=False: never remove the workspace itself
                _rollback(created, target, target_was_created=False)
            except RollbackError as re:
                rollback_errors = re.details
            if rollback_errors:
                typer.echo(f"Rollback errors:\n{rollback_errors}", err=True)
            raise CreateFailedError(spec.specifier, len(created), exc) from exc

    updated = Manifest(
        version=manifest.version,
        workspace_root=manifest.workspace_root,
        branch_name=manifest.branch_name,
        created_at=manifest.created_at,
        repos=list(manifest.repos) + new_entries,
    )
    write_manifest(updated)
    return updated

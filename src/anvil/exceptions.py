"""Domain-specific exceptions for Anvil."""

from __future__ import annotations

from pathlib import Path


class AnvilError(Exception):
    """Base class for all user-facing Anvil errors."""


class TargetNotEmptyError(AnvilError):
    def __init__(self, target: Path) -> None:
        super().__init__(f"Target '{target}' exists and is not empty.")
        self.target = target


class TargetParentMissingError(AnvilError):
    def __init__(self, target: Path) -> None:
        super().__init__(f"Parent directory of target '{target}' does not exist.")
        self.target = target


class EmptyBranchNameError(AnvilError):
    def __init__(self, target: Path) -> None:
        super().__init__(
            f"Could not derive a valid branch name from target path '{target}'."
        )
        self.target = target


class DuplicateRepoNameError(AnvilError):
    def __init__(self, name: str, specifiers: list[str]) -> None:
        quoted = " and ".join(f"'{s}'" for s in specifiers)
        super().__init__(
            f"Derived repository name '{name}' is duplicated by specifiers {quoted}."
        )
        self.name = name
        self.specifiers = specifiers


class NotAGitRepositoryError(AnvilError):
    def __init__(self, path: Path) -> None:
        super().__init__(f"Local path '{path}' exists but is not a Git repository.")
        self.path = path


class NoOriginRemoteError(AnvilError):
    def __init__(self, path: Path) -> None:
        super().__init__(
            f"Local repository '{path}' has no 'origin' remote. "
            "v1 requires 'origin' to resolve the default branch."
        )
        self.path = path


class DefaultBranchResolutionError(AnvilError):
    def __init__(self, specifier: str) -> None:
        super().__init__(
            f"Could not resolve default branch for repository '{specifier}'."
        )
        self.specifier = specifier


class BranchAlreadyExistsError(AnvilError):
    def __init__(self, branch: str, repo: Path) -> None:
        super().__init__(
            f"Branch '{branch}' already exists in repository '{repo}'. "
            "Anvil will not reuse or reset an existing branch."
        )
        self.branch = branch
        self.repo = repo


class ManifestNotFoundError(AnvilError):
    def __init__(self, path: Path) -> None:
        super().__init__(
            f"No Anvil manifest found at '{path}'. Is this a valid Anvil workspace?"
        )
        self.path = path


class InvalidManifestError(AnvilError):
    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"Invalid Anvil manifest at '{path}': {reason}")
        self.path = path
        self.reason = reason


class GitCommandError(AnvilError):
    """Raised when a git subprocess command fails."""

    def __init__(
        self,
        args: list[str],
        returncode: int,
        stdout: str,
        stderr: str,
        cwd: Path | None = None,
    ) -> None:
        cmd = " ".join(args)
        location = f" (cwd={cwd})" if cwd else ""
        super().__init__(
            f"Git command failed{location}: {cmd}\n"
            f"Exit code: {returncode}\n"
            f"stdout: {stdout.strip()}\n"
            f"stderr: {stderr.strip()}"
        )
        self.args_list = args
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.cwd = cwd


class CreateFailedError(AnvilError):
    def __init__(self, specifier: str, rolled_back: int, cause: Exception) -> None:
        super().__init__(
            f"Create failed while processing '{specifier}'. "
            f"Rolled back {rolled_back} created repositories."
        )
        self.specifier = specifier
        self.rolled_back = rolled_back
        self.cause = cause


class RollbackError(AnvilError):
    def __init__(self, details: str) -> None:
        super().__init__(
            f"Rollback encountered errors. The workspace may be partially present.\n{details}"
        )
        self.details = details


class EmptyRepoNameError(AnvilError):
    def __init__(self, specifier: str) -> None:
        super().__init__(
            f"Could not derive a repository name from specifier '{specifier}'."
        )
        self.specifier = specifier


class NoRepoSpecifiersError(AnvilError):
    def __init__(self) -> None:
        super().__init__("At least one repository specifier must be provided.")


class RepoAlreadyInWorkspaceError(AnvilError):
    def __init__(self, name: str, workspace: Path) -> None:
        super().__init__(
            f"Repository '{name}' already exists in workspace '{workspace}'."
        )
        self.name = name
        self.workspace = workspace


class NotAnAnvilWorkspaceError(AnvilError):
    def __init__(self, target: Path) -> None:
        super().__init__(
            f"'{target}' is not an existing Anvil workspace. Run 'anvil create' first."
        )
        self.target = target

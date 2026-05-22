"""Typed domain models for Anvil manifests and planning."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class SpecifierType(str, Enum):
    PATH = "path"
    URL = "url"


class CreationMode(str, Enum):
    WORKTREE = "worktree"
    CLONE = "clone"


@dataclass(frozen=True)
class RepoSpec:
    """Planning-time value object: a classified repository specifier."""

    specifier: str
    specifier_type: SpecifierType
    name: str  # derived directory name inside the workspace


@dataclass(frozen=True)
class RepoEntry:
    """A single repository entry in the manifest."""

    name: str
    specifier: str
    specifier_type: SpecifierType
    repo_path: Path
    remote_url: str
    default_branch: str
    base_sha: str
    branch: str
    creation_mode: CreationMode

    def to_dict(self) -> dict[object, object]:
        return {
            "name": self.name,
            "specifier": self.specifier,
            "specifierType": self.specifier_type.value,
            "repoPath": str(self.repo_path),
            "remoteUrl": self.remote_url,
            "defaultBranch": self.default_branch,
            "baseSha": self.base_sha,
            "branch": self.branch,
            "creationMode": self.creation_mode.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "RepoEntry":
        return cls(
            name=str(data["name"]),
            specifier=str(data["specifier"]),
            specifier_type=SpecifierType(data["specifierType"]),
            repo_path=Path(str(data["repoPath"])),
            remote_url=str(data["remoteUrl"]),
            default_branch=str(data["defaultBranch"]),
            base_sha=str(data["baseSha"]),
            branch=str(data["branch"]),
            creation_mode=CreationMode(data["creationMode"]),
        )


@dataclass(frozen=True)
class Manifest:
    """The workspace manifest written to <target>/.anvil/manifest.json."""

    version: int
    workspace_root: Path
    branch_name: str
    created_at: str  # ISO 8601 UTC
    repos: list[RepoEntry] = field(default_factory=list)

    MANIFEST_VERSION = 1

    def to_dict(self) -> dict[object, object]:
        return {
            "version": self.version,
            "workspaceRoot": str(self.workspace_root),
            "branchName": self.branch_name,
            "createdAt": self.created_at,
            "repos": [r.to_dict() for r in self.repos],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Manifest":
        repos_raw = data.get("repos", [])
        if not isinstance(repos_raw, list):
            repos_raw = []
        repos = [RepoEntry.from_dict(r) for r in repos_raw]  # type: ignore[arg-type]
        return cls(
            version=int(str(data["version"])),
            workspace_root=Path(str(data["workspaceRoot"])),
            branch_name=str(data["branchName"]),
            created_at=str(data["createdAt"]),
            repos=repos,
        )

"""Tests for manifest read/write/validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from anvil.exceptions import InvalidManifestError, ManifestNotFoundError
from anvil.manifest import manifest_path, read_manifest, write_manifest
from anvil.models import CreationMode, Manifest, RepoEntry, SpecifierType


def make_manifest(workspace_root: Path) -> Manifest:
    return Manifest(
        version=1,
        workspace_root=workspace_root,
        branch_name="feature-abc",
        created_at="2026-05-22T12:00:00Z",
        repos=[
            RepoEntry(
                name="myrepo",
                specifier="/some/path/myrepo",
                specifier_type=SpecifierType.PATH,
                repo_path=workspace_root / "myrepo",
                remote_url="git@github.com:org/myrepo.git",
                default_branch="main",
                base_sha="abc123",
                branch="feature-abc",
                creation_mode=CreationMode.WORKTREE,
            )
        ],
    )


class TestWriteAndReadManifest:
    def test_round_trip(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        manifest = make_manifest(workspace)
        write_manifest(manifest)

        loaded = read_manifest(workspace)
        assert loaded.version == 1
        assert loaded.branch_name == "feature-abc"
        assert len(loaded.repos) == 1
        assert loaded.repos[0].name == "myrepo"
        assert loaded.repos[0].creation_mode == CreationMode.WORKTREE

    def test_manifest_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(ManifestNotFoundError):
            read_manifest(tmp_path / "does-not-exist")

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        mp = manifest_path(workspace)
        mp.parent.mkdir(parents=True)
        mp.write_text("not json", encoding="utf-8")
        with pytest.raises(InvalidManifestError):
            read_manifest(workspace)

    def test_wrong_version_raises(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        mp = manifest_path(workspace)
        mp.parent.mkdir(parents=True)
        mp.write_text(
            json.dumps(
                {
                    "version": 99,
                    "workspaceRoot": str(workspace),
                    "branchName": "x",
                    "createdAt": "2026-01-01T00:00:00Z",
                    "repos": [],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(InvalidManifestError, match="Unsupported manifest version"):
            read_manifest(workspace)

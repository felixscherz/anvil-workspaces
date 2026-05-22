"""Manifest read/write/validation helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from anvil.exceptions import InvalidManifestError, ManifestNotFoundError
from anvil.models import Manifest

MANIFEST_DIR = ".anvil"
MANIFEST_FILENAME = "manifest.json"


def manifest_path(workspace_root: Path) -> Path:
    return workspace_root / MANIFEST_DIR / MANIFEST_FILENAME


def anvil_dir(workspace_root: Path) -> Path:
    return workspace_root / MANIFEST_DIR


def write_manifest(manifest: Manifest) -> None:
    """Write manifest to <workspace_root>/.anvil/manifest.json."""
    anvil = anvil_dir(manifest.workspace_root)
    anvil.mkdir(parents=True, exist_ok=True)
    path = manifest_path(manifest.workspace_root)
    path.write_text(json.dumps(manifest.to_dict(), indent=2) + "\n", encoding="utf-8")


def read_manifest(workspace_root: Path) -> Manifest:
    """Read and validate a manifest from the workspace root."""
    path = manifest_path(workspace_root)
    if not path.exists():
        raise ManifestNotFoundError(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise InvalidManifestError(path, f"JSON parse error: {e}") from e

    if not isinstance(raw, dict):
        raise InvalidManifestError(path, "Expected a JSON object at top level.")

    if raw.get("version") != Manifest.MANIFEST_VERSION:
        raise InvalidManifestError(
            path,
            f"Unsupported manifest version: {raw.get('version')!r}. "
            f"Expected {Manifest.MANIFEST_VERSION}.",
        )

    try:
        return Manifest.from_dict(raw)
    except (KeyError, ValueError, TypeError) as e:
        raise InvalidManifestError(path, str(e)) from e


def now_utc_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

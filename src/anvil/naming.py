"""Branch name sanitization and repository name derivation."""

from __future__ import annotations

import re
from pathlib import Path

from anvil.exceptions import EmptyBranchNameError, EmptyRepoNameError

# Characters not allowed in git branch names (simplified set)
_INVALID_BRANCH_CHARS = re.compile(r"[^a-zA-Z0-9._/-]")
_REPEATED_SEPARATORS = re.compile(r"[-]{2,}")


def infer_branch_name(target: Path) -> str:
    """Derive and sanitize a branch name from the target directory basename."""
    raw = Path(target).resolve().name
    # Lowercase
    name = raw.lower()
    # Replace spaces and invalid git branch characters with '-'
    name = _INVALID_BRANCH_CHARS.sub("-", name)
    # Collapse repeated separators
    name = _REPEATED_SEPARATORS.sub("-", name)
    # Trim leading/trailing separators
    name = name.strip("-")

    if not name:
        raise EmptyBranchNameError(target)

    return name


def derive_repo_name_from_path(path: Path) -> str:
    """Derive a repository directory name from a local filesystem path."""
    name = Path(path).resolve().name
    if not name:
        raise EmptyRepoNameError(str(path))
    return name


def derive_repo_name_from_specifier(specifier: str) -> str:
    """Derive a repository directory name from a clone specifier (URL or SCP)."""
    from urllib.parse import urlparse

    # Strip trailing slashes
    s = specifier.rstrip("/")

    # Try to parse as a URL with a known scheme
    parsed = urlparse(s)
    if parsed.scheme in ("https", "http", "ssh", "git", "ftp"):
        # Use the last path segment from the URL path
        segment = parsed.path.rstrip("/").split("/")[-1]
    elif ":" in s and not s.startswith("/"):
        # SCP-like: git@github.com:org/repo.git
        # Everything after the colon is the path
        path_part = s.split(":", 1)[1]
        segment = path_part.rstrip("/").split("/")[-1]
    else:
        # Fallback: take the last path segment
        segment = s.split("/")[-1]

    # Strip trailing .git
    if segment.endswith(".git"):
        segment = segment[:-4]
    segment = segment.strip()
    if not segment:
        raise EmptyRepoNameError(specifier)
    return segment

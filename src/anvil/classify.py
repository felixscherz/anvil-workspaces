"""Classifier for local-path vs clone specifier inputs."""

from __future__ import annotations

from pathlib import Path

from anvil.exceptions import DuplicateRepoNameError
from anvil.models import RepoSpec, SpecifierType
from anvil.naming import derive_repo_name_from_path, derive_repo_name_from_specifier


def classify_specifier(specifier: str) -> RepoSpec:
    """
    Classify a repository specifier as a local path or a clone URL.

    Order:
    1. If the specifier resolves to an existing local path, treat as local.
    2. Otherwise, treat as a clone specifier.
    """
    candidate = Path(specifier)
    if candidate.exists():
        name = derive_repo_name_from_path(candidate)
        return RepoSpec(
            specifier=specifier,
            specifier_type=SpecifierType.PATH,
            name=name,
        )
    else:
        name = derive_repo_name_from_specifier(specifier)
        return RepoSpec(
            specifier=specifier,
            specifier_type=SpecifierType.URL,
            name=name,
        )


def classify_all(specifiers: list[str]) -> list[RepoSpec]:
    """
    Classify all specifiers and validate for duplicate derived names.
    Raises DuplicateRepoNameError if two specifiers share the same derived name.
    """
    specs: list[RepoSpec] = []
    seen: dict[str, str] = {}

    for s in specifiers:
        spec = classify_specifier(s)
        if spec.name in seen:
            raise DuplicateRepoNameError(spec.name, [seen[spec.name], s])
        seen[spec.name] = s
        specs.append(spec)

    return specs

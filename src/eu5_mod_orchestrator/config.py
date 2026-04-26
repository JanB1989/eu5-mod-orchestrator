from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when a mod orchestration config is invalid."""


@dataclass(frozen=True)
class OrchestratorConfig:
    config_path: Path
    project_root: Path
    name: str
    mod_root: Path
    artifact_dir: Path
    parser_artifact_dir: Path
    reports_dir: Path
    accepted_blueprints_dir: Path
    generated_blueprints_dir: Path
    load_order_path: Path | None
    profile: str
    dependencies: dict[str, Path]


def load_project_config(path: str | Path) -> OrchestratorConfig:
    config_path = Path(path).resolve()
    with config_path.open("rb") as stream:
        raw = tomllib.load(stream)
    root = config_path.parent

    project = _mapping(raw.get("project"), "project")
    artifacts = _mapping(raw.get("artifacts", {}), "artifacts")
    parser = _mapping(raw.get("parser", {}), "parser")
    deps = _mapping(raw.get("dependencies", {}), "dependencies")

    name = _string(project, "name", "project")
    mod_root = _path(root, _string(project, "mod_root", "project"))
    artifact_dir = _path(root, str(artifacts.get("root", "artifacts")))
    accepted = _path(root, str(artifacts.get("accepted_blueprints", "blueprints/accepted")))
    generated = _path(root, str(artifacts.get("generated_blueprints", "blueprints/generated")))
    reports = _path(root, str(artifacts.get("reports", "reports")))
    parser_artifacts = _path(root, str(artifacts.get("parser", "artifacts/parser")))

    load_order_raw = parser.get("load_order")
    load_order_path = None if load_order_raw in (None, "") else _path(root, str(load_order_raw))
    profile = str(parser.get("profile", "merged_default"))

    return OrchestratorConfig(
        config_path=config_path,
        project_root=root,
        name=name,
        mod_root=mod_root,
        artifact_dir=artifact_dir,
        parser_artifact_dir=parser_artifacts,
        reports_dir=reports,
        accepted_blueprints_dir=accepted,
        generated_blueprints_dir=generated,
        load_order_path=load_order_path,
        profile=profile,
        dependencies={key: _path(root, str(value)) for key, value in deps.items()},
    )


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be a TOML table.")
    return value


def _string(mapping: dict[str, Any], key: str, section: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{section}.{key} must be a non-empty string.")
    return value


def _path(root: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (root / path).resolve()

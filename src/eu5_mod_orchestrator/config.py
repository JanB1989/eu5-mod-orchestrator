from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when a mod orchestration config is invalid."""


@dataclass(frozen=True)
class BuildingOutputLayout:
    prefix: str
    building_types: str
    production_methods: str
    prices: str
    advances: str
    localization: str
    icons: str


@dataclass(frozen=True)
class LabelingConfig:
    enabled: bool
    config_path: Path
    modifier_prefix: str
    generated_label: str
    managed_write_mode: str


@dataclass(frozen=True)
class PopulationCapacityConfig:
    enabled: bool
    config_path: Path
    generated_label: str
    managed_write_mode: str


@dataclass(frozen=True)
class OrchestratorConfig:
    config_path: Path
    project_root: Path
    name: str
    mod_root: Path
    deploy_target: Path | None
    artifact_dir: Path
    data_artifact_dir: Path
    building_artifact_dir: Path
    savegame_artifact_dir: Path
    graph_dir: Path
    parser_artifact_dir: Path
    reports_dir: Path
    accepted_blueprints_dir: Path
    generated_blueprints_dir: Path
    blueprint_manifest_path: Path | None
    building_clean_paths: tuple[str, ...]
    load_order_path: Path | None
    profile: str
    building_outputs: BuildingOutputLayout
    labeling: LabelingConfig | None
    population_capacity: PopulationCapacityConfig | None
    dependencies: dict[str, Path]


def load_project_config(path: str | Path) -> OrchestratorConfig:
    config_path = Path(path).resolve()
    with config_path.open("rb") as stream:
        raw = tomllib.load(stream)
    raw = _merge(raw, _load_local_config(config_path))
    root = config_path.parent

    project = _mapping(raw.get("project"), "project")
    deploy = _mapping(raw.get("deploy", {}), "deploy")
    artifacts = _mapping(raw.get("artifacts", {}), "artifacts")
    parser = _mapping(raw.get("parser", {}), "parser")
    building_outputs = _mapping(raw.get("building_outputs", {}), "building_outputs")
    building_blueprints = _mapping(raw.get("building_blueprints", {}), "building_blueprints")
    labeling_raw = raw.get("labeling")
    population_capacity_raw = raw.get("population_capacity")
    deps = _mapping(raw.get("dependencies", {}), "dependencies")

    name = _string(project, "name", "project")
    mod_root = _path(root, _string(project, "mod_root", "project"))
    deploy_target_raw = deploy.get("target")
    deploy_target = None
    if deploy_target_raw not in (None, ""):
        if not isinstance(deploy_target_raw, str):
            raise ConfigError("deploy.target must be a string.")
        deploy_target = _path(root, deploy_target_raw)
    artifact_dir = _path(root, str(artifacts.get("root", "artifacts")))
    accepted = _path(root, str(artifacts.get("accepted_blueprints", "blueprints/accepted")))
    generated = _path(root, str(artifacts.get("generated_blueprints", "blueprints/generated")))
    reports = _path(root, str(artifacts.get("reports", "reports")))
    data_artifacts = _path(root, str(artifacts.get("data", "artifacts/data")))
    building_artifacts = _path(
        root,
        str(artifacts.get("buildings", artifacts.get("parser", "artifacts/data/buildings"))),
    )
    savegame_artifacts = _path(root, str(artifacts.get("savegame", "artifacts/data/savegame")))
    graphs = _path(root, str(artifacts.get("graphs", "graphs")))

    load_order_raw = parser.get("load_order")
    load_order_path = None if load_order_raw in (None, "") else _path(root, str(load_order_raw))
    profile = str(parser.get("profile", "merged_default"))
    output_prefix = str(building_outputs.get("prefix", ""))
    layout = BuildingOutputLayout(
        prefix=output_prefix,
        building_types=str(building_outputs.get("building_types", "in_game/common/building_types/{tag}.txt")),
        production_methods=str(
            building_outputs.get("production_methods", "in_game/common/production_methods/{tag}.txt")
        ),
        prices=str(building_outputs.get("prices", "in_game/common/prices/{tag}.txt")),
        advances=str(building_outputs.get("advances", "in_game/common/advances/{tag}.txt")),
        localization=str(
            building_outputs.get("localization", "main_menu/localization/english/{tag}_l_english.yml")
        ),
        icons=str(building_outputs.get("icons", "in_game/gfx/interface/icons/buildings")),
    )
    manifest_raw = building_blueprints.get("manifest")
    blueprint_manifest_path = None if manifest_raw in (None, "") else _path(root, str(manifest_raw))
    clean_paths = building_blueprints.get("clean_paths", [])
    if not isinstance(clean_paths, list) or not all(isinstance(item, str) for item in clean_paths):
        raise ConfigError("building_blueprints.clean_paths must be a list of strings.")
    labeling = _labeling_config(root, labeling_raw)
    population_capacity = _population_capacity_config(root, population_capacity_raw)

    return OrchestratorConfig(
        config_path=config_path,
        project_root=root,
        name=name,
        mod_root=mod_root,
        deploy_target=deploy_target,
        artifact_dir=artifact_dir,
        data_artifact_dir=data_artifacts,
        building_artifact_dir=building_artifacts,
        savegame_artifact_dir=savegame_artifacts,
        graph_dir=graphs,
        parser_artifact_dir=building_artifacts,
        reports_dir=reports,
        accepted_blueprints_dir=accepted,
        generated_blueprints_dir=generated,
        blueprint_manifest_path=blueprint_manifest_path,
        building_clean_paths=tuple(clean_paths),
        load_order_path=load_order_path,
        profile=profile,
        building_outputs=layout,
        labeling=labeling,
        population_capacity=population_capacity,
        dependencies={key: _path(root, str(value)) for key, value in deps.items()},
    )


def _labeling_config(root: Path, value: Any) -> LabelingConfig | None:
    if value is None:
        return None
    raw = _mapping(value, "labeling")
    enabled = _bool(raw.get("enabled", True))
    config_raw = raw.get("config")
    if not isinstance(config_raw, str) or not config_raw.strip():
        raise ConfigError("labeling.config must be a non-empty string.")
    managed_write_mode = str(raw.get("managed_write_mode", "mod_root")).strip() or "mod_root"
    if managed_write_mode not in {"mod_root", "template_copy"}:
        raise ConfigError("labeling.managed_write_mode must be 'mod_root' or 'template_copy'.")
    return LabelingConfig(
        enabled=enabled,
        config_path=_path(root, config_raw),
        modifier_prefix=str(raw.get("modifier_prefix", "pp")).strip() or "pp",
        generated_label=str(raw.get("generated_label", "Prosper or Perish")).strip()
        or "Prosper or Perish",
        managed_write_mode=managed_write_mode,
    )


def _population_capacity_config(root: Path, value: Any) -> PopulationCapacityConfig | None:
    if value is None:
        return None
    raw = _mapping(value, "population_capacity")
    enabled = _bool(raw.get("enabled", True))
    config_raw = raw.get("config")
    if not isinstance(config_raw, str) or not config_raw.strip():
        raise ConfigError("population_capacity.config must be a non-empty string.")
    managed_write_mode = str(raw.get("managed_write_mode", "mod_root")).strip() or "mod_root"
    if managed_write_mode != "mod_root":
        raise ConfigError("population_capacity.managed_write_mode must be 'mod_root'.")
    return PopulationCapacityConfig(
        enabled=enabled,
        config_path=_path(root, config_raw),
        generated_label=str(raw.get("generated_label", "Prosper or Perish")).strip()
        or "Prosper or Perish",
        managed_write_mode=managed_write_mode,
    )


def _load_local_config(config_path: Path) -> dict[str, Any]:
    local_path = config_path.with_name(f"{config_path.stem}.local{config_path.suffix}")
    if not local_path.exists():
        return {}
    with local_path.open("rb") as stream:
        return tomllib.load(stream)


def _merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be a TOML table.")
    return value


def _string(mapping: dict[str, Any], key: str, section: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{section}.{key} must be a non-empty string.")
    return value


def _bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _path(root: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (root / path).resolve()

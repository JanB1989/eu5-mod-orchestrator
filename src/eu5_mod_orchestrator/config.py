from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
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
class ModifierCategoryEvaluationConfig:
    modifiers: tuple[str, ...]

    def to_pipeline_config(self) -> dict[str, Any]:
        return {
            "modifiers": list(self.modifiers),
        }


@dataclass(frozen=True)
class BlueprintEvaluationConfig:
    raw_input_efficiency_per_good: float
    profit_percent_min: float
    profit_percent_max: float
    base_output_per_1k_min: float
    base_output_per_1k_max: float
    throughput_gold_per_1k: dict[str, float]
    age_throughput_growth: float
    throughput_tolerance: float
    amortization_months_min: float | None
    amortization_months_max: float | None
    employment_size_constants: dict[str, float]
    modifier_categories: dict[str, ModifierCategoryEvaluationConfig]
    # good -> balance price used instead of the parsed default price (e.g. goods that sit at their price floor)
    price_overrides: dict[str, float] = field(default_factory=dict)
    # goods a base method may pay and still be judged as a base method (base output band, no margin/throughput rules)
    base_method_input_goods: tuple[str, ...] = ()

    @property
    def roi_cycles_max(self) -> float | None:
        return self.amortization_months_max

    def to_pipeline_config(self) -> dict[str, Any]:
        return {
            "raw_input_efficiency_per_good": self.raw_input_efficiency_per_good,
            "profit_percent_min": self.profit_percent_min,
            "profit_percent_max": self.profit_percent_max,
            "base_output_per_1k_min": self.base_output_per_1k_min,
            "base_output_per_1k_max": self.base_output_per_1k_max,
            "throughput_gold_per_1k": dict(self.throughput_gold_per_1k),
            "age_throughput_growth": self.age_throughput_growth,
            "throughput_tolerance": self.throughput_tolerance,
            "amortization_months_min": self.amortization_months_min,
            "amortization_months_max": self.amortization_months_max,
            "roi_cycles_max": self.amortization_months_max,
            "employment_size_constants": dict(self.employment_size_constants),
            "modifier_categories": {
                category: category_config.to_pipeline_config()
                for category, category_config in self.modifier_categories.items()
            },
            "base_method_input_goods": list(self.base_method_input_goods),
        }


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
    blueprint_evaluation: BlueprintEvaluationConfig
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
    blueprint_evaluation_raw = raw.get("blueprint_evaluation")
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
    blueprint_evaluation = _blueprint_evaluation_config(blueprint_evaluation_raw)

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
        blueprint_evaluation=blueprint_evaluation,
        dependencies={key: _path(root, str(value)) for key, value in deps.items()},
    )


def _blueprint_evaluation_config(value: Any) -> BlueprintEvaluationConfig:
    raw = {} if value is None else _mapping(value, "blueprint_evaluation")
    throughput_defaults = {"peasants": 1.0, "laborers": 1.5, "labourers": 1.5, "burghers": 2.5}
    throughput_raw = _mapping(raw.get("throughput_gold_per_1k", {}), "blueprint_evaluation.throughput_gold_per_1k")
    throughput = dict(throughput_defaults)
    throughput.update(
        {
            str(key): _float(value, f"blueprint_evaluation.throughput_gold_per_1k.{key}")
            for key, value in throughput_raw.items()
        }
    )
    constants = {
        str(key): _float(value, f"blueprint_evaluation.employment_size_constants.{key}")
        for key, value in _mapping(
            raw.get("employment_size_constants", {}),
            "blueprint_evaluation.employment_size_constants",
        ).items()
    }
    modifier_categories = _modifier_category_evaluation_configs(raw.get("modifier_categories", {}))
    price_overrides = {
        str(key): _float(value, f"blueprint_evaluation.price_overrides.{key}")
        for key, value in _mapping(raw.get("price_overrides", {}), "blueprint_evaluation.price_overrides").items()
    }
    return BlueprintEvaluationConfig(
        raw_input_efficiency_per_good=_optional_float(raw, "raw_input_efficiency_per_good", 0.05),
        profit_percent_min=_optional_float(raw, "profit_percent_min", -0.30),
        profit_percent_max=_optional_float(raw, "profit_percent_max", 0.30),
        base_output_per_1k_min=_optional_float(raw, "base_output_per_1k_min", 0.07),
        base_output_per_1k_max=_optional_float(raw, "base_output_per_1k_max", 0.15),
        throughput_gold_per_1k=throughput,
        age_throughput_growth=_optional_float(raw, "age_throughput_growth", 0.15),
        throughput_tolerance=_optional_float(raw, "throughput_tolerance", 0.30),
        amortization_months_min=_optional_alias_float(
            raw,
            canonical_key="amortization_months_min",
            legacy_key="",
            default=None,
        ),
        amortization_months_max=_optional_alias_float(
            raw,
            canonical_key="amortization_months_max",
            legacy_key="roi_cycles_max",
            default=None,
        ),
        employment_size_constants=constants,
        modifier_categories=modifier_categories,
        price_overrides=price_overrides,
        base_method_input_goods=_modifier_names(
            raw.get("base_method_input_goods", []), "blueprint_evaluation.base_method_input_goods"
        ),
    )


def _modifier_category_evaluation_configs(value: Any) -> dict[str, ModifierCategoryEvaluationConfig]:
    raw_categories = _mapping(value, "blueprint_evaluation.modifier_categories")
    categories: dict[str, ModifierCategoryEvaluationConfig] = {}
    for category, raw_category in raw_categories.items():
        category_name = str(category)
        category_data = _mapping(raw_category, f"blueprint_evaluation.modifier_categories.{category_name}")
        modifiers = _modifier_names(
            category_data.get("modifiers", []),
            f"blueprint_evaluation.modifier_categories.{category_name}.modifiers",
        )
        categories[category_name] = ModifierCategoryEvaluationConfig(
            modifiers=modifiers,
        )
    return categories


def _modifier_names(value: Any, name: str) -> tuple[str, ...]:
    if isinstance(value, list | tuple):
        result = tuple(item for item in value if isinstance(item, str) and item.strip())
        if len(result) != len(value):
            raise ConfigError(f"{name} must be a list of non-empty strings.")
        return result
    if isinstance(value, dict):
        return tuple(str(key) for key in value)
    raise ConfigError(f"{name} must be a list of modifier names.")


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


def _float(value: Any, name: str) -> float:
    if not isinstance(value, int | float):
        raise ConfigError(f"{name} must be a number.")
    return float(value)


def _optional_float(raw: dict[str, Any], key: str, default: float) -> float:
    return default if key not in raw else _float(raw[key], f"blueprint_evaluation.{key}")


def _optional_alias_float(
    raw: dict[str, Any],
    *,
    canonical_key: str,
    legacy_key: str,
    default: float | None,
) -> float | None:
    if canonical_key in raw:
        return _float(raw[canonical_key], f"blueprint_evaluation.{canonical_key}")
    if legacy_key and legacy_key in raw:
        return _float(raw[legacy_key], f"blueprint_evaluation.{legacy_key}")
    return default


def _path(root: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute() or _is_windows_absolute_path(raw):
        return path
    return (root / path).resolve()


def _is_windows_absolute_path(raw: str) -> bool:
    return len(raw) >= 3 and raw[0].isalpha() and raw[1] == ":" and raw[2] in {"/", "\\"}

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from eu5_mod_orchestrator.adapters.building_pipeline import (
    MANAGED_BLOCK_START,
    building_text_output_dirs,
    evaluate_building_blueprint,
    evaluate_building_blueprint_data,
    plan_building_text_outputs,
    render_building_blueprint,
)
from eu5_mod_orchestrator.adapters.labeling_pipeline import run_labeling_pipeline
from eu5_mod_orchestrator.adapters.parser import (
    compare_mod_building_state,
    export_parser_facts,
    export_savegame,
    load_balance_prices,
    validate_generated_mod,
)
from eu5_mod_orchestrator.adapters.population_capacity import (
    run_population_capacity_analyze,
    run_population_capacity_effects,
    run_population_capacity_extract,
    run_population_capacity_extract_effects,
    run_population_capacity_preview_start,
    run_population_capacity_render,
)
from eu5_mod_orchestrator.artifacts import ensure_artifact_dirs
from eu5_mod_orchestrator.blueprints import manifest_blueprint_files, validate_blueprint_file
from eu5_mod_orchestrator.config import OrchestratorConfig
from eu5_mod_orchestrator.deploy import deploy as deploy_mod


def inspect_project(config: OrchestratorConfig) -> str:
    lines = [
        f"project: {config.name}",
        f"root: {config.project_root}",
        f"mod_root: {config.mod_root}",
        f"deploy_target: {config.deploy_target}",
        f"profile: {config.profile}",
        f"accepted_blueprints: {config.accepted_blueprints_dir}",
        f"generated_blueprints: {config.generated_blueprints_dir}",
        f"blueprint_manifest: {config.blueprint_manifest_path}",
        f"building_data: {config.building_artifact_dir}",
        f"savegame_data: {config.savegame_artifact_dir}",
        f"graphs: {config.graph_dir}",
    ]
    if config.labeling is not None:
        lines.extend(
            [
                f"labeling_enabled: {config.labeling.enabled}",
                f"labeling_config: {config.labeling.config_path}",
                f"labeling_write_mode: {config.labeling.managed_write_mode}",
            ]
        )
    if config.population_capacity is not None:
        lines.extend(
            [
                f"population_capacity_enabled: {config.population_capacity.enabled}",
                f"population_capacity_config: {config.population_capacity.config_path}",
                f"population_capacity_write_mode: {config.population_capacity.managed_write_mode}",
            ]
        )
    if config.dependencies:
        lines.append("dependencies:")
        lines.extend(f"  {name}: {path}" for name, path in sorted(config.dependencies.items()))
    return "\n".join(lines)


def analyze(config: OrchestratorConfig) -> str:
    ensure_artifact_dirs(config)
    try:
        return export_parser_facts(
            config.building_artifact_dir,
            config.graph_dir,
            profile=config.profile,
            load_order_path=config.load_order_path,
        )
    except ModuleNotFoundError as exc:
        return f"parser package is not installed in this environment: {exc.name}"


def savegame(
    config: OrchestratorConfig,
    *,
    save_path: Path | None = None,
    save_dir: Path | None = None,
    force_rakaly: bool = False,
) -> str:
    ensure_artifact_dirs(config)
    try:
        return export_savegame(
            config.savegame_artifact_dir,
            config.graph_dir,
            profile=config.profile,
            load_order_path=config.load_order_path,
            save_path=save_path,
            save_dir=save_dir,
            force_rakaly=force_rakaly,
        )
    except ModuleNotFoundError as exc:
        return f"parser package is not installed in this environment: {exc.name}"


def label(
    config: OrchestratorConfig,
    *,
    goods: str | None = None,
    scale: str | None = None,
    dry_run: bool = False,
) -> str:
    try:
        return run_labeling_pipeline(config, goods=goods, scale=scale, dry_run=dry_run)
    except ModuleNotFoundError as exc:
        return f"labeling pipeline package is not installed in this environment: {exc.name}"


def population_capacity_analyze(config: OrchestratorConfig) -> str:
    try:
        return run_population_capacity_analyze(config)
    except ModuleNotFoundError as exc:
        return f"population capacity pipeline package is not installed in this environment: {exc.name}"


def population_capacity_effects(config: OrchestratorConfig) -> str:
    try:
        return run_population_capacity_effects(config)
    except ModuleNotFoundError as exc:
        return f"population capacity pipeline package is not installed in this environment: {exc.name}"


def population_capacity_preview_start(
    config: OrchestratorConfig,
    *,
    group_by: str | None = None,
    include_no_raw_material: bool = False,
) -> str:
    try:
        return run_population_capacity_preview_start(
            config,
            group_by=group_by,
            include_no_raw_material=include_no_raw_material,
        )
    except ModuleNotFoundError as exc:
        return f"population capacity pipeline package is not installed in this environment: {exc.name}"


def population_capacity_render(
    config: OrchestratorConfig,
    *,
    dry_run: bool = False,
) -> str:
    try:
        return run_population_capacity_render(config, dry_run=dry_run)
    except ModuleNotFoundError as exc:
        return f"population capacity pipeline package is not installed in this environment: {exc.name}"


def population_capacity_extract(
    config: OrchestratorConfig,
    *,
    paths: list[Path],
    dry_run: bool = False,
) -> str:
    try:
        return run_population_capacity_extract(config, paths=paths, dry_run=dry_run)
    except ModuleNotFoundError as exc:
        return f"population capacity pipeline package is not installed in this environment: {exc.name}"


def population_capacity_extract_effects(
    config: OrchestratorConfig,
    *,
    paths: list[Path],
    dry_run: bool = False,
) -> str:
    try:
        return run_population_capacity_extract_effects(config, paths=paths, dry_run=dry_run)
    except ModuleNotFoundError as exc:
        return f"population capacity pipeline package is not installed in this environment: {exc.name}"


def render(
    config: OrchestratorConfig,
    *,
    dry_run: bool = False,
    overwrite: bool = False,
    refresh_assets: bool = False,
) -> str:
    ensure_artifact_dirs(config)
    blueprints = _blueprint_files(config)
    if not blueprints:
        return f"no accepted blueprints found in {config.accepted_blueprints_dir}"

    return _render_blueprints(config, blueprints, dry_run=dry_run, overwrite=overwrite, refresh_assets=refresh_assets)


def list_blueprints(config: OrchestratorConfig) -> str:
    blueprints = _blueprint_files(config)
    if not blueprints:
        return f"no accepted blueprints found in {config.accepted_blueprints_dir}"
    summaries: list[str] = []
    for blueprint in blueprints:
        raw = validate_blueprint_file(blueprint)
        building = raw["building"]
        slots = building.get("production_method_slots", [])
        slot_count = len(slots) if isinstance(slots, list) else 0
        advancements = raw.get("advancements") or []
        production_methods = raw.get("production_methods") or []
        prices = raw.get("prices") or ([] if "price" not in raw else [raw["price"]])
        summaries.append(
            f"{blueprint.relative_to(config.accepted_blueprints_dir)}: "
            f"{str(building.get('mode', 'CREATE')).upper()} {building['key']} "
            f"(slots={slot_count}, global_pms={len(production_methods)}, "
            f"prices={len(prices)}, advancements={len(advancements)})"
        )
    return "\n\n".join(summaries)


def evaluate_blueprints(
    config: OrchestratorConfig,
    *,
    output_format: str = "text",
    building: str | None = None,
) -> str:
    ensure_artifact_dirs(config)
    blueprints = _blueprint_files(config)
    if not blueprints:
        return f"no accepted blueprints found in {config.accepted_blueprints_dir}"
    if building is not None:
        blueprints = _filter_blueprints(blueprints, building)
        if not blueprints:
            return f"no accepted blueprints matched {building!r}"
    try:
        price_by_good = load_balance_prices(
            profile=config.profile,
            load_order_path=config.load_order_path,
        )
    except ModuleNotFoundError as exc:
        return f"parser package is not installed in this environment: {exc.name}"

    summaries: list[str] = []
    evaluations = []
    for blueprint in blueprints:
        validate_blueprint_file(blueprint)
        try:
            if output_format == "json":
                from eu5_building_pipeline.evaluation import evaluation_to_dict

                evaluations.append(
                    evaluation_to_dict(
                        evaluate_building_blueprint_data(
                            blueprint,
                            config,
                            price_by_good=price_by_good,
                        )
                    )
                )
            else:
                summaries.append(
                    evaluate_building_blueprint(
                        blueprint,
                        config,
                        price_by_good=price_by_good,
                    )
                )
        except ModuleNotFoundError as exc:
            summaries.append(f"building pipeline package is not installed: {exc.name}")
    if output_format == "json":
        return json.dumps(evaluations, indent=2, sort_keys=True)
    return "\n\n".join(summaries)


def validate(config: OrchestratorConfig) -> str:
    ensure_artifact_dirs(config)
    errors = []
    for blueprint in _blueprint_files(config):
        validate_blueprint_file(blueprint)

    try:
        errors.extend(
            validate_generated_mod(profile=config.profile, load_order_path=config.load_order_path)
        )
    except ModuleNotFoundError as exc:
        return f"parser package is not installed in this environment: {exc.name}"

    if errors:
        return "validation failed:\n" + "\n".join(f"- {error}" for error in errors)
    return "validation passed"


def parity(config: OrchestratorConfig, *, mod_id: str = "constructor") -> str:
    if config.load_order_path is None:
        return "parity failed:\n- parser.load_order is required"
    blueprints = _blueprint_files(config)
    if not blueprints:
        return f"no accepted blueprints found in {config.accepted_blueprints_dir}"
    with tempfile.TemporaryDirectory(prefix="eu5-blueprint-parity-") as temp_dir:
        candidate_root = Path(temp_dir) / config.mod_root.name
        shutil.copytree(config.mod_root, candidate_root)
        _clean_building_paths(candidate_root, config.building_clean_paths)
        _render_blueprints(
            config,
            blueprints,
            dry_run=False,
            overwrite=True,
            refresh_assets=True,
            mod_root=candidate_root,
        )
        errors = compare_mod_building_state(
            profile=config.profile,
            load_order_path=config.load_order_path,
            mod_id=mod_id,
            reference_mod_root=config.mod_root,
            candidate_mod_root=candidate_root,
        )
    if errors:
        return "parity failed:\n" + "\n".join(f"- {error}" for error in errors)
    return "parity passed"


def deploy(config: OrchestratorConfig, *, dry_run: bool = False, clean: bool = False) -> str:
    return deploy_mod(config, dry_run=dry_run, clean=clean).summary()


def build(
    config: OrchestratorConfig,
    *,
    dry_run: bool = False,
    overwrite: bool = False,
    refresh_assets: bool = False,
) -> str:
    return "\n\n".join(
        [
            analyze(config),
            label(config, dry_run=dry_run),
            evaluate_blueprints(config),
            render(config, dry_run=dry_run, overwrite=overwrite, refresh_assets=refresh_assets),
            population_capacity_render(config, dry_run=dry_run),
            validate(config),
        ]
    )


def _blueprint_files(config: OrchestratorConfig) -> list[Path]:
    return manifest_blueprint_files(config.accepted_blueprints_dir, config.blueprint_manifest_path)


def _filter_blueprints(blueprints: list[Path], building: str) -> list[Path]:
    matches: list[Path] = []
    for blueprint in blueprints:
        raw = validate_blueprint_file(blueprint)
        raw_building = raw["building"]
        candidates = {blueprint.stem, str(raw.get("tag", "")), str(raw_building.get("key", ""))}
        if building in candidates:
            matches.append(blueprint)
    return matches


def _render_blueprints(
    config: OrchestratorConfig,
    blueprints: list[Path],
    *,
    dry_run: bool,
    overwrite: bool,
    refresh_assets: bool,
    mod_root: Path | None = None,
) -> str:
    summaries: list[str] = []
    summaries.extend(_clean_stale_building_outputs(config, blueprints, dry_run=dry_run, mod_root=mod_root))
    for blueprint in blueprints:
        validate_blueprint_file(blueprint)
        summaries.append(f"blueprint: {blueprint.name}")
        try:
            summaries.append(
                render_building_blueprint(
                    blueprint,
                    config,
                    dry_run=dry_run,
                    overwrite=overwrite,
                    refresh_assets=refresh_assets,
                    mod_root=mod_root,
                )
            )
        except ModuleNotFoundError as exc:
            summaries.append(f"building pipeline package is not installed: {exc.name}")
    return "\n\n".join(summaries)


def _clean_stale_building_outputs(
    config: OrchestratorConfig,
    blueprints: list[Path],
    *,
    dry_run: bool,
    mod_root: Path | None = None,
) -> list[str]:
    target_root = config.mod_root if mod_root is None else mod_root
    expected_paths: set[Path] = set()
    for blueprint in blueprints:
        expected_paths.update(plan_building_text_outputs(blueprint, config, mod_root=target_root))

    stale_paths: list[Path] = []
    for output_dir in building_text_output_dirs(config, mod_root=target_root):
        if not output_dir.exists():
            continue
        for path in output_dir.iterdir():
            if not path.is_file() or path in expected_paths:
                continue
            if _is_managed_building_output(path):
                stale_paths.append(path)

    if not stale_paths:
        return []

    stale_paths.sort()
    if not dry_run:
        for path in stale_paths:
            path.unlink()

    heading = "stale managed building output cleanup complete."
    if dry_run:
        heading = "stale managed building output cleanup dry run complete."
    lines = [heading, "Planned deletes:"]
    lines.extend(f"  {path}" for path in stale_paths)
    return ["\n".join(lines)]


def _is_managed_building_output(path: Path) -> bool:
    try:
        return MANAGED_BLOCK_START in path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return False


def _clean_building_paths(mod_root: Path, paths: tuple[str, ...]) -> None:
    for raw_path in paths:
        target = mod_root / raw_path
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()

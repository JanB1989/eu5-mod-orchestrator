from __future__ import annotations

from eu5_mod_orchestrator.adapters.building_pipeline import render_building_blueprint
from eu5_mod_orchestrator.adapters.parser import export_parser_facts, validate_generated_mod
from eu5_mod_orchestrator.artifacts import ensure_artifact_dirs
from eu5_mod_orchestrator.blueprints import accepted_blueprint_files, validate_blueprint_file
from eu5_mod_orchestrator.config import OrchestratorConfig


def inspect_project(config: OrchestratorConfig) -> str:
    lines = [
        f"project: {config.name}",
        f"root: {config.project_root}",
        f"mod_root: {config.mod_root}",
        f"profile: {config.profile}",
        f"accepted_blueprints: {config.accepted_blueprints_dir}",
        f"generated_blueprints: {config.generated_blueprints_dir}",
        f"parser_artifacts: {config.parser_artifact_dir}",
    ]
    if config.dependencies:
        lines.append("dependencies:")
        lines.extend(f"  {name}: {path}" for name, path in sorted(config.dependencies.items()))
    return "\n".join(lines)


def analyze(config: OrchestratorConfig) -> str:
    ensure_artifact_dirs(config)
    try:
        return export_parser_facts(
            config.parser_artifact_dir,
            profile=config.profile,
            load_order_path=config.load_order_path,
        )
    except ModuleNotFoundError as exc:
        return f"parser package is not installed in this environment: {exc.name}"


def render(config: OrchestratorConfig, *, dry_run: bool = False, overwrite: bool = False) -> str:
    ensure_artifact_dirs(config)
    blueprints = accepted_blueprint_files(config.accepted_blueprints_dir)
    if not blueprints:
        return f"no accepted blueprints found in {config.accepted_blueprints_dir}"

    summaries: list[str] = []
    for blueprint in blueprints:
        validate_blueprint_file(blueprint)
        summaries.append(f"blueprint: {blueprint.name}")
        try:
            summaries.append(
                render_building_blueprint(
                    blueprint,
                    config.mod_root,
                    dry_run=dry_run,
                    overwrite=overwrite,
                )
            )
        except ModuleNotFoundError as exc:
            summaries.append(f"building pipeline package is not installed: {exc.name}")
    return "\n\n".join(summaries)


def validate(config: OrchestratorConfig) -> str:
    ensure_artifact_dirs(config)
    errors = []
    for blueprint in accepted_blueprint_files(config.accepted_blueprints_dir):
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


def build(config: OrchestratorConfig, *, dry_run: bool = False, overwrite: bool = False) -> str:
    return "\n\n".join(
        [
            analyze(config),
            render(config, dry_run=dry_run, overwrite=overwrite),
            validate(config),
        ]
    )

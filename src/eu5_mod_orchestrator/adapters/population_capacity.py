from __future__ import annotations

from pathlib import Path

from eu5_mod_orchestrator.config import OrchestratorConfig


def run_population_capacity_analyze(config: OrchestratorConfig) -> str:
    if config.population_capacity is None:
        return "population capacity skipped: no [population_capacity] config found"
    if not config.population_capacity.enabled:
        return "population capacity skipped: disabled"

    from prosper_or_perish_population_capacity import analyze_population_capacity

    return analyze_population_capacity(
        config.population_capacity.config_path,
        profile=config.profile,
        load_order_path=config.load_order_path or Path("constructor.load_order.toml"),
    )


def run_population_capacity_effects(config: OrchestratorConfig) -> str:
    if config.population_capacity is None:
        return "population capacity skipped: no [population_capacity] config found"
    if not config.population_capacity.enabled:
        return "population capacity skipped: disabled"

    from prosper_or_perish_population_capacity import analyze_capacity_effects

    return analyze_capacity_effects(
        config.population_capacity.config_path,
        profile=config.profile,
        load_order_path=config.load_order_path or Path("constructor.load_order.toml"),
    )


def run_population_capacity_preview_start(
    config: OrchestratorConfig,
    *,
    group_by: str | None = None,
    include_no_raw_material: bool = False,
) -> str:
    if config.population_capacity is None:
        return "population capacity skipped: no [population_capacity] config found"
    if not config.population_capacity.enabled:
        return "population capacity skipped: disabled"

    from prosper_or_perish_population_capacity import preview_start_capacity

    return preview_start_capacity(
        config.population_capacity.config_path,
        profile=config.profile,
        load_order_path=config.load_order_path or Path("constructor.load_order.toml"),
        group_by=group_by,
        include_no_raw_material=include_no_raw_material,
    )


def run_population_capacity_render(
    config: OrchestratorConfig,
    *,
    dry_run: bool = False,
) -> str:
    if config.population_capacity is None:
        return "population capacity skipped: no [population_capacity] config found"
    if not config.population_capacity.enabled:
        return "population capacity skipped: disabled"

    from prosper_or_perish_population_capacity import render_population_capacity

    return render_population_capacity(
        config.population_capacity.config_path,
        mod_root=config.mod_root,
        dry_run=dry_run,
    )


def run_population_capacity_extract(
    config: OrchestratorConfig,
    *,
    paths: list[Path],
    dry_run: bool = False,
) -> str:
    if config.population_capacity is None:
        return "population capacity skipped: no [population_capacity] config found"
    if not config.population_capacity.enabled:
        return "population capacity skipped: disabled"

    from prosper_or_perish_population_capacity import extract_population_capacity

    return extract_population_capacity(paths, dry_run=dry_run)


def run_population_capacity_extract_effects(
    config: OrchestratorConfig,
    *,
    paths: list[Path],
    dry_run: bool = False,
) -> str:
    if config.population_capacity is None:
        return "population capacity skipped: no [population_capacity] config found"
    if not config.population_capacity.enabled:
        return "population capacity skipped: disabled"

    from prosper_or_perish_population_capacity import extract_capacity_effects

    return extract_capacity_effects(paths, dry_run=dry_run)

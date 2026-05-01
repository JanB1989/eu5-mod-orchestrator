from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from eu5_mod_orchestrator.config import OrchestratorConfig


def run_labeling_pipeline(
    config: OrchestratorConfig,
    *,
    goods: str | None = None,
    scale: str | None = None,
    dry_run: bool = False,
) -> str:
    if config.labeling is None:
        return "labeling skipped: no [labeling] config found"
    if not config.labeling.enabled:
        return "labeling skipped: disabled"

    from mod_injector.__main__ import run as run_mod_injector
    from mod_injector.config import load_mod_injector_config

    injector_config = load_mod_injector_config(config.labeling.config_path)
    effective_config = replace(
        injector_config,
        mod_output_dir=config.mod_root.parent,
        mod_name=config.mod_root.name,
        modifier_prefix=config.labeling.modifier_prefix,
        generated_label=config.labeling.generated_label,
        managed_write_mode=config.labeling.managed_write_mode,
    )
    goods_filter = _goods_filter(goods)
    exit_code = run_mod_injector(
        effective_config,
        goods_filter=goods_filter,
        cli_scale=scale,
        dry_run=dry_run,
    )
    if exit_code != 0:
        return f"labeling failed with exit code {exit_code}"
    if dry_run:
        return "labeling dry run complete."
    return f"labeling complete: {Path(effective_config.mod_output_dir) / effective_config.mod_name}"


def _goods_filter(goods: str | None) -> set[str] | None:
    if not goods:
        return None
    selected = {item.strip() for item in goods.split(",") if item.strip()}
    return selected or None

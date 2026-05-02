from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from eu5_mod_orchestrator.config import BuildingOutputLayout, OrchestratorConfig

BOM = b"\xef\xbb\xbf"
MANAGED_BLOCK_START = "# >>> eu5-building-pipeline:"
_TEXT_OUTPUT_KINDS = ("building", "production_method", "price", "advancement", "localization")


@dataclass
class BuildingRenderResult:
    planned: list[Path] = field(default_factory=list)
    written: list[Path] = field(default_factory=list)
    skipped_assets: list[Path] = field(default_factory=list)
    dry_run: bool = False

    def summary(self) -> str:
        lines = ["building blueprint render complete."]
        if self.dry_run:
            lines[0] = "building blueprint render dry run complete."
        if self.planned:
            lines.append("Planned:")
            lines.extend(f"  {path}" for path in self.planned)
        if self.written:
            lines.append("Written:")
            lines.extend(f"  {path}" for path in self.written)
        if self.skipped_assets:
            lines.append("Skipped assets:")
            lines.extend(f"  {path}" for path in self.skipped_assets)
        return "\n".join(lines)


def render_building_blueprint(
    blueprint_path: Path,
    config: OrchestratorConfig,
    *,
    dry_run: bool,
    overwrite: bool,
    refresh_assets: bool,
    mod_root: Path | None = None,
) -> str:
    from eu5_building_pipeline import render_template, write_icon_asset

    bundle = render_template(blueprint_path)
    result = BuildingRenderResult(dry_run=dry_run)
    target_root = config.mod_root if mod_root is None else mod_root

    for text in bundle.texts:
        output_path = _text_output_path(target_root, config.building_outputs, text.kind, bundle.tag, bundle.key)
        result.planned.append(output_path)
        if not dry_run:
            _write_managed_text(
                output_path,
                text.content,
                marker=f"eu5-building-pipeline:{bundle.key}:{text.kind}",
                localization=text.kind == "localization",
                overwrite=overwrite,
            )
            result.written.append(output_path)

    if bundle.icon is not None:
        icon_path = target_root / config.building_outputs.icons / bundle.icon.output_dds
        result.planned.append(icon_path)
        if not dry_run:
            wrote_icon = write_icon_asset(bundle.icon, icon_path, overwrite=refresh_assets)
            if wrote_icon:
                result.written.append(icon_path)
            else:
                result.skipped_assets.append(icon_path)

    return result.summary()


def evaluate_building_blueprint(
    blueprint_path: Path,
    config: OrchestratorConfig,
    *,
    price_by_good: dict[str, float],
    raw_material_goods: set[str],
    script_values: dict[str, float],
    global_unlock_age_by_method: dict[str, str],
    global_unlock_age_by_building: dict[str, str],
) -> str:
    from eu5_building_pipeline.evaluation import format_evaluation

    return format_evaluation(
        evaluate_building_blueprint_data(
            blueprint_path,
            config,
            price_by_good=price_by_good,
            raw_material_goods=raw_material_goods,
            script_values=script_values,
            global_unlock_age_by_method=global_unlock_age_by_method,
            global_unlock_age_by_building=global_unlock_age_by_building,
        )
    )


def evaluate_building_blueprint_data(
    blueprint_path: Path,
    config: OrchestratorConfig,
    *,
    price_by_good: dict[str, float],
    raw_material_goods: set[str],
    script_values: dict[str, float],
    global_unlock_age_by_method: dict[str, str],
    global_unlock_age_by_building: dict[str, str],
):
    from eu5_building_pipeline.evaluation import evaluate_template_file

    return evaluate_template_file(
        blueprint_path,
        price_by_good=price_by_good,
        raw_material_goods=raw_material_goods,
        global_unlock_age_by_method=global_unlock_age_by_method,
        global_unlock_age_by_building=global_unlock_age_by_building,
        global_config=_pipeline_evaluation_config(config, script_values),
    )


def _pipeline_evaluation_config(config: OrchestratorConfig, script_values: dict[str, float]) -> dict:
    pipeline_config = config.blueprint_evaluation.to_pipeline_config()
    constants = dict(script_values)
    constants.update(pipeline_config.get("employment_size_constants", {}))
    pipeline_config["employment_size_constants"] = constants
    return pipeline_config


def plan_building_text_outputs(
    blueprint_path: Path,
    config: OrchestratorConfig,
    *,
    mod_root: Path | None = None,
) -> list[Path]:
    from eu5_building_pipeline import render_template

    bundle = render_template(blueprint_path)
    target_root = config.mod_root if mod_root is None else mod_root
    return [
        _text_output_path(target_root, config.building_outputs, text.kind, bundle.tag, bundle.key)
        for text in bundle.texts
    ]


def building_text_output_dirs(config: OrchestratorConfig, *, mod_root: Path | None = None) -> set[Path]:
    target_root = config.mod_root if mod_root is None else mod_root
    return {
        _text_output_path(target_root, config.building_outputs, kind, "__tag__", "__key__").parent
        for kind in _TEXT_OUTPUT_KINDS
    }


def _text_output_path(
    mod_root: Path,
    layout: BuildingOutputLayout,
    kind: str,
    tag: str,
    key: str,
) -> Path:
    patterns = {
        "building": layout.building_types,
        "production_method": layout.production_methods,
        "price": layout.prices,
        "advancement": layout.advances,
        "localization": layout.localization,
    }
    if kind not in patterns:
        raise ValueError(f"Unknown building text fragment kind: {kind}")
    return mod_root / patterns[kind].format(prefix=layout.prefix, tag=tag, key=key)


def _write_managed_text(
    path: Path,
    content: str,
    *,
    marker: str,
    localization: bool,
    overwrite: bool,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    updated = _upsert_managed_block(existing, content, marker, localization=localization, overwrite=overwrite)
    path.write_text(updated, encoding="utf-8-sig", newline="\n")
    if not path.read_bytes().startswith(BOM):
        raise RuntimeError(f"Generated text file is missing UTF-8 BOM: {path}")


def _upsert_managed_block(
    existing: str,
    content: str,
    marker: str,
    *,
    localization: bool,
    overwrite: bool,
) -> str:
    start = f"# >>> {marker}"
    end = f"# <<< {marker}"
    block = f"{start}\n{content.rstrip()}\n{end}"
    if not existing.strip() and localization:
        existing = "l_english:\n"

    start_index = existing.find(start)
    if start_index != -1:
        end_index = existing.find(end, start_index)
        if end_index == -1:
            if overwrite:
                return _normalize_trailing_newline(existing[:start_index] + block)
            raise RuntimeError(f"Managed block start found without end marker: {marker}")
        end_index += len(end)
        return _normalize_trailing_newline(existing[:start_index] + block + existing[end_index:])

    prefix = _normalize_trailing_newline(existing)
    if prefix.strip():
        prefix = prefix.rstrip() + "\n\n"
    return prefix + block + "\n"


def _normalize_trailing_newline(content: str) -> str:
    return content.rstrip() + "\n" if content else ""

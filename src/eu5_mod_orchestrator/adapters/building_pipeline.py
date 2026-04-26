from __future__ import annotations

from pathlib import Path


def render_building_blueprint(
    blueprint_path: Path,
    mod_root: Path,
    *,
    dry_run: bool,
    overwrite: bool,
) -> str:
    from eu5_building_pipeline import create_building

    result = create_building(
        template_path=blueprint_path,
        mod_root=mod_root,
        dry_run=dry_run,
        overwrite=overwrite,
    )
    return result.summary()

from pathlib import Path
import os

from PIL import Image, ImageDraw

from eu5_mod_orchestrator.adapters.building_pipeline import BOM, render_building_blueprint
from eu5_mod_orchestrator.config import load_project_config


def _config(tmp_path: Path):
    config_path = tmp_path / "foundations.toml"
    config_path.write_text(
        """
[project]
name = "Foundations"
mod_root = "mod/Foundations"

[building_outputs]
prefix = "zz_foundation_"
building_types = "in_game/common/building_types/{prefix}{tag}.txt"
prices = "in_game/common/prices/{prefix}{tag}.txt"
advances = "in_game/common/advances/{prefix}{tag}.txt"
localization = "main_menu/localization/english/{prefix}{tag}_l_english.yml"
icons = "in_game/gfx/interface/icons/buildings"
""".strip(),
        encoding="utf-8",
    )
    return load_project_config(config_path)


def _transparent_png(path: Path) -> None:
    image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((96, 96, 416, 416), fill=(120, 90, 60, 255))
    image.save(path)


def _blueprint(tmp_path: Path, *, icon_name: str = "test_building.dds", icon_line: str = "icon = test_building") -> Path:
    assets = tmp_path / "blueprints" / "accepted" / "assets" / "icons"
    assets.mkdir(parents=True, exist_ok=True)
    icon_path = assets / "test_building.png"
    _transparent_png(icon_path)
    blueprint = tmp_path / "blueprints" / "accepted" / "buildings" / "test_building.yml"
    blueprint.parent.mkdir(parents=True, exist_ok=True)
    blueprint.write_text(
        f"""
tag: test

building:
  key: test_building
  body: |
    is_foreign = no
    {icon_line}
price:
  key: pp_test_building_price
  body: "{{gold = 25}}"
advancements:
  - key: pp_test_building_advance
    body: |
      age = age_1_traditions
      ai_weight = {{ add = 50 }}
localization:
  entries:
    test_building: Test Building
icon:
  source_png: ../assets/icons/test_building.png
  output_dds: {icon_name}
  size: 512
  prompt: Test icon.
""".strip(),
        encoding="utf-8",
    )
    return blueprint


def test_render_building_blueprint_uses_project_layout_for_dry_run(tmp_path: Path) -> None:
    config = _config(tmp_path)
    blueprint = _blueprint(tmp_path)

    summary = render_building_blueprint(blueprint, config, dry_run=True, overwrite=False, refresh_assets=False)

    assert str(config.mod_root / "in_game" / "common" / "building_types" / "zz_foundation_test.txt") in summary
    assert str(config.mod_root / "in_game" / "common" / "prices" / "zz_foundation_test.txt") in summary
    assert str(config.mod_root / "in_game" / "common" / "advances" / "zz_foundation_test.txt") in summary
    assert str(config.mod_root / "main_menu" / "localization" / "english" / "zz_foundation_test_l_english.yml") in summary
    assert str(config.mod_root / "in_game" / "gfx" / "interface" / "icons" / "buildings" / "test_building.dds") in summary
    assert not config.mod_root.exists()


def test_render_building_blueprint_writes_managed_blocks_and_bom(tmp_path: Path) -> None:
    config = _config(tmp_path)
    blueprint = _blueprint(tmp_path, icon_line="icon = first_icon")
    building_path = config.mod_root / "in_game" / "common" / "building_types" / "zz_foundation_test.txt"
    building_path.parent.mkdir(parents=True)
    building_path.write_text("hand_written_building = {}\n", encoding="utf-8-sig")

    render_building_blueprint(blueprint, config, dry_run=False, overwrite=False, refresh_assets=False)
    blueprint = _blueprint(tmp_path, icon_line="icon = second_icon")
    render_building_blueprint(blueprint, config, dry_run=False, overwrite=False, refresh_assets=False)

    updated = building_path.read_text(encoding="utf-8-sig")
    localization_path = config.mod_root / "main_menu" / "localization" / "english" / "zz_foundation_test_l_english.yml"
    assert building_path.read_bytes().startswith(BOM)
    assert "hand_written_building = {}" in updated
    assert "icon = first_icon" not in updated
    assert "icon = second_icon" in updated
    assert updated.count("# >>> eu5-building-pipeline:test_building:building") == 1
    assert localization_path.read_bytes().startswith(BOM)
    assert localization_path.read_text(encoding="utf-8-sig").startswith("l_english:")


def test_render_building_blueprint_preserves_unchanged_text_mtime(tmp_path: Path) -> None:
    config = _config(tmp_path)
    blueprint = _blueprint(tmp_path)
    building_path = config.mod_root / "in_game" / "common" / "building_types" / "zz_foundation_test.txt"

    render_building_blueprint(blueprint, config, dry_run=False, overwrite=False, refresh_assets=False)
    fixed_time = 1_700_000_000_000_000_000
    os.utime(building_path, ns=(fixed_time, fixed_time))

    summary = render_building_blueprint(blueprint, config, dry_run=False, overwrite=False, refresh_assets=False)

    assert building_path.stat().st_mtime_ns == fixed_time
    assert "Written:" not in summary


def test_render_building_blueprint_preserves_icon_unless_refreshed(tmp_path: Path) -> None:
    config = _config(tmp_path)
    blueprint = _blueprint(tmp_path, icon_name="test_building.dds")
    icon_path = config.mod_root / "in_game" / "gfx" / "interface" / "icons" / "buildings" / "test_building.dds"

    render_building_blueprint(blueprint, config, dry_run=False, overwrite=False, refresh_assets=False)
    first = icon_path.read_bytes()
    icon_path.write_bytes(b"existing")

    summary = render_building_blueprint(blueprint, config, dry_run=False, overwrite=False, refresh_assets=False)
    assert "Skipped assets:" in summary
    assert icon_path.read_bytes() == b"existing"

    render_building_blueprint(blueprint, config, dry_run=False, overwrite=False, refresh_assets=True)
    assert icon_path.read_bytes() != b"existing"
    assert icon_path.read_bytes() == first


def test_render_v2_blueprint_writes_production_methods_without_icon(tmp_path: Path) -> None:
    config = _config(tmp_path)
    blueprint = tmp_path / "blueprints" / "accepted" / "buildings" / "cookery.yml"
    blueprint.parent.mkdir(parents=True, exist_ok=True)
    blueprint.write_text(
        """
version: 2
tag: cookery
building:
  key: cookery
  mode: REPLACE
  body: |
    is_foreign = no
production_methods:
  - key: victuals_market_maintenance
    body: |
      victuals = 2.0
      category = building_maintenance
localization:
  entries:
    cookery: Cookery
""".strip(),
        encoding="utf-8",
    )

    render_building_blueprint(blueprint, config, dry_run=False, overwrite=False, refresh_assets=False)

    building_path = config.mod_root / "in_game" / "common" / "building_types" / "zz_foundation_cookery.txt"
    method_path = config.mod_root / "in_game" / "common" / "production_methods" / "cookery.txt"
    assert "REPLACE:cookery = {" in building_path.read_text(encoding="utf-8-sig")
    assert "victuals_market_maintenance = {" in method_path.read_text(encoding="utf-8-sig")

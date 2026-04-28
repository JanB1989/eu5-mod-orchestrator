from pathlib import Path

from eu5_mod_orchestrator.config import load_project_config
from eu5_mod_orchestrator.workflow import render


def _config(tmp_path: Path):
    config_path = tmp_path / "foundations.toml"
    config_path.write_text(
        """
[project]
name = "Foundations"
mod_root = "mod/Foundations"

[building_outputs]
prefix = "pp_"
building_types = "in_game/common/building_types/{prefix}{tag}.txt"
production_methods = "in_game/common/production_methods/{prefix}{tag}.txt"
prices = "in_game/common/prices/{prefix}{tag}.txt"
advances = "in_game/common/advances/{prefix}{tag}.txt"
localization = "main_menu/localization/english/{prefix}{tag}_l_english.yml"
icons = "in_game/gfx/interface/icons/buildings"
""".strip(),
        encoding="utf-8",
    )
    return load_project_config(config_path)


def _blueprint(tmp_path: Path) -> Path:
    blueprint = tmp_path / "blueprints" / "accepted" / "buildings" / "test_building.yml"
    blueprint.parent.mkdir(parents=True, exist_ok=True)
    blueprint.write_text(
        """
version: 2
tag: test
building:
  key: test_building
  mode: REPLACE
  body: |
    is_foreign = no
localization:
  entries:
    test_building: Test Building
""".strip(),
        encoding="utf-8",
    )
    return blueprint


def test_render_removes_stale_managed_outputs_after_prefix_change(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _blueprint(tmp_path)
    stale_path = config.mod_root / "in_game" / "common" / "building_types" / "zz_constructor_test.txt"
    stale_path.parent.mkdir(parents=True, exist_ok=True)
    stale_path.write_text(
        """
# >>> eu5-building-pipeline:test_building:building
test_building = {}
# <<< eu5-building-pipeline:test_building:building
""".lstrip(),
        encoding="utf-8-sig",
    )

    summary = render(config, dry_run=False, overwrite=True, refresh_assets=False)

    current_path = config.mod_root / "in_game" / "common" / "building_types" / "pp_test.txt"
    assert "stale managed building output cleanup complete." in summary
    assert not stale_path.exists()
    assert current_path.exists()


def test_render_preserves_unmanaged_files_during_stale_cleanup(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _blueprint(tmp_path)
    unmanaged_path = config.mod_root / "in_game" / "common" / "building_types" / "zz_constructor_test.txt"
    unmanaged_path.parent.mkdir(parents=True, exist_ok=True)
    unmanaged_path.write_text("hand_written_building = {}\n", encoding="utf-8-sig")

    render(config, dry_run=False, overwrite=True, refresh_assets=False)

    assert unmanaged_path.exists()
    assert unmanaged_path.read_text(encoding="utf-8-sig") == "hand_written_building = {}\n"


def test_render_dry_run_reports_stale_managed_outputs_without_deleting(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _blueprint(tmp_path)
    stale_path = config.mod_root / "main_menu" / "localization" / "english" / "zz_constructor_test_l_english.yml"
    stale_path.parent.mkdir(parents=True, exist_ok=True)
    stale_path.write_text(
        """
l_english:
# >>> eu5-building-pipeline:test_building:localization
 test_building: "Old Test Building"
# <<< eu5-building-pipeline:test_building:localization
""".lstrip(),
        encoding="utf-8-sig",
    )

    summary = render(config, dry_run=True, overwrite=True, refresh_assets=False)

    assert "stale managed building output cleanup dry run complete." in summary
    assert str(stale_path) in summary
    assert stale_path.exists()

from pathlib import Path

import pytest

from eu5_mod_orchestrator.blueprints import BlueprintError, validate_blueprint_file


def test_validate_blueprint_file_accepts_building_pipeline_shape(tmp_path: Path) -> None:
    blueprint = tmp_path / "test.yml"
    blueprint.write_text(
        """
building:
  key: test_building
  body: |
    category = rgo_building_category
price:
  key: test_building_price
  body: "{gold = 100}"
localization:
  file: test_building_l_english.yml
  entries:
    test_building: Test Building
icon:
  source_png: ../assets/test.png
  output_dds: test_building.dds
  size: 512
""".strip(),
        encoding="utf-8",
    )

    assert validate_blueprint_file(blueprint)["building"]["key"] == "test_building"


def test_validate_blueprint_file_rejects_missing_sections(tmp_path: Path) -> None:
    blueprint = tmp_path / "bad.yml"
    blueprint.write_text("building: {}\n", encoding="utf-8")

    with pytest.raises(BlueprintError):
        validate_blueprint_file(blueprint)

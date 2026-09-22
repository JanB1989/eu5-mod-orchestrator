from pathlib import Path

import pytest

from eu5_mod_orchestrator.blueprints import BlueprintError, validate_blueprint_file


def test_validate_blueprint_file_accepts_building_pipeline_shape(tmp_path: Path) -> None:
    blueprint = tmp_path / "test_building.yml"
    blueprint.write_text(
        """
tag: test

building:
  key: test_building
  body: |
    category = rgo_building_category
price:
  key: test_building_price
  body: "{gold = 100}"
localization:
  entries:
    test_building: Test Building
advancements:
  - key: test_advance
    body: |
      age = age_1_traditions
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


def test_validate_blueprint_file_accepts_v2_without_price_or_icon(tmp_path: Path) -> None:
    blueprint = tmp_path / "cookery.yml"
    blueprint.write_text(
        """
version: 2
tag: cookery
building:
  key: cookery
  mode: REPLACE
  production_method_slots:
    - name: Prepared Victuals
      methods: [pp_cookery_khichdi]
  body: |
    is_foreign = no
production_methods:
  - key: victuals_market_maintenance
    body: |
      victuals = 2.0
""".strip(),
        encoding="utf-8",
    )

    assert validate_blueprint_file(blueprint)["version"] == 2


def test_validate_blueprint_file_rejects_unsafe_output_tag(tmp_path: Path) -> None:
    blueprint = tmp_path / "test_building.yml"
    blueprint.write_text(
        """
version: 2
tag: test
output_tag: Bad-Tag
building:
  key: test_building
  body: |
    is_foreign = no
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(BlueprintError, match="output_tag"):
        validate_blueprint_file(blueprint)


def test_accepted_blueprint_files_searches_recursively(tmp_path: Path) -> None:
    nested = tmp_path / "buildings"
    nested.mkdir()
    blueprint = nested / "test_building.yml"
    blueprint.write_text("tag: test\n", encoding="utf-8")

    from eu5_mod_orchestrator.blueprints import accepted_blueprint_files

    assert accepted_blueprint_files(tmp_path) == [blueprint]


def test_enabled_manifest_entries_supports_path_toggles() -> None:
    from eu5_mod_orchestrator.blueprints import declared_manifest_entries, enabled_manifest_entries

    mapping = {
        "buildings/aqueduct_system.yml": True,
        "buildings/amber_collector.yml": False,
        "buildings/alum_quarry.yml": True,
    }
    assert enabled_manifest_entries(mapping) == [
        "buildings/aqueduct_system.yml",
        "buildings/alum_quarry.yml",
    ]
    assert declared_manifest_entries(mapping) == [
        "buildings/aqueduct_system.yml",
        "buildings/amber_collector.yml",
        "buildings/alum_quarry.yml",
    ]
    assert enabled_manifest_entries(
        [
            "buildings/aqueduct_system.yml",
            {"buildings/amber_collector.yml": False},
            {"buildings/alum_quarry.yml": True},
        ]
    ) == [
        "buildings/aqueduct_system.yml",
        "buildings/alum_quarry.yml",
    ]


def test_manifest_blueprint_files_honors_disabled_toggles(tmp_path: Path) -> None:
    from eu5_mod_orchestrator.blueprints import manifest_blueprint_files

    accepted = tmp_path / "accepted"
    buildings = accepted / "buildings"
    buildings.mkdir(parents=True)
    (buildings / "on.yml").write_text("tag: on\n", encoding="utf-8")
    (buildings / "off.yml").write_text("tag: off\n", encoding="utf-8")
    manifest = tmp_path / "buildings.manifest.yml"
    manifest.write_text(
        "enabled:\n  buildings/on.yml: true\n  buildings/off.yml: false\n",
        encoding="utf-8",
    )

    assert manifest_blueprint_files(accepted, manifest) == [(buildings / "on.yml").resolve()]

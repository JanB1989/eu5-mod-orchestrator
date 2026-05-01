import json
from pathlib import Path

from eu5_mod_orchestrator.config import load_project_config
from eu5_mod_orchestrator import workflow
from eu5_mod_orchestrator.workflow import build, evaluate_blueprints, label, population_capacity_effects, population_capacity_render, render


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


def _labeling_config(tmp_path: Path):
    config_path = tmp_path / "foundations.toml"
    config_path.write_text(
        """
[project]
name = "Foundations"
mod_root = "mod/Foundations"

[labeling]
enabled = true
config = "../labeling/mod_injector_config.yaml"
modifier_prefix = "pp"
generated_label = "Prosper or Perish"
managed_write_mode = "mod_root"
""".strip(),
        encoding="utf-8",
    )
    return load_project_config(config_path)


def _population_capacity_config(tmp_path: Path):
    config_path = tmp_path / "foundations.toml"
    config_path.write_text(
        """
[project]
name = "Foundations"
mod_root = "mod/Foundations"

[population_capacity]
enabled = true
config = "../population-capacity/population_capacity.toml"
generated_label = "Prosper or Perish"
managed_write_mode = "mod_root"
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


def test_label_dry_run_calls_labeling_adapter(tmp_path: Path, monkeypatch) -> None:
    config = _labeling_config(tmp_path)
    calls = []

    def fake_run(config_arg, *, goods, scale, dry_run):
        calls.append((config_arg, goods, scale, dry_run))
        return "fake labeling"

    monkeypatch.setattr(workflow, "run_labeling_pipeline", fake_run)

    assert label(config, dry_run=True) == "fake labeling"
    assert calls == [(config, None, None, True)]


def test_label_passes_goods_filter_to_adapter(tmp_path: Path, monkeypatch) -> None:
    config = _labeling_config(tmp_path)
    calls = []

    def fake_run(config_arg, *, goods, scale, dry_run):
        calls.append((goods, scale, dry_run))
        return "fake labeling"

    monkeypatch.setattr(workflow, "run_labeling_pipeline", fake_run)

    label(config, goods="fish,wheat", scale="rank_uniform", dry_run=False)

    assert calls == [("fish,wheat", "rank_uniform", False)]


def test_build_runs_labeling_between_analyze_and_validate(tmp_path: Path, monkeypatch) -> None:
    config = _labeling_config(tmp_path)
    calls = []

    monkeypatch.setattr(workflow, "analyze", lambda config_arg: calls.append("analyze") or "analyze")
    monkeypatch.setattr(
        workflow,
        "label",
        lambda config_arg, dry_run=False: calls.append("label") or "label",
    )
    monkeypatch.setattr(
        workflow,
        "evaluate_blueprints",
        lambda config_arg: calls.append("evaluate") or "evaluate",
    )
    monkeypatch.setattr(
        workflow,
        "population_capacity_render",
        lambda config_arg, dry_run=False: calls.append("population_capacity") or "population_capacity",
    )
    monkeypatch.setattr(
        workflow,
        "render",
        lambda config_arg, dry_run=False, overwrite=False, refresh_assets=False: calls.append("render") or "render",
    )
    monkeypatch.setattr(workflow, "validate", lambda config_arg: calls.append("validate") or "validate")

    summary = build(config, dry_run=True)

    assert calls == ["analyze", "label", "evaluate", "render", "population_capacity", "validate"]
    assert summary == "analyze\n\nlabel\n\nevaluate\n\nrender\n\npopulation_capacity\n\nvalidate"


def test_evaluate_blueprints_uses_parser_balance_inputs(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    blueprint = _blueprint(tmp_path)
    calls = []

    monkeypatch.setattr(
        workflow,
        "load_balance_prices",
        lambda profile, load_order_path: {"tools": 3.0},
    )

    def fake_evaluate(blueprint_arg, config_arg, *, price_by_good):
        calls.append((blueprint_arg, config_arg, price_by_good))
        return "fake evaluation"

    monkeypatch.setattr(workflow, "evaluate_building_blueprint", fake_evaluate)

    assert evaluate_blueprints(config) == "fake evaluation"
    assert calls == [(blueprint, config, {"tools": 3.0})]


def test_evaluate_blueprints_can_emit_json(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    _blueprint(tmp_path)

    monkeypatch.setattr(
        workflow,
        "load_balance_prices",
        lambda profile, load_order_path: {"tools": 3.0},
    )

    class FakeEvaluation:
        tag = "test"
        building = "test_building"
        warnings = ()
        violations = ()
        methods = ()

    monkeypatch.setattr(
        workflow,
        "evaluate_building_blueprint_data",
        lambda blueprint_arg, config_arg, price_by_good: FakeEvaluation(),
    )

    assert json.loads(evaluate_blueprints(config, output_format="json")) == [
        {"building": "test_building", "methods": [], "tag": "test", "violations": [], "warnings": []}
    ]


def test_evaluate_blueprints_can_filter_to_single_building(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    blueprint = _blueprint(tmp_path)
    other = tmp_path / "blueprints" / "accepted" / "buildings" / "other_building.yml"
    other.write_text(
        """
version: 2
tag: other
building:
  key: other_building
  body: |
    is_foreign = no
""".strip(),
        encoding="utf-8",
    )
    calls = []

    monkeypatch.setattr(
        workflow,
        "load_balance_prices",
        lambda profile, load_order_path: {},
    )
    monkeypatch.setattr(
        workflow,
        "evaluate_building_blueprint",
        lambda blueprint_arg, config_arg, price_by_good: calls.append(blueprint_arg)
        or "fake evaluation",
    )

    assert evaluate_blueprints(config, building="test_building") == "fake evaluation"
    assert calls == [blueprint]


def test_population_capacity_render_calls_adapter(tmp_path: Path, monkeypatch) -> None:
    config = _population_capacity_config(tmp_path)
    calls = []

    def fake_run(config_arg, *, dry_run):
        calls.append((config_arg, dry_run))
        return "fake population capacity"

    monkeypatch.setattr(workflow, "run_population_capacity_render", fake_run)

    assert population_capacity_render(config, dry_run=True) == "fake population capacity"
    assert calls == [(config, True)]


def test_population_capacity_effects_calls_adapter(tmp_path: Path, monkeypatch) -> None:
    config = _population_capacity_config(tmp_path)
    calls = []

    def fake_run(config_arg):
        calls.append(config_arg)
        return "fake effects"

    monkeypatch.setattr(workflow, "run_population_capacity_effects", fake_run)

    assert population_capacity_effects(config) == "fake effects"
    assert calls == [config]


def test_population_capacity_preview_passes_raw_material_filter_flag(tmp_path: Path, monkeypatch) -> None:
    config = _population_capacity_config(tmp_path)
    calls = []

    def fake_run(config_arg, *, group_by, include_no_raw_material):
        calls.append((config_arg, group_by, include_no_raw_material))
        return "fake preview"

    monkeypatch.setattr(workflow, "run_population_capacity_preview_start", fake_run)

    assert (
        workflow.population_capacity_preview_start(
            config,
            group_by="climate",
            include_no_raw_material=True,
        )
        == "fake preview"
    )
    assert calls == [(config, "climate", True)]

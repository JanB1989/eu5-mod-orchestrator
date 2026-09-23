import json
from pathlib import Path

from eu5_building_pipeline.evaluation import (
    BlueprintEvaluation,
    EvaluatedBuildingModifier,
    EvaluatedProductionMethod,
)
from eu5_mod_orchestrator.config import load_project_config
from eu5_mod_orchestrator import workflow
from eu5_mod_orchestrator.workflow import (
    build,
    evaluate_blueprint_good,
    evaluate_blueprint_ratios,
    evaluate_blueprints,
    render,
)


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


def _blueprint(
    tmp_path: Path,
    *,
    output_tag: str | None = None,
    custom_tags: tuple[str, ...] = (),
) -> Path:
    blueprint = tmp_path / "blueprints" / "accepted" / "buildings" / "test_building.yml"
    blueprint.parent.mkdir(parents=True, exist_ok=True)
    output_tag_line = f"output_tag: {output_tag}\n" if output_tag is not None else ""
    custom_tags_line = f"    custom_tags = {{ {' '.join(custom_tags)} }}\n" if custom_tags else ""
    blueprint.write_text(
        f"""
version: 2
tag: test
{output_tag_line}
building:
  key: test_building
  mode: REPLACE
  body: |
    is_foreign = no
{custom_tags_line.rstrip()}
localization:
  entries:
    test_building: Test Building
""".strip(),
        encoding="utf-8",
    )
    return blueprint


def _evaluated_method(
    name: str,
    produced: str | None,
    *,
    building: str = "test_building",
    building_category: str | None = None,
    employment_size: float | None = None,
    building_cost_gold: float | None = None,
    building_modifiers: tuple[EvaluatedBuildingModifier, ...] = (),
    input_gold: float = 0.0,
) -> EvaluatedProductionMethod:
    return EvaluatedProductionMethod(
        name=name,
        building=building,
        global_unlock_age=None,
        produced=produced,
        output=1.0,
        inputs=(),
        production_efficiency=1.0,
        building_pop_type=None,
        building_category=building_category,
        employment_size=employment_size,
        building_cost_gold=building_cost_gold,
        building_modifiers=building_modifiers,
        raw_material_input_count=0,
        input_gold=input_gold,
        output_gold=1.0,
        profit_gold=1.0,
        profit_percent=None,
        input_gold_per_1k=None,
        output_gold_per_1k=None,
        base_output_per_1k=None,
        amortization_months=None,
        missing_price_goods=(),
        warnings=(),
        rule_diagnostics=(),
        allowed_violations=(),
        violations=(),
    )


def _evaluation(
    *,
    tag: str = "test",
    building: str = "test_building",
    methods: tuple[EvaluatedProductionMethod, ...],
) -> BlueprintEvaluation:
    return BlueprintEvaluation(
        tag=tag,
        building=building,
        methods=methods,
        warnings=(),
        allowed_violations=(),
        violations=(),
    )


def _stub_evaluation_inputs(monkeypatch) -> None:
    monkeypatch.setattr(workflow, "load_balance_prices", lambda profile, load_order_path: {})
    monkeypatch.setattr(workflow, "load_global_unlock_ages", lambda profile, load_order_path: {})
    monkeypatch.setattr(workflow, "load_global_building_unlock_ages", lambda profile, load_order_path: {})
    monkeypatch.setattr(workflow, "load_raw_material_goods", lambda profile, load_order_path: set())
    monkeypatch.setattr(workflow, "load_script_values", lambda profile, load_order_path: {})
    monkeypatch.setattr(workflow, "load_food_cost_context", lambda profile, load_order_path: None)


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


def test_render_removes_stale_managed_outputs_after_output_tag_change(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _blueprint(tmp_path, output_tag="test_after_dependency")
    stale_path = config.mod_root / "in_game" / "common" / "building_types" / "pp_test.txt"
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

    current_path = config.mod_root / "in_game" / "common" / "building_types" / "pp_test_after_dependency.txt"
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


def test_build_runs_analyze_evaluate_render_and_validate_in_order(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    calls = []

    monkeypatch.setattr(workflow, "analyze", lambda config_arg: calls.append("analyze") or "analyze")
    monkeypatch.setattr(
        workflow,
        "evaluate_blueprints",
        lambda config_arg: calls.append("evaluate") or "evaluate",
    )
    monkeypatch.setattr(
        workflow,
        "render",
        lambda config_arg, dry_run=False, overwrite=False, refresh_assets=False: calls.append("render") or "render",
    )
    monkeypatch.setattr(workflow, "validate", lambda config_arg: calls.append("validate") or "validate")

    summary = build(config, dry_run=True)

    assert calls == ["analyze", "evaluate", "render", "validate"]
    assert summary == "analyze\n\nevaluate\n\nrender\n\nvalidate"


def test_evaluate_blueprints_uses_parser_balance_inputs(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    blueprint = _blueprint(tmp_path)
    calls = []
    food_cost_context = object()

    monkeypatch.setattr(
        workflow,
        "load_balance_prices",
        lambda profile, load_order_path: {"tools": 3.0},
    )
    monkeypatch.setattr(
        workflow,
        "load_global_unlock_ages",
        lambda profile, load_order_path: {"pp_method": "age_2_renaissance"},
    )
    monkeypatch.setattr(
        workflow,
        "load_global_building_unlock_ages",
        lambda profile, load_order_path: {"test_building": "age_2_renaissance"},
    )
    monkeypatch.setattr(
        workflow,
        "load_raw_material_goods",
        lambda profile, load_order_path: {"iron"},
    )
    monkeypatch.setattr(
        workflow,
        "load_script_values",
        lambda profile, load_order_path: {"rural_peasant_produce_employment": 1.0},
    )
    monkeypatch.setattr(
        workflow,
        "load_food_cost_context",
        lambda profile, load_order_path: food_cost_context,
    )

    def fake_evaluate(
        blueprint_arg,
        config_arg,
        *,
        price_by_good,
        raw_material_goods,
        script_values,
        global_unlock_age_by_method,
        global_unlock_age_by_building,
        food_cost_context,
    ):
        calls.append(
            (
                blueprint_arg,
                config_arg,
                price_by_good,
                raw_material_goods,
                script_values,
                global_unlock_age_by_method,
                global_unlock_age_by_building,
                food_cost_context,
            )
        )
        return "fake evaluation"

    monkeypatch.setattr(workflow, "evaluate_building_blueprint", fake_evaluate)

    assert evaluate_blueprints(config) == "fake evaluation"
    assert calls == [
        (
            blueprint,
            config,
            {"tools": 3.0},
            {"iron"},
            {"rural_peasant_produce_employment": 1.0},
            {"pp_method": "age_2_renaissance"},
            {"test_building": "age_2_renaissance"},
            food_cost_context,
        )
    ]


def test_evaluate_blueprints_can_emit_json(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    _blueprint(tmp_path)

    monkeypatch.setattr(
        workflow,
        "load_balance_prices",
        lambda profile, load_order_path: {"tools": 3.0},
    )
    monkeypatch.setattr(
        workflow,
        "load_global_unlock_ages",
        lambda profile, load_order_path: {},
    )
    monkeypatch.setattr(
        workflow,
        "load_global_building_unlock_ages",
        lambda profile, load_order_path: {},
    )
    monkeypatch.setattr(
        workflow,
        "load_raw_material_goods",
        lambda profile, load_order_path: set(),
    )
    monkeypatch.setattr(
        workflow,
        "load_script_values",
        lambda profile, load_order_path: {},
    )
    monkeypatch.setattr(
        workflow,
        "load_food_cost_context",
        lambda profile, load_order_path: None,
    )

    class FakeEvaluation:
        tag = "test"
        building = "test_building"
        warnings = ()
        allowed_violations = ()
        violations = ()
        methods = ()

    monkeypatch.setattr(
        workflow,
        "evaluate_building_blueprint_data",
        lambda blueprint_arg, config_arg, price_by_good, raw_material_goods, script_values, global_unlock_age_by_method, global_unlock_age_by_building, food_cost_context: FakeEvaluation(),
    )

    assert json.loads(evaluate_blueprints(config, output_format="json")) == [
        {
            "allowed_violations": [],
            "building": "test_building",
            "methods": [],
            "tag": "test",
            "violations": [],
            "warnings": [],
        }
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
        "load_global_unlock_ages",
        lambda profile, load_order_path: {},
    )
    monkeypatch.setattr(
        workflow,
        "load_global_building_unlock_ages",
        lambda profile, load_order_path: {},
    )
    monkeypatch.setattr(
        workflow,
        "load_raw_material_goods",
        lambda profile, load_order_path: set(),
    )
    monkeypatch.setattr(
        workflow,
        "load_script_values",
        lambda profile, load_order_path: {},
    )
    monkeypatch.setattr(
        workflow,
        "load_food_cost_context",
        lambda profile, load_order_path: None,
    )
    monkeypatch.setattr(
        workflow,
        "evaluate_building_blueprint",
        lambda blueprint_arg, config_arg, price_by_good, raw_material_goods, script_values, global_unlock_age_by_method, global_unlock_age_by_building, food_cost_context: calls.append(blueprint_arg)
        or "fake evaluation",
    )

    assert evaluate_blueprints(config, building="test_building") == "fake evaluation"
    assert calls == [blueprint]


def test_evaluate_blueprint_good_outputs_single_text_report(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    _blueprint(tmp_path)
    _stub_evaluation_inputs(monkeypatch)
    monkeypatch.setattr(
        workflow,
        "evaluate_building_blueprint_data",
        lambda blueprint_arg, config_arg, price_by_good, raw_material_goods, script_values, global_unlock_age_by_method, global_unlock_age_by_building, food_cost_context: _evaluation(
            methods=(
                _evaluated_method("coal_method", "coal"),
                _evaluated_method("tools_method", "tools"),
            )
        ),
    )

    summary = evaluate_blueprint_good(config, good="coal")

    assert summary.count("Columns:") == 1
    assert "coal_method" in summary
    assert "tools_method" not in summary


def test_evaluate_blueprint_good_can_emit_flat_json(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    _blueprint(tmp_path)
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
    _stub_evaluation_inputs(monkeypatch)

    def fake_evaluate(
        blueprint_arg,
        config_arg,
        *,
        price_by_good,
        raw_material_goods,
        script_values,
        global_unlock_age_by_method,
        global_unlock_age_by_building,
        food_cost_context,
    ):
        if blueprint_arg == other:
            return _evaluation(tag="other", building="other_building", methods=(_evaluated_method("tools_method", "tools"),))
        return _evaluation(
            methods=(
                _evaluated_method("coal_method", "coal"),
                _evaluated_method("tools_method", "tools"),
            )
        )

    monkeypatch.setattr(workflow, "evaluate_building_blueprint_data", fake_evaluate)

    result = json.loads(evaluate_blueprint_good(config, output_format="json", good="coal"))

    assert result["good"] == "coal"
    assert [method["building"] for method in result["methods"]] == ["test_building"]
    assert [method["name"] for method in result["methods"]] == ["coal_method"]


def test_evaluate_blueprint_good_reports_when_good_has_no_matches(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    _blueprint(tmp_path)
    _stub_evaluation_inputs(monkeypatch)
    monkeypatch.setattr(
        workflow,
        "evaluate_building_blueprint_data",
        lambda blueprint_arg, config_arg, price_by_good, raw_material_goods, script_values, global_unlock_age_by_method, global_unlock_age_by_building, food_cost_context: _evaluation(
            methods=(_evaluated_method("tools_method", "tools"),)
        ),
    )

    assert evaluate_blueprint_good(config, good="coal") == "no accepted blueprint methods produced 'coal'"


def test_evaluate_blueprint_ratios_filters_and_outputs_combined_table(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    blueprint = _blueprint(tmp_path, custom_tags=("pp_test_ratios",))
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
    _stub_evaluation_inputs(monkeypatch)

    def fake_evaluate(
        blueprint_arg,
        config_arg,
        *,
        price_by_good,
        raw_material_goods,
        script_values,
        global_unlock_age_by_method,
        global_unlock_age_by_building,
        food_cost_context,
    ):
        if blueprint_arg == other:
            return _evaluation(
                tag="other",
                building="other_building",
                methods=(
                    _evaluated_method(
                        "other_method",
                        None,
                        building="other_building",
                        building_category="infrastructure_category",
                        employment_size=1.0,
                        building_cost_gold=100.0,
                        input_gold=1.0,
                        building_modifiers=(
                            EvaluatedBuildingModifier(
                                name="local_market_access",
                                amount=0.02,
                                per_building_gold=0.0002,
                                per_maintenance_gold=0.02,
                                per_1k=0.02,
                            ),
                        ),
                    ),
                ),
            )
        return _evaluation(
            methods=(
                _evaluated_method(
                    "test_method",
                    None,
                    building_category="infrastructure_category",
                    employment_size=2.0,
                    building_cost_gold=300.0,
                    input_gold=2.0,
                    building_modifiers=(
                        EvaluatedBuildingModifier(
                            name="local_market_access",
                            amount=0.015,
                            per_building_gold=0.00005,
                            per_maintenance_gold=0.0075,
                            per_1k=0.0075,
                        ),
                    ),
                ),
            )
        )

    monkeypatch.setattr(workflow, "evaluate_building_blueprint_data", fake_evaluate)

    result = evaluate_blueprint_ratios(config, building="pp_test_ratios")

    assert result.startswith("building")
    assert "modifier ratios" not in result
    assert "building       value  build  maint  pop" in result
    assert "test_building  0.015  300    2      2" in result
    assert "modifier" in result
    assert "building       tag   method" not in result
    assert "test_building" in result
    assert "local_market_access" in result
    assert "0.00005" in result
    assert "other_building" not in result
    assert blueprint.name not in result



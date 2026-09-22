import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

from eu5_mod_orchestrator.adapters.parser import (
    export_parser_facts,
    export_savegame,
    global_building_unlock_ages_from_rows,
    global_unlock_ages_from_rows,
    load_food_cost_context,
    load_script_values,
    raw_material_goods_from_rows,
    script_values_from_text,
)


class FakeTable:
    def __init__(self, name: str) -> None:
        self.name = name

    def write_parquet(self, path: Path) -> None:
        path.write_text(self.name, encoding="utf-8")


def test_export_parser_facts_writes_tables_and_explorer(tmp_path: Path, monkeypatch) -> None:
    data = SimpleNamespace(
        advancements=FakeTable("advancements"),
        pop_types=FakeTable("pop_types"),
        goods=FakeTable("goods"),
        goods_summary=FakeTable("goods_summary"),
        ages=FakeTable("ages"),
        buildings=FakeTable("buildings"),
        production_methods=FakeTable("production_methods"),
        defines=FakeTable("defines"),
        food_price_scenarios=FakeTable("food_price_scenarios"),
        good_output_modifier_scenarios=FakeTable("good_output_modifier_scenarios"),
        fixed_good_prices=FakeTable("fixed_good_prices"),
        pop_food_costs=FakeTable("pop_food_costs"),
        unemployed_peasant_food_balance=FakeTable("unemployed_peasant_food_balance"),
        building_worker_food_costs=FakeTable("building_worker_food_costs"),
        production_method_food_costs=FakeTable("production_method_food_costs"),
        goods_flow_nodes=FakeTable("goods_flow_nodes"),
        goods_flow_edges=FakeTable("goods_flow_edges"),
    )
    calls = {}

    def fake_load_eu5_data(**kwargs):
        calls["load"] = kwargs
        return data

    def fake_write_goods_flow_explorer_html(path: Path, **kwargs) -> Path:
        calls["explorer"] = kwargs
        path.write_text("<html></html>", encoding="utf-8")
        return path

    eu5gameparser = ModuleType("eu5gameparser")
    domain = ModuleType("eu5gameparser.domain")
    eu5 = ModuleType("eu5gameparser.domain.eu5")
    graphs = ModuleType("eu5gameparser.graphs")
    goods_flow = ModuleType("eu5gameparser.graphs.goods_flow")
    eu5.load_eu5_data = fake_load_eu5_data
    goods_flow.write_goods_flow_explorer_html = fake_write_goods_flow_explorer_html

    monkeypatch.setitem(sys.modules, "eu5gameparser", eu5gameparser)
    monkeypatch.setitem(sys.modules, "eu5gameparser.domain", domain)
    monkeypatch.setitem(sys.modules, "eu5gameparser.domain.eu5", eu5)
    monkeypatch.setitem(sys.modules, "eu5gameparser.graphs", graphs)
    monkeypatch.setitem(sys.modules, "eu5gameparser.graphs.goods_flow", goods_flow)

    data_dir = tmp_path / "artifacts" / "data" / "buildings"
    graph_dir = tmp_path / "graphs"

    result = export_parser_facts(
        data_dir,
        graph_dir,
        profile="foundations",
        load_order_path=tmp_path / "foundations.load_order.toml",
    )

    for name in (
        "advancements",
        "pop_types",
        "goods",
        "goods_summary",
        "ages",
        "buildings",
        "production_methods",
        "defines",
        "food_price_scenarios",
        "good_output_modifier_scenarios",
        "fixed_good_prices",
        "pop_food_costs",
        "unemployed_peasant_food_balance",
        "building_worker_food_costs",
        "production_method_food_costs",
        "goods_flow_nodes",
        "goods_flow_edges",
    ):
        assert (data_dir / f"{name}.parquet").exists()
    assert (graph_dir / "goods_flow_explorer.html").exists()
    assert calls["load"]["profile"] == "foundations"
    assert calls["explorer"]["eu5_data"] is data
    assert str(data_dir) in result
    assert str(graph_dir / "goods_flow_explorer.html") in result


def test_load_food_cost_context_uses_parser_pop_food_costs(tmp_path: Path, monkeypatch) -> None:
    class FakeRows:
        def __init__(self, rows) -> None:
            self.rows = rows

        def to_dicts(self):
            return self.rows

    pop_food_costs = FakeRows(
        [
            {
                "pop_type": "laborers",
                "scenario": "cheap_50",
                "food_consumption_cost_gold": 0.1,
            },
            {
                "pop_type": "laborers",
                "scenario": "base_100",
                "food_consumption_cost_gold": 0.2,
            },
            {
                "pop_type": "laborers",
                "scenario": "expensive_150",
                "food_consumption_cost_gold": 0.3,
            },
        ]
    )
    output_modifiers = FakeRows(
        [
            {
                "good": "food_revenue",
                "scenario": "base_100",
                "output_modifier": 0.0,
                "output_multiplier": 1.0,
            }
        ]
    )
    fixed_prices = FakeRows(
        [
            {
                "good": "food_revenue",
                "age": "age_1_traditions",
                "default_market_price": 1.2,
                "price_stability": 0.1,
                "fixed_price": 0.12,
            }
        ]
    )
    calls = {}

    def fake_load_food_economics_data(**kwargs):
        calls["load"] = kwargs
        return SimpleNamespace(
            pop_food_costs=pop_food_costs,
            good_output_modifier_scenarios=output_modifiers,
            fixed_good_prices=fixed_prices,
        )

    eu5gameparser = ModuleType("eu5gameparser")
    domain = ModuleType("eu5gameparser.domain")
    food_economics = ModuleType("eu5gameparser.domain.food_economics")
    food_economics.load_food_economics_data = fake_load_food_economics_data

    monkeypatch.setitem(sys.modules, "eu5gameparser", eu5gameparser)
    monkeypatch.setitem(sys.modules, "eu5gameparser.domain", domain)
    monkeypatch.setitem(sys.modules, "eu5gameparser.domain.food_economics", food_economics)

    context = load_food_cost_context(
        profile="foundations",
        load_order_path=tmp_path / "foundations.load_order.toml",
    )

    assert calls["load"] == {
        "profile": "foundations",
        "load_order_path": tmp_path / "foundations.load_order.toml",
    }
    assert context.pop_cost("laborers", "base_100").food_consumption_cost_gold == 0.2
    assert context.output_modifier("food_revenue", "base_100").output_multiplier == 1.0
    assert context.fixed_price("food_revenue").fixed_price == 0.12


def test_export_savegame_writes_tables_and_explorer(tmp_path: Path, monkeypatch) -> None:
    class FakeTables:
        def as_dict(self):
            return {}

    calls = {}

    def fake_write_savegame_parquet(output_dir: Path, **kwargs):
        calls["parquet"] = (output_dir, kwargs)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "save_metadata.parquet").write_text("metadata", encoding="utf-8")
        return FakeTables()

    def fake_write_savegame_explorer_html(tables, path: Path) -> Path:
        calls["explorer"] = (tables, path)
        path.write_text("<html></html>", encoding="utf-8")
        return path

    eu5gameparser = ModuleType("eu5gameparser")
    savegame = ModuleType("eu5gameparser.savegame")
    savegame.write_savegame_parquet = fake_write_savegame_parquet
    savegame.write_savegame_explorer_html = fake_write_savegame_explorer_html

    monkeypatch.setitem(sys.modules, "eu5gameparser", eu5gameparser)
    monkeypatch.setitem(sys.modules, "eu5gameparser.savegame", savegame)

    data_dir = tmp_path / "artifacts" / "data" / "savegame"
    graph_dir = tmp_path / "graphs"
    result = export_savegame(
        data_dir,
        graph_dir,
        profile="foundations",
        load_order_path=tmp_path / "foundations.load_order.toml",
        save_path=tmp_path / "save.eu5",
        save_dir=tmp_path / "saves",
        force_rakaly=True,
    )

    assert (data_dir / "save_metadata.parquet").exists()
    assert (graph_dir / "savegame_explorer.html").exists()
    assert calls["parquet"][0] == data_dir
    assert calls["parquet"][1]["profile"] == "foundations"
    assert calls["parquet"][1]["save_path"] == tmp_path / "save.eu5"
    assert calls["parquet"][1]["save_dir"] == tmp_path / "saves"
    assert calls["parquet"][1]["force_rakaly"] is True
    assert str(data_dir) in result
    assert str(graph_dir / "savegame_explorer.html") in result


def test_global_unlock_ages_filter_potential_and_choose_earliest() -> None:
    rows = [
        {
            "age": "age_4_reformation",
            "has_potential": False,
            "unlock_production_method": ["pp_method"],
        },
        {
            "age": "age_2_renaissance",
            "has_potential": True,
            "unlock_production_method": ["pp_method", "pp_gated"],
        },
        {
            "age": "age_3_discovery",
            "has_potential": False,
            "unlock_production_method": ["pp_method"],
        },
    ]

    assert global_unlock_ages_from_rows(
        rows,
        {
            "age_2_renaissance": 1,
            "age_3_discovery": 2,
            "age_4_reformation": 3,
        },
    ) == {"pp_method": "age_3_discovery"}


def test_global_building_unlock_ages_filter_potential_and_choose_earliest() -> None:
    rows = [
        {
            "age": "age_4_reformation",
            "has_potential": False,
            "unlock_building": ["pp_building"],
        },
        {
            "age": "age_2_renaissance",
            "has_potential": True,
            "unlock_building": ["pp_building", "pp_gated"],
        },
        {
            "age": "age_3_discovery",
            "has_potential": False,
            "unlock_building": ["pp_building"],
        },
    ]

    assert global_building_unlock_ages_from_rows(
        rows,
        {
            "age_2_renaissance": 1,
            "age_3_discovery": 2,
            "age_4_reformation": 3,
        },
    ) == {"pp_building": "age_3_discovery"}


def test_raw_material_goods_from_rows_filters_category() -> None:
    assert raw_material_goods_from_rows(
        [
            {"name": "iron", "category": "raw_material"},
            {"name": "tools", "category": "manufactured"},
            {"name": "coal", "category": "raw_material"},
        ]
    ) == {"iron", "coal"}


def test_script_values_from_text_reads_numeric_scalars() -> None:
    assert script_values_from_text(
        """
        rural_peasant_produce_employment = 1.0
        manpower_employment = 2
        ignored_block = { gold = 1 }
        negative_value = -0.25 # comment
        """
    ) == {
        "rural_peasant_produce_employment": 1.0,
        "manpower_employment": 2.0,
        "negative_value": -0.25,
    }


def test_load_script_values_uses_profile_load_order_with_later_layers_overriding(tmp_path: Path) -> None:
    vanilla_values = tmp_path / "vanilla" / "game" / "main_menu" / "common" / "script_values"
    mod_values = tmp_path / "mod" / "main_menu" / "common" / "script_values"
    vanilla_values.mkdir(parents=True)
    mod_values.mkdir(parents=True)
    (vanilla_values / "default_values.txt").write_text(
        """
        rural_peasant_produce_employment = 1.0
        manpower_employment = 1.0
        """,
        encoding="utf-8",
    )
    (mod_values / "override_values.txt").write_text(
        """
        manpower_employment = 2.0
        guild_employment = 3.0
        """,
        encoding="utf-8",
    )
    load_order = tmp_path / "constructor.load_order.toml"
    load_order.write_text(
        """
        [paths]
        vanilla_root = "vanilla"

        [[mods]]
        id = "constructor"
        name = "Constructor"
        root = "mod"

        [profiles]
        constructor = ["vanilla", "constructor"]
        """,
        encoding="utf-8",
    )

    assert load_script_values(profile="constructor", load_order_path=load_order) == {
        "rural_peasant_produce_employment": 1.0,
        "manpower_employment": 2.0,
        "guild_employment": 3.0,
    }

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

from eu5_mod_orchestrator.adapters.parser import export_parser_facts, export_savegame


class FakeTable:
    def __init__(self, name: str) -> None:
        self.name = name

    def write_parquet(self, path: Path) -> None:
        path.write_text(self.name, encoding="utf-8")


def test_export_parser_facts_writes_tables_and_explorer(tmp_path: Path, monkeypatch) -> None:
    data = SimpleNamespace(
        advancements=FakeTable("advancements"),
        goods=FakeTable("goods"),
        goods_summary=FakeTable("goods_summary"),
        buildings=FakeTable("buildings"),
        production_methods=FakeTable("production_methods"),
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
        "goods",
        "goods_summary",
        "buildings",
        "production_methods",
        "goods_flow_nodes",
        "goods_flow_edges",
    ):
        assert (data_dir / f"{name}.parquet").exists()
    assert (graph_dir / "goods_flow_explorer.html").exists()
    assert calls["load"]["profile"] == "foundations"
    assert calls["explorer"]["eu5_data"] is data
    assert str(data_dir) in result
    assert str(graph_dir / "goods_flow_explorer.html") in result


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

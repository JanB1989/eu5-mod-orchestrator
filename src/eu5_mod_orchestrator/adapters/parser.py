from __future__ import annotations

from pathlib import Path


def export_parser_facts(output_dir: Path, *, profile: str, load_order_path: Path | None) -> str:
    from eu5gameparser.domain.eu5 import load_eu5_data

    kwargs = {"profile": profile}
    if load_order_path is not None:
        kwargs["load_order_path"] = load_order_path
    data = load_eu5_data(**kwargs)

    output_dir.mkdir(parents=True, exist_ok=True)
    data.goods.write_parquet(output_dir / "goods.parquet")
    data.buildings.write_parquet(output_dir / "buildings.parquet")
    data.production_methods.write_parquet(output_dir / "production_methods.parquet")
    data.goods_flow_nodes.write_parquet(output_dir / "goods_flow_nodes.parquet")
    data.goods_flow_edges.write_parquet(output_dir / "goods_flow_edges.parquet")
    return f"exported parser facts to {output_dir}"


def validate_generated_mod(*, profile: str, load_order_path: Path | None) -> list[str]:
    from eu5gameparser.domain.buildings import load_building_data

    kwargs = {"profile": profile}
    if load_order_path is not None:
        kwargs["load_order_path"] = load_order_path
    data = load_building_data(**kwargs)

    issues: list[str] = []
    unresolved = data.unresolved_production_methods.height
    duplicates = data.duplicate_production_methods.height
    if unresolved:
        issues.append(f"unresolved production methods: {unresolved}")
    if duplicates:
        issues.append(f"duplicate production methods: {duplicates}")
    issues.extend(data.warnings)
    return issues

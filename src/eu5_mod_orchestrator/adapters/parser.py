from __future__ import annotations

from pathlib import Path
import re
import tempfile
import tomllib


def compare_mod_building_state(
    *,
    profile: str,
    load_order_path: Path,
    mod_id: str,
    reference_mod_root: Path,
    candidate_mod_root: Path,
) -> list[str]:
    reference_load_order = _temporary_load_order(load_order_path, mod_id, reference_mod_root)
    candidate_load_order = _temporary_load_order(load_order_path, mod_id, candidate_mod_root)
    try:
        return _compare_loaded_state(
            profile=profile,
            reference_load_order_path=reference_load_order,
            candidate_load_order_path=candidate_load_order,
        )
    finally:
        reference_load_order.unlink(missing_ok=True)
        candidate_load_order.unlink(missing_ok=True)


def export_parser_facts(
    data_dir: Path,
    graph_dir: Path,
    *,
    profile: str,
    load_order_path: Path | None,
) -> str:
    from eu5gameparser.domain.eu5 import load_eu5_data
    from eu5gameparser.graphs.goods_flow import write_goods_flow_explorer_html

    kwargs = {"profile": profile}
    if load_order_path is not None:
        kwargs["load_order_path"] = load_order_path
    data = load_eu5_data(**kwargs)

    data_dir.mkdir(parents=True, exist_ok=True)
    graph_dir.mkdir(parents=True, exist_ok=True)
    data.goods.write_parquet(data_dir / "goods.parquet")
    data.goods_summary.write_parquet(data_dir / "goods_summary.parquet")
    data.advancements.write_parquet(data_dir / "advancements.parquet")
    data.buildings.write_parquet(data_dir / "buildings.parquet")
    data.production_methods.write_parquet(data_dir / "production_methods.parquet")
    data.goods_flow_nodes.write_parquet(data_dir / "goods_flow_nodes.parquet")
    data.goods_flow_edges.write_parquet(data_dir / "goods_flow_edges.parquet")
    explorer_path = write_goods_flow_explorer_html(
        graph_dir / "goods_flow_explorer.html",
        profile=profile,
        load_order_path=load_order_path,
        eu5_data=data,
    )
    return f"exported parser facts to {data_dir}\nexplorer: {explorer_path}"


def load_balance_prices(
    *,
    profile: str,
    load_order_path: Path | None,
) -> dict[str, float]:
    from eu5gameparser.domain.goods import load_goods_data

    kwargs = {"profile": profile}
    if load_order_path is not None:
        kwargs["load_order_path"] = load_order_path
    goods_data = load_goods_data(**kwargs)
    return {
        row["name"]: row["default_market_price"]
        for row in goods_data.goods.to_dicts()
        if row["default_market_price"] is not None
    }


def load_raw_material_goods(
    *,
    profile: str,
    load_order_path: Path | None,
) -> set[str]:
    from eu5gameparser.domain.goods import load_goods_data

    kwargs = {"profile": profile}
    if load_order_path is not None:
        kwargs["load_order_path"] = load_order_path
    goods_data = load_goods_data(**kwargs)
    return raw_material_goods_from_rows(goods_data.goods.to_dicts())


def raw_material_goods_from_rows(rows: list[dict]) -> set[str]:
    return {str(row["name"]) for row in rows if row.get("category") == "raw_material"}


def load_script_values(
    *,
    profile: str,
    load_order_path: Path | None,
) -> dict[str, float]:
    if load_order_path is None:
        return {}
    raw = tomllib.loads(load_order_path.read_text(encoding="utf-8"))
    layer_roots = _profile_layer_roots(raw, profile, load_order_path.parent)
    values: dict[str, float] = {}
    for root in layer_roots:
        for path in _script_value_files(root):
            values.update(script_values_from_text(path.read_text(encoding="utf-8-sig")))
    return values


def script_values_from_text(text: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for match in re.finditer(
        r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(-?\d+(?:\.\d+)?)\s*(?:#.*)?$",
        text,
        flags=re.MULTILINE,
    ):
        values[match.group(1)] = float(match.group(2))
    return values


def load_global_unlock_ages(
    *,
    profile: str,
    load_order_path: Path | None,
) -> dict[str, str]:
    from eu5gameparser.domain.advancements import load_advancement_data
    from eu5gameparser.domain.availability import AGE_INDEX

    kwargs = {"profile": profile}
    if load_order_path is not None:
        kwargs["load_order_path"] = load_order_path
    advancement_data = load_advancement_data(**kwargs)
    return global_method_unlock_ages_from_rows(advancement_data.advancements.to_dicts(), AGE_INDEX)


def load_global_building_unlock_ages(
    *,
    profile: str,
    load_order_path: Path | None,
) -> dict[str, str]:
    from eu5gameparser.domain.advancements import load_advancement_data
    from eu5gameparser.domain.availability import AGE_INDEX

    kwargs = {"profile": profile}
    if load_order_path is not None:
        kwargs["load_order_path"] = load_order_path
    advancement_data = load_advancement_data(**kwargs)
    return global_building_unlock_ages_from_rows(advancement_data.advancements.to_dicts(), AGE_INDEX)


def global_unlock_ages_from_rows(rows: list[dict], age_index: dict[str, int]) -> dict[str, str]:
    return global_method_unlock_ages_from_rows(rows, age_index)


def global_method_unlock_ages_from_rows(rows: list[dict], age_index: dict[str, int]) -> dict[str, str]:
    return _global_unlock_ages_from_rows(rows, age_index, "unlock_production_method")


def global_building_unlock_ages_from_rows(rows: list[dict], age_index: dict[str, int]) -> dict[str, str]:
    return _global_unlock_ages_from_rows(rows, age_index, "unlock_building")


def _global_unlock_ages_from_rows(rows: list[dict], age_index: dict[str, int], field: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in rows:
        if row.get("has_potential"):
            continue
        age = row.get("age")
        if age is None:
            continue
        for unlocked in row.get(field) or []:
            current = result.get(unlocked)
            if current is None or age_index.get(age, 10_000) < age_index.get(current, 10_000):
                result[str(unlocked)] = str(age)
    return result


def export_savegame(
    data_dir: Path,
    graph_dir: Path,
    *,
    profile: str,
    load_order_path: Path | None,
    save_path: Path | None = None,
    save_dir: Path | None = None,
    force_rakaly: bool = False,
) -> str:
    from eu5gameparser.savegame import write_savegame_explorer_html, write_savegame_parquet

    data_dir.mkdir(parents=True, exist_ok=True)
    graph_dir.mkdir(parents=True, exist_ok=True)
    kwargs = {
        "profile": profile,
        "load_order_path": load_order_path,
        "save_path": save_path,
        "force_rakaly": force_rakaly,
    }
    if save_dir is not None:
        kwargs["save_dir"] = save_dir
    tables = write_savegame_parquet(data_dir, **kwargs)
    explorer_path = write_savegame_explorer_html(tables, graph_dir / "savegame_explorer.html")
    return f"exported savegame facts to {data_dir}\nexplorer: {explorer_path}"


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


def _compare_loaded_state(
    *,
    profile: str,
    reference_load_order_path: Path,
    candidate_load_order_path: Path,
) -> list[str]:
    from eu5gameparser.domain.advancements import load_advancement_data
    from eu5gameparser.domain.buildings import load_building_data

    reference_buildings = load_building_data(profile=profile, load_order_path=reference_load_order_path)
    candidate_buildings = load_building_data(profile=profile, load_order_path=candidate_load_order_path)
    reference_advancements = load_advancement_data(profile=profile, load_order_path=reference_load_order_path)
    candidate_advancements = load_advancement_data(profile=profile, load_order_path=candidate_load_order_path)

    errors: list[str] = []
    errors.extend(
        _compare_rows(
            "buildings",
            reference_buildings.buildings.select(
                ["name", "category", "pop_type", "employment_size", "max_levels", "possible_production_methods", "unique_production_method_groups", "source_mode"]
            ).to_dicts(),
            candidate_buildings.buildings.select(
                ["name", "category", "pop_type", "employment_size", "max_levels", "possible_production_methods", "unique_production_method_groups", "source_mode"]
            ).to_dicts(),
            key="name",
        )
    )
    errors.extend(
        _compare_rows(
            "production_methods",
            reference_buildings.production_methods.filter(
                reference_buildings.production_methods["source_kind"] != "generated_rgo"
            )
            .select(["name", "category", "produced", "output", "input_goods", "input_amounts", "no_upkeep", "building", "production_method_group_index"])
            .to_dicts(),
            candidate_buildings.production_methods.filter(
                candidate_buildings.production_methods["source_kind"] != "generated_rgo"
            )
            .select(["name", "category", "produced", "output", "input_goods", "input_amounts", "no_upkeep", "building", "production_method_group_index"])
            .to_dicts(),
            key="name",
        )
    )
    errors.extend(
        _compare_rows(
            "advancements",
            reference_advancements.advancements.select(
                ["name", "age", "icon", "requires", "unlock_production_method", "unlock_building", "source_mode"]
            ).to_dicts(),
            candidate_advancements.advancements.select(
                ["name", "age", "icon", "requires", "unlock_production_method", "unlock_building", "source_mode"]
            ).to_dicts(),
            key="name",
        )
    )
    return errors


def _compare_rows(kind: str, reference: list[dict], candidate: list[dict], *, key: str) -> list[str]:
    reference_by_key = {str(row[key]): row for row in reference}
    candidate_by_key = {str(row[key]): row for row in candidate}
    errors: list[str] = []
    missing = sorted(set(reference_by_key) - set(candidate_by_key))
    extra = sorted(set(candidate_by_key) - set(reference_by_key))
    if missing:
        errors.append(f"{kind}: missing {len(missing)} entries: {', '.join(missing[:20])}")
    if extra:
        errors.append(f"{kind}: extra {len(extra)} entries: {', '.join(extra[:20])}")
    for item in sorted(set(reference_by_key) & set(candidate_by_key)):
        if reference_by_key[item] != candidate_by_key[item]:
            errors.append(f"{kind}: different entry {item}")
            if len(errors) >= 50:
                break
    return errors


def _temporary_load_order(load_order_path: Path, mod_id: str, mod_root: Path) -> Path:
    raw = tomllib.loads(load_order_path.read_text(encoding="utf-8"))
    for mod in raw.get("mods", []):
        if str(mod.get("id")) == mod_id:
            mod["root"] = str(mod_root)
            break
    else:
        raise ValueError(f"Mod id {mod_id!r} was not found in {load_order_path}.")
    handle = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False, encoding="utf-8")
    with handle:
        handle.write(_toml_load_order(raw))
    return Path(handle.name)


def _profile_layer_roots(raw: dict, profile: str, base_dir: Path) -> list[Path]:
    paths = raw.get("paths", {})
    vanilla_root_raw = paths.get("vanilla_root")
    mods = {str(mod.get("id")): mod for mod in raw.get("mods", [])}
    profiles = raw.get("profiles", {})
    layers = profiles.get(profile)
    if layers is None:
        layers = ["vanilla"]
    roots: list[Path] = []
    for layer in layers:
        layer_id = str(layer)
        if layer_id == "vanilla":
            if vanilla_root_raw:
                roots.append(_load_order_path(base_dir, str(vanilla_root_raw)) / "game")
            continue
        mod = mods.get(layer_id)
        if mod is None:
            continue
        roots.append(_load_order_path(base_dir, str(mod["root"])))
    return roots


def _script_value_files(root: Path) -> list[Path]:
    candidates = [
        root / "main_menu" / "common" / "script_values",
        root / "game" / "main_menu" / "common" / "script_values",
    ]
    files: list[Path] = []
    for directory in candidates:
        if directory.exists():
            files.extend(sorted(directory.glob("*.txt")))
    return files


def _load_order_path(base_dir: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _toml_load_order(raw: dict) -> str:
    lines: list[str] = []
    paths = raw.get("paths", {})
    lines.append("[paths]")
    lines.append(f'vanilla_root = "{_toml_string(str(paths.get("vanilla_root", "")))}"')
    lines.append("")
    for mod in raw.get("mods", []):
        lines.append("[[mods]]")
        lines.append(f'id = "{_toml_string(str(mod["id"]))}"')
        lines.append(f'name = "{_toml_string(str(mod.get("name", mod["id"])))}"')
        lines.append(f'root = "{_toml_string(str(mod["root"]))}"')
        lines.append("")
    lines.append("[profiles]")
    for name, layers in raw.get("profiles", {}).items():
        rendered = ", ".join(f'"{_toml_string(str(layer))}"' for layer in layers)
        lines.append(f"{name} = [{rendered}]")
    lines.append("")
    return "\n".join(lines)


def _toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')

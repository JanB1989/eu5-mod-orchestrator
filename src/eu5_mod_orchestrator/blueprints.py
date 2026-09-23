from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import yaml

# libyaml loads the same data as the pure-Python loader, several times faster.
_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


class BlueprintError(ValueError):
    """Raised when a blueprint cannot be consumed by the rendering pipeline."""


SAFE_TAG = re.compile(r"^[a-z0-9_]+$")


def validate_blueprint_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        raw = yaml.load(stream, Loader=_YAML_LOADER)
    validate_blueprint(raw, source=path)
    return raw


def validate_blueprint(raw: Any, *, source: Path | str = "<memory>") -> None:
    if not isinstance(raw, dict):
        raise BlueprintError(f"{source}: blueprint root must be a mapping.")
    tag = _string(raw, "tag", "template", source)
    if not SAFE_TAG.fullmatch(tag):
        raise BlueprintError(f"{source}: template.tag must contain only lowercase letters, numbers, and underscores.")
    output_tag = raw.get("output_tag")
    if output_tag is not None:
        if not isinstance(output_tag, str) or not output_tag.strip():
            raise BlueprintError(f"{source}: template.output_tag must be a non-empty string.")
        if not SAFE_TAG.fullmatch(output_tag):
            raise BlueprintError(
                f"{source}: template.output_tag must contain only lowercase letters, numbers, and underscores."
            )
    if not path_stem_starts_with_tag(source, tag):
        raise BlueprintError(f"{source}: blueprint filename must start with tag {tag!r}.")
    version = raw.get("version", 1)
    if version not in (1, 2):
        raise BlueprintError(f"{source}: version must be 1 or 2.")

    required = ("building", "price", "localization", "icon") if version == 1 else ("building",)
    for section in required:
        if section not in raw:
            raise BlueprintError(f"{source}: missing required section {section!r}.")

    building = _mapping(raw["building"], "building", source)
    _string(building, "key", "building", source)
    _string(building, "body", "building", source)
    mode = str(building.get("mode", "CREATE")).upper()
    if mode not in {"CREATE", "REPLACE", "REPLACE_OR_CREATE", "TRY_REPLACE", "INJECT", "TRY_INJECT", "INJECT_OR_CREATE"}:
        raise BlueprintError(f"{source}: unsupported building.mode {mode!r}.")
    if "production_method_slots" in building:
        _validate_method_slots(building["production_method_slots"], source)

    if "price" in raw:
        price = _mapping(raw["price"], "price", source)
        _string(price, "key", "price", source)
        _string(price, "body", "price", source)
    if "prices" in raw:
        prices = raw["prices"]
        if not isinstance(prices, list):
            raise BlueprintError(f"{source}: prices must be a list.")
        for index, price in enumerate(prices):
            section = f"prices[{index}]"
            price = _mapping(price, section, source)
            _string(price, "key", section, source)
            _string(price, "body", section, source)

    localization = _mapping(raw.get("localization", {"entries": {}}), "localization", source)
    entries = _mapping(localization.get("entries", {}), "localization.entries", source)
    if version == 1 and not entries:
        raise BlueprintError(f"{source}: localization.entries must not be empty.")
    if "production_methods" in raw:
        methods = raw["production_methods"]
        if not isinstance(methods, list):
            raise BlueprintError(f"{source}: production_methods must be a list.")
        for index, method in enumerate(methods):
            section = f"production_methods[{index}]"
            method = _mapping(method, section, source)
            _string(method, "key", section, source)
            _string(method, "body", section, source)

    advancements = raw.get("advancements", [])
    if advancements is None:
        advancements = []
    if not isinstance(advancements, list):
        raise BlueprintError(f"{source}: advancements must be a list.")
    for index, advancement in enumerate(advancements):
        section = f"advancements[{index}]"
        advancement = _mapping(advancement, section, source)
        _string(advancement, "key", section, source)
        _string(advancement, "body", section, source)

    if "icon" in raw and raw["icon"] is not None:
        icon = _mapping(raw["icon"], "icon", source)
        if not isinstance(icon.get("source_png"), str) and not isinstance(icon.get("source_dds"), str):
            raise BlueprintError(f"{source}: icon.source_png or icon.source_dds must be set.")
        output_dds = _string(icon, "output_dds", "icon", source)
        if not output_dds.endswith(".dds"):
            raise BlueprintError(f"{source}: icon.output_dds must be a .dds file.")
        size = icon.get("size")
        if size != 512:
            raise BlueprintError(f"{source}: icon.size must be 512.")


def accepted_blueprint_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted([*directory.rglob("*.yml"), *directory.rglob("*.yaml")])


def _iter_manifest_entry_flags(
    enabled: Any,
    *,
    source: Path | str = "<memory>",
) -> list[tuple[str, bool]]:
    """Normalize buildings-manifest ``enabled`` into ``(path, is_enabled)`` pairs."""
    if enabled is None:
        return []
    if isinstance(enabled, list):
        entries: list[tuple[str, bool]] = []
        for index, item in enumerate(enabled):
            if isinstance(item, str):
                path = item.strip()
                if not path:
                    raise BlueprintError(f"{source}: enabled[{index}] must be a non-empty path.")
                entries.append((path, True))
                continue
            if isinstance(item, dict) and len(item) == 1:
                path_raw, flag = next(iter(item.items()))
                if not isinstance(path_raw, str) or not path_raw.strip():
                    raise BlueprintError(
                        f"{source}: enabled[{index}] toggle key must be a non-empty path."
                    )
                if not isinstance(flag, bool):
                    raise BlueprintError(
                        f"{source}: enabled[{index}] toggle for {path_raw!r} must be true or false."
                    )
                entries.append((path_raw.strip(), flag))
                continue
            raise BlueprintError(
                f"{source}: enabled[{index}] must be a path string or {{path: true|false}}."
            )
        return entries
    if isinstance(enabled, dict):
        entries = []
        for path_raw, flag in enabled.items():
            if not isinstance(path_raw, str) or not path_raw.strip():
                raise BlueprintError(f"{source}: enabled keys must be non-empty blueprint paths.")
            if not isinstance(flag, bool):
                raise BlueprintError(
                    f"{source}: enabled[{path_raw!r}] must be true or false, got {flag!r}."
                )
            entries.append((path_raw.strip(), flag))
        return entries
    raise BlueprintError(
        f"{source}: enabled must be a list of paths or a mapping of path -> true/false."
    )


def declared_manifest_entries(enabled: Any, *, source: Path | str = "<memory>") -> list[str]:
    """Return every relative blueprint path declared in a buildings manifest."""
    return [path for path, _flag in _iter_manifest_entry_flags(enabled, source=source)]


def enabled_manifest_entries(enabled: Any, *, source: Path | str = "<memory>") -> list[str]:
    """Return relative blueprint paths marked enabled in a buildings manifest.

    Accepts either:
    - a list of relative paths (legacy; every entry is treated as enabled)
    - a mapping of relative path -> bool (only ``true`` entries are enabled)
    """
    return [path for path, flag in _iter_manifest_entry_flags(enabled, source=source) if flag]


def manifest_blueprint_files(directory: Path, manifest_path: Path | None) -> list[Path]:
    if manifest_path is None or not manifest_path.exists():
        return accepted_blueprint_files(directory)
    with manifest_path.open("r", encoding="utf-8") as stream:
        raw = yaml.load(stream, Loader=_YAML_LOADER)
    if not isinstance(raw, dict):
        raise BlueprintError(f"{manifest_path}: manifest root must be a mapping.")
    return [
        (directory / item).resolve()
        for item in enabled_manifest_entries(raw.get("enabled", []), source=manifest_path)
    ]


def path_stem_starts_with_tag(source: Path | str, tag: str) -> bool:
    if isinstance(source, Path):
        return source.stem.startswith(tag)
    return True


def _validate_method_slots(value: Any, source: Path | str) -> None:
    if not isinstance(value, list):
        raise BlueprintError(f"{source}: building.production_method_slots must be a list.")
    for index, slot in enumerate(value):
        section = f"building.production_method_slots[{index}]"
        slot = _mapping(slot, section, source)
        methods = slot.get("methods")
        if not isinstance(methods, list) or not all(isinstance(method, str) for method in methods):
            raise BlueprintError(f"{source}: {section}.methods must be a list of strings.")


def _mapping(value: Any, name: str, source: Path | str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BlueprintError(f"{source}: {name} must be a mapping.")
    return value


def _string(mapping: dict[str, Any], key: str, section: str, source: Path | str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BlueprintError(f"{source}: {section}.{key} must be a non-empty string.")
    return value

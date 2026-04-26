from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class BlueprintError(ValueError):
    """Raised when a blueprint cannot be consumed by the rendering pipeline."""


def validate_blueprint_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)
    validate_blueprint(raw, source=path)
    return raw


def validate_blueprint(raw: Any, *, source: Path | str = "<memory>") -> None:
    if not isinstance(raw, dict):
        raise BlueprintError(f"{source}: blueprint root must be a mapping.")
    for section in ("building", "price", "localization", "icon"):
        if section not in raw:
            raise BlueprintError(f"{source}: missing required section {section!r}.")

    building = _mapping(raw["building"], "building", source)
    price = _mapping(raw["price"], "price", source)
    localization = _mapping(raw["localization"], "localization", source)
    icon = _mapping(raw["icon"], "icon", source)

    _string(building, "key", "building", source)
    _string(building, "body", "building", source)
    _string(price, "key", "price", source)
    _string(price, "body", "price", source)
    localization_file = _string(localization, "file", "localization", source)
    if not localization_file.endswith("_l_english.yml"):
        raise BlueprintError(f"{source}: localization.file must end with '_l_english.yml'.")
    entries = _mapping(localization.get("entries"), "localization.entries", source)
    if not entries:
        raise BlueprintError(f"{source}: localization.entries must not be empty.")

    _string(icon, "source_png", "icon", source)
    output_dds = _string(icon, "output_dds", "icon", source)
    if not output_dds.endswith(".dds"):
        raise BlueprintError(f"{source}: icon.output_dds must be a .dds file.")
    size = icon.get("size")
    if size != 512:
        raise BlueprintError(f"{source}: icon.size must be 512.")


def accepted_blueprint_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted([*directory.glob("*.yml"), *directory.glob("*.yaml")])


def _mapping(value: Any, name: str, source: Path | str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BlueprintError(f"{source}: {name} must be a mapping.")
    return value


def _string(mapping: dict[str, Any], key: str, section: str, source: Path | str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BlueprintError(f"{source}: {section}.{key} must be a non-empty string.")
    return value

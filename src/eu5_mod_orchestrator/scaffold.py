from __future__ import annotations

from pathlib import Path

from eu5_mod_orchestrator.config import ConfigError


def init_project(
    project_dir: Path,
    *,
    name: str,
    mod_name: str,
    vanilla_root: Path,
    force: bool = False,
) -> str:
    target = project_dir.resolve()
    if target.exists() and any(target.iterdir()) and not force:
        raise ConfigError(f"target directory is not empty: {target}")

    target.mkdir(parents=True, exist_ok=True)
    mod_root = target / "mod" / mod_name
    accepted_blueprints = target / "blueprints" / "accepted"
    scripts = target / "scripts"
    for path in (
        mod_root,
        accepted_blueprints,
        target / "artifacts" / "data" / "buildings",
        target / "artifacts" / "data" / "savegame",
        target / "graphs",
        target / "reports",
        scripts,
    ):
        path.mkdir(parents=True, exist_ok=True)

    config_stem = _slug(name)
    profile = config_stem.replace("-", "_")
    config_path = target / f"{config_stem}.toml"
    load_order_path = target / f"{config_stem}.load_order.toml"
    local_example_path = target / f"{config_stem}.local.toml.example"
    _write_if_missing_or_force(
        config_path,
        _project_toml(name, mod_name, profile, load_order_path.name),
        force=force,
    )
    _write_if_missing_or_force(
        load_order_path,
        _load_order_toml(name, mod_name, profile, vanilla_root),
        force=force,
    )
    _write_if_missing_or_force(local_example_path, _local_toml_example(mod_name), force=force)
    _write_if_missing_or_force(target / "pyproject.toml", _pyproject_toml(name), force=force)
    _write_if_missing_or_force(target / ".gitignore", _gitignore(), force=force)
    _write_if_missing_or_force(target / "README.md", _readme(name, config_path.name), force=force)
    _write_if_missing_or_force(scripts / "analyze.ps1", _analyze_script(config_path.name), force=force)
    _write_if_missing_or_force(scripts / "savegame.ps1", _savegame_script(config_path.name), force=force)

    return f"initialized EU5 mod workspace at {target}\nproject: {config_path}"


def _write_if_missing_or_force(path: Path, content: str, *, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _slug(value: str) -> str:
    result = "".join(char.lower() if char.isalnum() else "-" for char in value.strip())
    while "--" in result:
        result = result.replace("--", "-")
    return result.strip("-") or "eu5-project"


def _toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _project_toml(name: str, mod_name: str, profile: str, load_order_name: str) -> str:
    return f"""
[project]
name = "{_toml_string(name)}"
mod_root = "mod/{_toml_string(mod_name)}"

[artifacts]
root = "artifacts"
data = "artifacts/data"
buildings = "artifacts/data/buildings"
savegame = "artifacts/data/savegame"
graphs = "graphs"
reports = "reports"
accepted_blueprints = "blueprints/accepted"
generated_blueprints = "blueprints/generated"

[parser]
profile = "{_toml_string(profile)}"
load_order = "{_toml_string(load_order_name)}"

[building_outputs]
prefix = ""
building_types = "in_game/common/building_types/{{prefix}}{{tag}}.txt"
production_methods = "in_game/common/production_methods/{{prefix}}{{tag}}.txt"
prices = "in_game/common/prices/{{prefix}}{{tag}}.txt"
advances = "in_game/common/advances/{{prefix}}{{tag}}.txt"
localization = "main_menu/localization/english/{{prefix}}{{tag}}_l_english.yml"
icons = "in_game/gfx/interface/icons/buildings"
""".lstrip()


def _load_order_toml(name: str, mod_name: str, profile: str, vanilla_root: Path) -> str:
    return f"""
[paths]
vanilla_root = "{_toml_string(str(vanilla_root))}"

[[mods]]
id = "{_toml_string(profile)}"
name = "{_toml_string(name)}"
root = "mod/{_toml_string(mod_name)}"

[profiles]
vanilla = ["vanilla"]
{profile} = ["vanilla", "{_toml_string(profile)}"]
""".lstrip()


def _local_toml_example(mod_name: str) -> str:
    return f"""
# Copy this to the matching .local.toml file and edit the target for deployment.
[deploy]
target = "C:/Users/<you>/Documents/Paradox Interactive/Europa Universalis V/mod/{_toml_string(mod_name)}"
""".lstrip()


def _pyproject_toml(name: str) -> str:
    return f"""
[project]
name = "{_toml_string(_slug(name))}"
version = "0.1.0"
description = "EU5 mod orchestration workspace."
requires-python = ">=3.13"
dependencies = [
    "eu5-building-pipeline",
    "eu5-mod-orchestrator",
    "eu5gameparser",
    "prosper-or-perish-labeling-pipeline",
]

[dependency-groups]
dev = [
    "pytest>=9.0.3",
]

[tool.uv]
package = false

[tool.uv.sources]
eu5-building-pipeline = {{ path = "../ProsperOrPerishBuildingPipeline", editable = true }}
eu5-mod-orchestrator = {{ path = "../Eu5ModOrchestrator", editable = true }}
eu5gameparser = {{ path = "../Eu5GameParser", editable = true }}
prosper-or-perish-labeling-pipeline = {{ path = "../ProsperOrPerishLabelingPipeline", editable = true }}
""".lstrip()


def _gitignore() -> str:
    return """
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
build/
dist/
*.egg-info/

artifacts/
graphs/
reports/
blueprints/generated/
*.local.toml
.env
.env.*
""".lstrip()


def _readme(name: str, config_name: str) -> str:
    return f"""
# {name}

EU5 mod orchestration workspace.

## Setup

```powershell
uv sync --dev
uv run eu5-orchestrator inspect --project {config_name}
```

This workspace expects sibling clones of `Eu5GameParser`, `Eu5ModOrchestrator`,
`ProsperOrPerishBuildingPipeline`, and `ProsperOrPerishLabelingPipeline` beside this directory.

Edit the generated load-order TOML so `vanilla_root` points at your EU5 install and the mod
entry points at your local mod copy under `mod/`.

## Analyze

```powershell
uv run eu5-orchestrator analyze --project {config_name}
uv run eu5-orchestrator savegame --project {config_name}
```

Static parquet tables are written to `artifacts/data/buildings`, savegame parquet tables are
written to `artifacts/data/savegame`, and HTML graphs are written to `graphs`.

## Deploy

Copy the generated `.local.toml.example` to `.local.toml`, set `[deploy].target`, then run:

```powershell
uv run eu5-orchestrator deploy --project {config_name} --clean
```
""".lstrip()


def _analyze_script(config_name: str) -> str:
    return f"""
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {{
    uv run eu5-orchestrator analyze --project {config_name}
}} finally {{
    Pop-Location
}}
""".lstrip()


def _savegame_script(config_name: str) -> str:
    return f"""
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {{
    uv run eu5-orchestrator savegame --project {config_name}
}} finally {{
    Pop-Location
}}
""".lstrip()

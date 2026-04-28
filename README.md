# EU5 Mod Orchestrator

Reusable workflow engine for Europa Universalis V mod projects.

The orchestrator coordinates parser exports, savegame graph exports, blueprint rendering,
validation, and deploys without making those packages depend on any specific mod.

## Create A Workspace

```powershell
uv run eu5-orchestrator init C:/Development/my-eu5-mod --name "My EU5 Mod" --mod-name "My EU5 Mod" --vanilla-root "C:/Games/steamapps/common/Europa Universalis V"
```

The scaffold creates a project TOML, load-order TOML, scripts, `mod/`, `blueprints/accepted`,
`artifacts/data`, `graphs`, and README files. It refuses non-empty target directories unless
`--force` is passed.
Generated workspaces expect sibling clones named `eu5-game-parser`, `eu5-mod-orchestrator`,
and `eu5-building-pipeline`.

## Core Commands

```powershell
uv run eu5-orchestrator inspect --project project.toml
uv run eu5-orchestrator analyze --project project.toml
uv run eu5-orchestrator savegame --project project.toml
uv run eu5-orchestrator render --project project.toml --dry-run
uv run eu5-orchestrator validate --project project.toml
uv run eu5-orchestrator build --project project.toml
uv run eu5-orchestrator deploy --project project.toml --clean
```

`analyze` exports static parser tables to `artifacts/data/buildings` and the goods-flow graph to
`graphs/goods_flow_explorer.html`.

`savegame` exports market/savegame tables to `artifacts/data/savegame` and the savegame explorer to
`graphs/savegame_explorer.html`. Pass `--save` or `--save-dir` to select a save explicitly.

## Project Config

A project supplies a TOML config with:

- `[project]` for the workspace name and local mod copy.
- `[artifacts]` for generated data and graph directories.
- `[parser]` for the parser profile and load-order TOML.
- `[building_outputs]` for generated mod file layout.
- optional ignored `.local.toml` for machine-local deploy targets.

Generated parser exports, generated blueprints, reports, and graph HTML files should stay out of
Git. Commit reusable recipes, accepted blueprints, fixtures, docs, and tests.

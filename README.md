# EU5 Mod Orchestrator

Reusable workflow engine for Europa Universalis V mod projects.

The package coordinates independent parser, labeling, and rendering packages without making those
packages depend on any specific mod. Concrete mod projects provide a TOML config, accepted
blueprints, and output paths.

## Commands

```powershell
uv run eu5-orchestrator inspect --project ../ProsperOrPerishFoundations/foundations.toml
uv run eu5-orchestrator analyze --project ../ProsperOrPerishFoundations/foundations.toml
uv run eu5-orchestrator render --project ../ProsperOrPerishFoundations/foundations.toml --dry-run
uv run eu5-orchestrator validate --project ../ProsperOrPerishFoundations/foundations.toml
uv run eu5-orchestrator build --project ../ProsperOrPerishFoundations/foundations.toml
```

Generated parser exports, generated blueprints, reports, and mod output folders should stay out of
Git. Commit only reusable recipes, accepted blueprints, fixtures, and tests.

from __future__ import annotations

from pathlib import Path

from eu5_mod_orchestrator.config import OrchestratorConfig


def ensure_artifact_dirs(config: OrchestratorConfig) -> list[Path]:
    paths = [
        config.artifact_dir,
        config.parser_artifact_dir,
        config.reports_dir,
        config.generated_blueprints_dir,
        config.accepted_blueprints_dir,
        config.mod_root,
    ]
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
    return paths

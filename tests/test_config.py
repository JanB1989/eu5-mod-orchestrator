from pathlib import Path

from eu5_mod_orchestrator.artifacts import ensure_artifact_dirs
from eu5_mod_orchestrator.config import load_project_config


def test_load_project_config_resolves_relative_paths(tmp_path: Path) -> None:
    config_path = tmp_path / "foundations.toml"
    config_path.write_text(
        """
[project]
name = "Foundations"
mod_root = "mod/Foundations"

[artifacts]
root = "artifacts"
accepted_blueprints = "blueprints/accepted"
generated_blueprints = "blueprints/generated"

[parser]
profile = "foundations"
load_order = "../Eu5GameParser/eu5_load_order.toml"

[dependencies]
parser = "../Eu5GameParser"
""".strip(),
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.name == "Foundations"
    assert config.mod_root == tmp_path / "mod" / "Foundations"
    assert config.dependencies["parser"] == tmp_path.parent / "Eu5GameParser"


def test_ensure_artifact_dirs_creates_expected_directories(tmp_path: Path) -> None:
    config_path = tmp_path / "foundations.toml"
    config_path.write_text(
        """
[project]
name = "Foundations"
mod_root = "mod/Foundations"
""".strip(),
        encoding="utf-8",
    )

    config = load_project_config(config_path)
    paths = ensure_artifact_dirs(config)

    assert all(path.exists() for path in paths)

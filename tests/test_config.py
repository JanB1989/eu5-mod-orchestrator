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

[building_outputs]
building_types = "in_game/common/building_types/zz_foundation_{tag}.txt"

[dependencies]
parser = "../Eu5GameParser"
""".strip(),
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.name == "Foundations"
    assert config.mod_root == tmp_path / "mod" / "Foundations"
    assert config.deploy_target is None
    assert config.building_outputs.prefix == ""
    assert (
        config.building_outputs.building_types
        == "in_game/common/building_types/zz_foundation_{tag}.txt"
    )
    assert config.building_outputs.production_methods == "in_game/common/production_methods/{tag}.txt"
    assert config.building_outputs.icons == "in_game/gfx/interface/icons/buildings"
    assert config.dependencies["parser"] == tmp_path.parent / "Eu5GameParser"
    assert config.data_artifact_dir == tmp_path / "artifacts" / "data"
    assert config.building_artifact_dir == tmp_path / "artifacts" / "data" / "buildings"
    assert config.savegame_artifact_dir == tmp_path / "artifacts" / "data" / "savegame"
    assert config.graph_dir == tmp_path / "graphs"
    assert config.parser_artifact_dir == config.building_artifact_dir


def test_load_project_config_accepts_explicit_artifact_layout(tmp_path: Path) -> None:
    config_path = tmp_path / "foundations.toml"
    config_path.write_text(
        """
[project]
name = "Foundations"
mod_root = "mod/Foundations"

[artifacts]
data = "out/data"
buildings = "out/data/static"
savegame = "out/data/saves"
graphs = "out/graphs"
""".strip(),
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.data_artifact_dir == tmp_path / "out" / "data"
    assert config.building_artifact_dir == tmp_path / "out" / "data" / "static"
    assert config.savegame_artifact_dir == tmp_path / "out" / "data" / "saves"
    assert config.graph_dir == tmp_path / "out" / "graphs"


def test_load_project_config_keeps_legacy_parser_artifact_path(tmp_path: Path) -> None:
    config_path = tmp_path / "foundations.toml"
    config_path.write_text(
        """
[project]
name = "Foundations"
mod_root = "mod/Foundations"

[artifacts]
parser = "artifacts/parser"
""".strip(),
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.building_artifact_dir == tmp_path / "artifacts" / "parser"
    assert config.parser_artifact_dir == config.building_artifact_dir


def test_load_project_config_merges_local_deploy_target(tmp_path: Path) -> None:
    config_path = tmp_path / "foundations.toml"
    config_path.write_text(
        """
[project]
name = "Foundations"
mod_root = "mod/Foundations"
""".strip(),
        encoding="utf-8",
    )
    local_config_path = tmp_path / "foundations.local.toml"
    local_config_path.write_text(
        """
[deploy]
target = "local/Foundations"
""".strip(),
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.deploy_target == tmp_path / "local" / "Foundations"


def test_load_project_config_resolves_absolute_windows_deploy_target(tmp_path: Path) -> None:
    config_path = tmp_path / "foundations.toml"
    config_path.write_text(
        """
[project]
name = "Foundations"
mod_root = "mod/Foundations"

[deploy]
target = "C:/Users/Anwender/Documents/Paradox Interactive/Europa Universalis V/mod/Foundations"
""".strip(),
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.deploy_target == Path(
        "C:/Users/Anwender/Documents/Paradox Interactive/Europa Universalis V/mod/Foundations"
    )


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
    assert config.building_artifact_dir.exists()
    assert config.savegame_artifact_dir.exists()
    assert config.graph_dir.exists()

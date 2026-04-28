from pathlib import Path

import pytest
from typer.testing import CliRunner

from eu5_mod_orchestrator.cli import app
from eu5_mod_orchestrator.config import ConfigError
from eu5_mod_orchestrator.scaffold import init_project


def test_init_project_creates_reusable_workspace(tmp_path: Path) -> None:
    target = tmp_path / "MyMod"

    summary = init_project(
        target,
        name="My Mod",
        mod_name="My Mod",
        vanilla_root=Path("C:/Games/Europa Universalis V"),
    )

    assert "initialized EU5 mod workspace" in summary
    assert (target / "my-mod.toml").exists()
    assert (target / "my-mod.load_order.toml").exists()
    assert (target / "my-mod.local.toml.example").exists()
    assert (target / "pyproject.toml").exists()
    assert (target / "mod" / "My Mod").is_dir()
    assert (target / "blueprints" / "accepted").is_dir()
    assert (target / "artifacts" / "data" / "buildings").is_dir()
    assert (target / "artifacts" / "data" / "savegame").is_dir()
    assert (target / "graphs").is_dir()
    assert "artifacts/" in (target / ".gitignore").read_text(encoding="utf-8")
    assert "graphs/" in (target / ".gitignore").read_text(encoding="utf-8")
    assert "savegame" in (target / "README.md").read_text(encoding="utf-8")
    pyproject = (target / "pyproject.toml").read_text(encoding="utf-8")
    assert 'eu5-mod-orchestrator = { path = "../eu5-mod-orchestrator", editable = true }' in pyproject
    assert 'eu5gameparser = { path = "../eu5-game-parser", editable = true }' in pyproject
    assert "package = false" in pyproject


def test_init_project_refuses_non_empty_directory_without_force(tmp_path: Path) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    (target / "file.txt").write_text("existing\n", encoding="utf-8")

    with pytest.raises(ConfigError):
        init_project(
            target,
            name="My Mod",
            mod_name="My Mod",
            vanilla_root=Path("C:/Games/Europa Universalis V"),
        )


def test_init_project_force_allows_non_empty_directory(tmp_path: Path) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    (target / "file.txt").write_text("existing\n", encoding="utf-8")

    init_project(
        target,
        name="My Mod",
        mod_name="My Mod",
        vanilla_root=Path("C:/Games/Europa Universalis V"),
        force=True,
    )

    assert (target / "file.txt").read_text(encoding="utf-8") == "existing\n"
    assert (target / "my-mod.toml").exists()


def test_init_cli_creates_workspace(tmp_path: Path) -> None:
    target = tmp_path / "cli-project"
    result = CliRunner().invoke(
        app,
        [
            "init",
            str(target),
            "--name",
            "CLI Project",
            "--mod-name",
            "CLI Project",
            "--vanilla-root",
            "C:/Games/Europa Universalis V",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert (target / "cli-project.toml").exists()

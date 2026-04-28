from pathlib import Path

import pytest

from eu5_mod_orchestrator.config import load_project_config
from eu5_mod_orchestrator.deploy import DeployError, deploy


def _config(tmp_path: Path, deploy_target: str = "deployed/Foundations"):
    config_path = tmp_path / "foundations.toml"
    config_path.write_text(
        f"""
[project]
name = "Foundations"
mod_root = "mod/Foundations"

[deploy]
target = "{deploy_target}"
""".strip(),
        encoding="utf-8",
    )
    config = load_project_config(config_path)
    config.mod_root.mkdir(parents=True)
    return config


def test_deploy_dry_run_reports_planned_copies_without_writing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    source_file = config.mod_root / "in_game" / "common" / "building_types" / "market.txt"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("market = {}\n", encoding="utf-8")

    result = deploy(config, dry_run=True)

    assert result.planned_copies == [
        config.deploy_target / "in_game" / "common" / "building_types" / "market.txt"
    ]
    assert result.copied == []
    assert not config.deploy_target.exists()


def test_deploy_copies_nested_files(tmp_path: Path) -> None:
    config = _config(tmp_path)
    source_file = config.mod_root / "main_menu" / "localization" / "english" / "foundations.yml"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("l_english:\n", encoding="utf-8")

    result = deploy(config)

    target_file = config.deploy_target / "main_menu" / "localization" / "english" / "foundations.yml"
    assert target_file.read_text(encoding="utf-8") == "l_english:\n"
    assert result.copied == [target_file]


def test_deploy_creates_target_when_source_is_empty(tmp_path: Path) -> None:
    config = _config(tmp_path)

    result = deploy(config)

    assert config.deploy_target.is_dir()
    assert result.copied == []


def test_deploy_preserves_empty_source_directories(tmp_path: Path) -> None:
    config = _config(tmp_path)
    (config.mod_root / "loading_screen").mkdir(parents=True)

    result = deploy(config)

    assert (config.deploy_target / "loading_screen").is_dir()
    assert result.copied == []


def test_deploy_refuses_same_source_and_target(tmp_path: Path) -> None:
    config = _config(tmp_path, deploy_target="mod/Foundations")

    with pytest.raises(DeployError, match="must be different"):
        deploy(config)


def test_deploy_refuses_unsafe_clean_targets(tmp_path: Path) -> None:
    config = _config(tmp_path, deploy_target="mod")
    (config.mod_root / "file.txt").write_text("content\n", encoding="utf-8")

    with pytest.raises(DeployError, match="broad deploy target"):
        deploy(config, clean=True)


def test_deploy_clean_removes_only_stale_files_under_target(tmp_path: Path) -> None:
    config = _config(tmp_path)
    source_file = config.mod_root / "kept.txt"
    source_file.write_text("new\n", encoding="utf-8")
    stale_file = config.deploy_target / "old" / "stale.txt"
    stale_file.parent.mkdir(parents=True)
    stale_file.write_text("old\n", encoding="utf-8")
    sibling_file = config.deploy_target.parent / "sibling.txt"
    sibling_file.write_text("outside\n", encoding="utf-8")

    result = deploy(config, clean=True)

    assert (config.deploy_target / "kept.txt").read_text(encoding="utf-8") == "new\n"
    assert stale_file in result.deleted
    assert not stale_file.exists()
    assert sibling_file.read_text(encoding="utf-8") == "outside\n"

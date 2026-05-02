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
load_order = "../eu5-game-parser/eu5_load_order.toml"

[building_outputs]
building_types = "in_game/common/building_types/zz_foundation_{tag}.txt"

[dependencies]
parser = "../eu5-game-parser"
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
    assert config.dependencies["parser"] == tmp_path.parent / "eu5-game-parser"
    assert config.data_artifact_dir == tmp_path / "artifacts" / "data"
    assert config.building_artifact_dir == tmp_path / "artifacts" / "data" / "buildings"
    assert config.savegame_artifact_dir == tmp_path / "artifacts" / "data" / "savegame"
    assert config.graph_dir == tmp_path / "graphs"
    assert config.parser_artifact_dir == config.building_artifact_dir
    assert config.labeling is None
    assert config.blueprint_evaluation.raw_input_efficiency_per_good == 0.05


def test_load_project_config_accepts_labeling_config(tmp_path: Path) -> None:
    config_path = tmp_path / "foundations.toml"
    config_path.write_text(
        """
[project]
name = "Foundations"
mod_root = "mod/Foundations"

[labeling]
enabled = true
config = "../labeling/mod_injector_config.yaml"
modifier_prefix = "pp"
generated_label = "Prosper or Perish"
managed_write_mode = "mod_root"
""".strip(),
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.labeling is not None
    assert config.labeling.enabled is True
    assert config.labeling.config_path == tmp_path.parent / "labeling" / "mod_injector_config.yaml"
    assert config.labeling.modifier_prefix == "pp"
    assert config.labeling.generated_label == "Prosper or Perish"
    assert config.labeling.managed_write_mode == "mod_root"


def test_load_project_config_accepts_population_capacity_config(tmp_path: Path) -> None:
    config_path = tmp_path / "foundations.toml"
    config_path.write_text(
        """
[project]
name = "Foundations"
mod_root = "mod/Foundations"

[population_capacity]
enabled = true
config = "../population-capacity/population_capacity.toml"
generated_label = "Prosper or Perish"
managed_write_mode = "mod_root"
""".strip(),
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    assert config.population_capacity is not None
    assert config.population_capacity.enabled is True
    assert (
        config.population_capacity.config_path
        == tmp_path.parent / "population-capacity" / "population_capacity.toml"
    )
    assert config.population_capacity.generated_label == "Prosper or Perish"
    assert config.population_capacity.managed_write_mode == "mod_root"


def test_load_project_config_accepts_blueprint_evaluation_config(tmp_path: Path) -> None:
    config_path = tmp_path / "foundations.toml"
    config_path.write_text(
        """
[project]
name = "Foundations"
mod_root = "mod/Foundations"

[blueprint_evaluation]
raw_input_efficiency_per_good = 0.04
profit_percent_min = -0.25
profit_percent_max = 0.25
base_output_per_1k_min = 0.08
base_output_per_1k_max = 0.14
age_throughput_growth = 0.12
throughput_tolerance = 0.20
amortization_months_min = 40
amortization_months_max = 80

[blueprint_evaluation.throughput_gold_per_1k]
peasants = 1.1
laborers = 1.6
burghers = 2.6

[blueprint_evaluation.employment_size_constants]
rural_peasant_produce_employment = 3
guild_employment = 4
""".strip(),
        encoding="utf-8",
    )

    config = load_project_config(config_path)

    evaluation = config.blueprint_evaluation
    assert evaluation.raw_input_efficiency_per_good == 0.04
    assert evaluation.profit_percent_min == -0.25
    assert evaluation.profit_percent_max == 0.25
    assert evaluation.base_output_per_1k_min == 0.08
    assert evaluation.base_output_per_1k_max == 0.14
    assert evaluation.throughput_gold_per_1k["laborers"] == 1.6
    assert evaluation.age_throughput_growth == 0.12
    assert evaluation.throughput_tolerance == 0.20
    assert evaluation.amortization_months_min == 40
    assert evaluation.amortization_months_max == 80
    assert evaluation.roi_cycles_max == 80
    assert evaluation.to_pipeline_config()["amortization_months_min"] == 40
    assert evaluation.to_pipeline_config()["amortization_months_max"] == 80
    assert evaluation.employment_size_constants["guild_employment"] == 4


def test_load_project_config_accepts_legacy_roi_cycles_alias(tmp_path: Path) -> None:
    config_path = tmp_path / "foundations.toml"
    config_path.write_text(
        """
[project]
name = "Foundations"
mod_root = "mod/Foundations"

[blueprint_evaluation]
roi_cycles_max = 80
""".strip(),
        encoding="utf-8",
    )

    evaluation = load_project_config(config_path).blueprint_evaluation

    assert evaluation.amortization_months_max == 80
    assert evaluation.to_pipeline_config()["amortization_months_max"] == 80
    assert evaluation.to_pipeline_config()["roi_cycles_max"] == 80


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

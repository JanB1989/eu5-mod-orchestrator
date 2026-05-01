from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from eu5_mod_orchestrator.config import load_project_config
from eu5_mod_orchestrator.scaffold import init_project as run_init_project
from eu5_mod_orchestrator.workflow import (
    analyze as run_analyze,
    build as run_build,
    deploy as run_deploy,
    inspect_project,
    label as run_label,
    list_blueprints as run_list_blueprints,
    parity as run_parity,
    population_capacity_analyze as run_population_capacity_analyze,
    population_capacity_effects as run_population_capacity_effects,
    population_capacity_extract as run_population_capacity_extract,
    population_capacity_extract_effects as run_population_capacity_extract_effects,
    population_capacity_preview_start as run_population_capacity_preview_start,
    population_capacity_render as run_population_capacity_render,
    render as run_render,
    savegame as run_savegame,
    validate as run_validate,
)

app = typer.Typer(help="Coordinate reusable EU5 mod build pipelines.")
blueprint_app = typer.Typer(help="Inspect and verify accepted blueprints.")
population_capacity_app = typer.Typer(help="Analyze and render population-capacity data.")
app.add_typer(blueprint_app, name="blueprint")
app.add_typer(population_capacity_app, name="population-capacity")


def _config(project: Path):
    return load_project_config(project)


@app.command()
def inspect(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")]
) -> None:
    typer.echo(inspect_project(_config(project)))


@app.command()
def analyze(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")]
) -> None:
    result = run_analyze(_config(project))
    typer.echo(result)


@app.command()
def savegame(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")],
    save: Annotated[Path | None, typer.Option("--save", help="Explicit .eu5 save path.")] = None,
    save_dir: Annotated[Path | None, typer.Option("--save-dir", help="Directory to search for newest .eu5 save.")] = None,
    force_rakaly: Annotated[
        bool,
        typer.Option(help="Force optional Rakaly/pyeu5 parsing instead of native text parsing."),
    ] = False,
) -> None:
    result = run_savegame(
        _config(project),
        save_path=save,
        save_dir=save_dir,
        force_rakaly=force_rakaly,
    )
    typer.echo(result)


@app.command()
def label(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")],
    dry_run: Annotated[bool, typer.Option(help="Validate only; do not write mod files.")] = False,
    goods: Annotated[str | None, typer.Option("--goods", help="Comma-separated trade goods to inject.")] = None,
    scale: Annotated[
        str | None,
        typer.Option(
            "--scale",
            help="Override scale mode for selected goods.",
        ),
    ] = None,
) -> None:
    if scale is not None and scale not in {
        "rank_uniform",
        "min_max_linear",
        "linear_percentile",
        "tanh_iqr",
    }:
        raise typer.BadParameter(
            "scale must be one of rank_uniform, min_max_linear, linear_percentile, tanh_iqr"
        )
    typer.echo(run_label(_config(project), goods=goods, scale=scale, dry_run=dry_run))


@population_capacity_app.command("analyze")
def population_capacity_analyze(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")]
) -> None:
    typer.echo(run_population_capacity_analyze(_config(project)))


@population_capacity_app.command("effects")
def population_capacity_effects(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")]
) -> None:
    typer.echo(run_population_capacity_effects(_config(project)))


@population_capacity_app.command("preview-start")
def population_capacity_preview_start(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")],
    group_by: Annotated[str | None, typer.Option("--group-by", help="Optional grouping column.")] = None,
    include_no_raw_material: Annotated[
        bool,
        typer.Option("--include-no-raw-material", help="Include sea/lake/non-economic locations for debugging."),
    ] = False,
) -> None:
    typer.echo(
        run_population_capacity_preview_start(
            _config(project),
            group_by=group_by,
            include_no_raw_material=include_no_raw_material,
        )
    )


@population_capacity_app.command("render")
def population_capacity_render(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")],
    dry_run: Annotated[bool, typer.Option(help="Plan writes without changing mod files.")] = False,
) -> None:
    typer.echo(run_population_capacity_render(_config(project), dry_run=dry_run))


@population_capacity_app.command("extract")
def population_capacity_extract(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")],
    paths: Annotated[list[Path], typer.Argument(help="Files to strip population-capacity lines from.")],
    dry_run: Annotated[bool, typer.Option(help="Plan extraction without changing files.")] = False,
) -> None:
    typer.echo(run_population_capacity_extract(_config(project), paths=paths, dry_run=dry_run))


@population_capacity_app.command("extract-effects")
def population_capacity_extract_effects(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")],
    paths: Annotated[list[Path], typer.Argument(help="Files to strip capacity-pressure effect blocks from.")],
    dry_run: Annotated[bool, typer.Option(help="Plan extraction without changing files.")] = False,
) -> None:
    typer.echo(run_population_capacity_extract_effects(_config(project), paths=paths, dry_run=dry_run))


@app.command("init")
def init_workspace(
    project_dir: Annotated[Path, typer.Argument(help="Directory to initialize.")],
    name: Annotated[str, typer.Option(help="Human-readable project name.")],
    mod_name: Annotated[str, typer.Option(help="Mod folder name under the workspace mod directory.")],
    vanilla_root: Annotated[Path, typer.Option(help="Europa Universalis V install directory.")],
    force: Annotated[bool, typer.Option(help="Allow scaffolding into a non-empty directory.")] = False,
) -> None:
    typer.echo(
        run_init_project(
            project_dir,
            name=name,
            mod_name=mod_name,
            vanilla_root=vanilla_root,
            force=force,
        )
    )


@app.command()
def render(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")],
    dry_run: Annotated[bool, typer.Option(help="Plan writes without changing mod files.")] = False,
    overwrite: Annotated[bool, typer.Option(help="Replace existing generated files.")] = False,
    refresh_assets: Annotated[bool, typer.Option(help="Replace existing generated image assets.")] = False,
) -> None:
    typer.echo(run_render(_config(project), dry_run=dry_run, overwrite=overwrite, refresh_assets=refresh_assets))


@app.command()
def validate(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")]
) -> None:
    typer.echo(run_validate(_config(project)))


@app.command()
def deploy(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")],
    dry_run: Annotated[bool, typer.Option(help="Plan sync without changing deployed files.")] = False,
    clean: Annotated[
        bool,
        typer.Option(help="Delete deployed files that are no longer present in the built mod."),
    ] = False,
) -> None:
    typer.echo(run_deploy(_config(project), dry_run=dry_run, clean=clean))


@app.command()
def build(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")],
    dry_run: Annotated[bool, typer.Option(help="Plan writes without changing mod files.")] = False,
    overwrite: Annotated[bool, typer.Option(help="Replace existing generated files.")] = False,
    refresh_assets: Annotated[bool, typer.Option(help="Replace existing generated image assets.")] = False,
) -> None:
    typer.echo(run_build(_config(project), dry_run=dry_run, overwrite=overwrite, refresh_assets=refresh_assets))


@blueprint_app.command("list")
def blueprint_list(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")]
) -> None:
    typer.echo(run_list_blueprints(_config(project)))


@blueprint_app.command("parity")
def blueprint_parity(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")],
    mod_id: Annotated[str, typer.Option(help="Load-order mod id to replace for the candidate render.")] = "constructor",
) -> None:
    typer.echo(run_parity(_config(project), mod_id=mod_id))

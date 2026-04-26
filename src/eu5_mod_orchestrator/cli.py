from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from eu5_mod_orchestrator.config import load_project_config
from eu5_mod_orchestrator.workflow import (
    analyze as run_analyze,
    build as run_build,
    inspect_project,
    render as run_render,
    validate as run_validate,
)

app = typer.Typer(help="Coordinate reusable EU5 mod build pipelines.")


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
def render(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")],
    dry_run: Annotated[bool, typer.Option(help="Plan writes without changing mod files.")] = False,
    overwrite: Annotated[bool, typer.Option(help="Replace existing generated files.")] = False,
) -> None:
    typer.echo(run_render(_config(project), dry_run=dry_run, overwrite=overwrite))


@app.command()
def validate(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")]
) -> None:
    typer.echo(run_validate(_config(project)))


@app.command()
def build(
    project: Annotated[Path, typer.Option("--project", "-p", help="Project TOML config.")],
    dry_run: Annotated[bool, typer.Option(help="Plan writes without changing mod files.")] = False,
    overwrite: Annotated[bool, typer.Option(help="Replace existing generated files.")] = False,
) -> None:
    typer.echo(run_build(_config(project), dry_run=dry_run, overwrite=overwrite))

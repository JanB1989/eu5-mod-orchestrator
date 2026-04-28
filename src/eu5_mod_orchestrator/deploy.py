from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from eu5_mod_orchestrator.config import OrchestratorConfig


class DeployError(ValueError):
    """Raised when a mod deploy request is unsafe or incomplete."""


@dataclass
class DeployResult:
    source: Path
    target: Path
    copied: list[Path] = field(default_factory=list)
    deleted: list[Path] = field(default_factory=list)
    planned_copies: list[Path] = field(default_factory=list)
    planned_deletes: list[Path] = field(default_factory=list)
    dry_run: bool = False

    def summary(self) -> str:
        lines = ["EU5 mod deploy complete."]
        if self.dry_run:
            lines[0] = "EU5 mod deploy dry run complete."
        lines.append(f"Source: {self.source}")
        lines.append(f"Target: {self.target}")
        if self.planned_copies:
            lines.append("Planned copies:")
            lines.extend(f"  {path}" for path in self.planned_copies)
        if self.planned_deletes:
            lines.append("Planned deletes:")
            lines.extend(f"  {path}" for path in self.planned_deletes)
        if self.copied:
            lines.append("Copied:")
            lines.extend(f"  {path}" for path in self.copied)
        if self.deleted:
            lines.append("Deleted:")
            lines.extend(f"  {path}" for path in self.deleted)
        if not self.planned_copies and not self.planned_deletes and not self.copied and not self.deleted:
            lines.append("No file changes needed.")
        return "\n".join(lines)


def deploy(config: OrchestratorConfig, *, dry_run: bool = False, clean: bool = False) -> DeployResult:
    if config.deploy_target is None:
        raise DeployError("deploy.target is not configured.")

    source = config.mod_root.resolve()
    target = config.deploy_target.resolve()
    if source == target:
        raise DeployError("deploy source and target must be different directories.")
    if not source.exists():
        raise DeployError(f"deploy source does not exist: {source}")
    if not source.is_dir():
        raise DeployError(f"deploy source must be a directory: {source}")

    result = DeployResult(source=source, target=target, dry_run=dry_run)
    source_dirs = _source_dirs(source)
    source_files = _source_files(source)
    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)

    if clean:
        _validate_clean_target(config, target)
        for stale in _stale_targets(source_files, source, target):
            result.planned_deletes.append(stale)
            if not dry_run:
                stale.unlink()
                result.deleted.append(stale)

    for source_dir in source_dirs:
        target_dir = target / source_dir.relative_to(source)
        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)

    for source_file in source_files:
        target_file = target / source_file.relative_to(source)
        result.planned_copies.append(target_file)
        if dry_run:
            continue
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target_file)
        result.copied.append(target_file)

    if not dry_run:
        _remove_empty_dirs(target, expected_dirs={target / d.relative_to(source) for d in source_dirs})
    return result


def _source_dirs(source: Path) -> list[Path]:
    return sorted(path for path in source.rglob("*") if path.is_dir())


def _source_files(source: Path) -> list[Path]:
    return sorted(path for path in source.rglob("*") if path.is_file())


def _stale_targets(source_files: list[Path], source: Path, target: Path) -> list[Path]:
    if not target.exists():
        return []
    expected = {target / source_file.relative_to(source) for source_file in source_files}
    return sorted(path for path in target.rglob("*") if path.is_file() and path not in expected)


def _validate_clean_target(config: OrchestratorConfig, target: Path) -> None:
    if not target.is_absolute():
        raise DeployError("clean deploy target must resolve to an absolute path.")

    dangerous = {
        target.anchor,
        str(Path.home().resolve()),
        str(config.project_root.resolve()),
        str(config.project_root.parent.resolve()),
    }
    normalized = str(target)
    if normalized in dangerous:
        raise DeployError(f"refusing to clean broad deploy target: {target}")

    lowered_parts = [part.lower() for part in target.parts]
    if target.name.lower() in {"", "documents", "mod"}:
        raise DeployError(f"refusing to clean broad deploy target: {target}")
    if len(lowered_parts) < 4:
        raise DeployError(f"refusing to clean shallow deploy target: {target}")


def _remove_empty_dirs(target: Path, *, expected_dirs: set[Path] | None = None) -> None:
    if not target.exists():
        return
    keep = expected_dirs or set()
    for path in sorted((path for path in target.rglob("*") if path.is_dir()), reverse=True):
        if path in keep:
            continue
        try:
            path.rmdir()
        except OSError:
            pass

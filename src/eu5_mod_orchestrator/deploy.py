from __future__ import annotations

import filecmp
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from eu5_mod_orchestrator.config import OrchestratorConfig

# Deploy targets usually sit on a Windows drive mounted into WSL, where every file-system call is a
# slow round trip. The target is therefore walked once and its files are stat'ed and copied in parallel.
_IO_WORKERS = 32


class DeployError(ValueError):
    """Raised when a mod deploy request is unsafe or incomplete."""


@dataclass
class DeployResult:
    source: Path
    target: Path
    copied: list[Path] = field(default_factory=list)
    deleted: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)
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
        if self.skipped:
            lines.append(f"Skipped unchanged: {len(self.skipped)}")
        if not self.planned_copies and not self.planned_deletes and not self.copied and not self.deleted:
            lines.append("No file changes needed.")
        return "\n".join(lines)


def deploy(
    config: OrchestratorConfig,
    *,
    dry_run: bool = False,
    clean: bool = False,
    force: bool = False,
) -> DeployResult:
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
    source_dirs, source_files = _walk(source)
    target_dirs, target_files = _walk(target) if target.is_dir() else (set(), set())
    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)

    if clean:
        _validate_clean_target(config, target)
        for stale in sorted(target_files - source_files):
            result.planned_deletes.append(target / stale)
            if not dry_run:
                (target / stale).unlink()
                result.deleted.append(target / stale)

    if not dry_run:
        for relative in sorted(source_dirs - target_dirs):
            (target / relative).mkdir(parents=True, exist_ok=True)

    ordered = sorted(source_files)
    existing = [relative for relative in ordered if relative in target_files]
    with ThreadPoolExecutor(_IO_WORKERS) as pool:
        target_stats = dict(zip(existing, pool.map(lambda rel: (target / rel).stat(), existing)))
        unchanged = set()
        if not force:
            matches = pool.map(lambda rel: _files_match(source / rel, target / rel, target_stats[rel]), existing)
            unchanged = {relative for relative, match in zip(existing, matches) if match}
        copies = [relative for relative in ordered if relative not in unchanged]
        result.skipped = [target / relative for relative in ordered if relative in unchanged]
        result.planned_copies = [target / relative for relative in copies]
        if not dry_run:
            list(pool.map(lambda rel: shutil.copy2(source / rel, target / rel), copies))
            result.copied = list(result.planned_copies)

    if not dry_run:
        _remove_empty_dirs(target, target_dirs - source_dirs)
    return result


def _walk(root: Path) -> tuple[set[Path], set[Path]]:
    """Directories and files under ``root``, relative to it, from one directory listing pass."""
    dirs: set[Path] = set()
    files: set[Path] = set()
    for current, dir_names, file_names in os.walk(root):
        relative = Path(current).relative_to(root)
        dirs.update(relative / name for name in dir_names)
        files.update(relative / name for name in file_names)
    return dirs, files


def _files_match(source: Path, target: Path, target_stat: os.stat_result) -> bool:
    source_stat = source.stat()
    if source_stat.st_size != target_stat.st_size:
        return False
    if int(source_stat.st_mtime) == int(target_stat.st_mtime):
        return True
    return filecmp.cmp(source, target, shallow=False)


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


def _remove_empty_dirs(target: Path, candidates: set[Path]) -> None:
    """Remove target directories the source no longer has, deepest first, if they are empty."""
    for relative in sorted(candidates, key=lambda path: len(path.parts), reverse=True):
        try:
            (target / relative).rmdir()
        except OSError:
            pass

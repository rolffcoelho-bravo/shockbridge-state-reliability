"""Minimal fail-closed extraction for in-memory Git tar archives."""

from __future__ import annotations

import shutil
import tarfile
from pathlib import Path


class UnsafeTarError(ValueError):
    """Raised when an archive cannot be extracted without path ambiguity."""


def _member_parts(member: tarfile.TarInfo) -> tuple[str, ...]:
    name = member.name.rstrip("/")
    raw_parts = name.split("/")
    if (
        not name
        or name.startswith("/")
        or "\\" in name
        or any(part in {"", ".", ".."} for part in raw_parts)
        or (len(raw_parts[0]) == 2 and raw_parts[0][0].isalpha() and raw_parts[0][1] == ":")
        or not (member.isfile() or member.isdir())
    ):
        raise UnsafeTarError(f"Unsafe tar member: {member.name!r}")
    return tuple(raw_parts)


def safe_tar_member(member: tarfile.TarInfo) -> bool:
    """Return whether a member is a portable regular file or directory."""
    try:
        _member_parts(member)
    except UnsafeTarError:
        return False
    return True


def extract_tar_safely(archive: tarfile.TarFile, destination: Path) -> int:
    """Extract validated regular files without calling TarFile.extract/all."""
    if not destination.is_dir() or destination.is_symlink():
        raise UnsafeTarError("Extraction destination must be a real directory")
    root = destination.resolve()
    members = archive.getmembers()
    validated: list[tuple[tarfile.TarInfo, tuple[str, ...]]] = []
    seen: set[tuple[str, ...]] = set()
    file_paths: set[tuple[str, ...]] = set()

    for member in members:
        parts = _member_parts(member)
        if parts in seen:
            raise UnsafeTarError(f"Duplicate tar member: {member.name!r}")
        seen.add(parts)
        if member.isfile():
            file_paths.add(parts)
        target = destination.joinpath(*parts).resolve(strict=False)
        if root not in target.parents:
            raise UnsafeTarError(f"Tar member escapes destination: {member.name!r}")
        validated.append((member, parts))

    for _member, parts in validated:
        if any(parts[:index] in file_paths for index in range(1, len(parts))):
            raise UnsafeTarError(f"Tar member descends from a file: {'/'.join(parts)!r}")

    for member, parts in sorted(validated, key=lambda item: (len(item[1]), item[1])):
        target = destination.joinpath(*parts)
        if member.isdir():
            target.mkdir(parents=True, exist_ok=False)
            target.chmod(member.mode & 0o777)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        source = archive.extractfile(member)
        if source is None:
            raise UnsafeTarError(f"Regular tar member has no data: {member.name!r}")
        with source, target.open("xb") as output:
            shutil.copyfileobj(source, output)
        target.chmod(member.mode & 0o777)

    return sum(member.isfile() for member, _parts in validated)

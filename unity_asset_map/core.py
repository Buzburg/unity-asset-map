"""Read-only Unity GUID reference indexing. No editor or semantic C# parsing."""

from __future__ import annotations

import os
import re
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path

GUID = re.compile(r"\bguid:\s*([0-9a-fA-F]{32})(?![0-9a-fA-F])")
OWN_GUID = re.compile(r"^guid:\s*([0-9a-fA-F]{32})\s*$", re.MULTILINE)
TEXT_ASSETS = {
    ".unity",
    ".prefab",
    ".asset",
    ".mat",
    ".controller",
    ".overridecontroller",
    ".anim",
    ".playable",
    ".rendertexture",
    ".shadergraph",
    ".shadersubgraph",
}
SKIP_DIRS = {"Library", "Temp", "Logs", "obj", "Build", "Builds", ".git", ".venv", "node_modules"}
MAX_FILE = 10 * 1024 * 1024


def project_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(
            d
            for d in dirs
            if d not in SKIP_DIRS and (Path(directory) / d).resolve() == (Path(directory) / d).absolute()
        )
        for name in sorted(files):
            path = Path(directory) / name
            if not path.is_symlink() and path.resolve().is_relative_to(root):
                paths.append(path)
    return paths


def index(root: Path, database: Path, ignore_guids: set[str] | None = None) -> dict[str, object]:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Project must be a directory.")
    ignored = {g.lower() for g in (ignore_guids or set())}
    if any(re.fullmatch("[0-9a-f]{32}", guid) is None for guid in ignored):
        raise ValueError("Ignored GUIDs must have exactly 32 hex characters.")
    owners: dict[str, list[str]] = defaultdict(list)
    references: list[tuple[str, str, int]] = []
    skipped: list[dict[str, str]] = []
    warnings: list[str] = []
    for path in project_files(root):
        relative = path.relative_to(root).as_posix()
        if path.suffix.lower() not in TEXT_ASSETS | {".meta"}:
            continue
        if path.stat().st_size > MAX_FILE:
            skipped.append({"path": relative, "reason": "Exceeds 10 MiB text-file limit."})
            continue
        try:
            content = path.read_text(encoding="utf-8-sig")
        except UnicodeError:
            skipped.append({"path": relative, "reason": "Not UTF-8 text serialization."})
            continue
        if "\0" in content:
            skipped.append({"path": relative, "reason": "Binary content."})
            continue
        if path.suffix.lower() == ".meta":
            match = OWN_GUID.search(content)
            asset = path.with_suffix("")
            if match and asset.exists():
                owners[match[1].lower()].append(asset.relative_to(root).as_posix())
            else:
                warnings.append(f"Missing asset or valid top-level GUID: {relative}")
        else:
            for line_number, source_line in enumerate(content.splitlines(), 1):
                references.extend(
                    (relative, match[1].lower(), line_number) for match in GUID.finditer(source_line)
                )
    duplicates = {guid: paths for guid, paths in owners.items() if len(paths) > 1}
    resolved = {guid: paths[0] for guid, paths in owners.items() if len(paths) == 1}
    rows: list[tuple[str, str, str | None, int, str]] = []
    for source, guid, line in references:
        status = (
            "ambiguous"
            if guid in duplicates
            else "resolved"
            if guid in resolved
            else "ignored"
            if guid in ignored or guid.startswith("0000000000000000")
            else "unresolved"
        )
        rows.append((source, guid, resolved.get(guid), line, status))
    with closing(sqlite3.connect(database)) as db, db:
        db.execute("CREATE TABLE IF NOT EXISTS metadata (root TEXT)")
        db.execute(
            "CREATE TABLE IF NOT EXISTS refs (source TEXT, guid TEXT, target TEXT, line INTEGER, status TEXT)"
        )
        db.execute("CREATE INDEX IF NOT EXISTS refs_source ON refs(source)")
        db.execute("CREATE INDEX IF NOT EXISTS refs_target ON refs(target)")
        db.execute("DELETE FROM metadata")
        db.execute("DELETE FROM refs")
        db.execute("INSERT INTO metadata VALUES (?)", (str(root),))
        db.executemany("INSERT INTO refs VALUES (?,?,?,?,?)", rows)
    return {
        "project": str(root),
        "assets_with_unique_guids": len(resolved),
        "references": len(rows),
        "unresolved": [
            {"source": s, "guid": g, "line": line} for s, g, _, line, status in rows if status == "unresolved"
        ],
        "duplicate_guids": duplicates,
        "skipped": skipped,
        "warnings": warnings,
        "scope": "Text GUID references only. Unresolved may mean an external package; inspect before changing.",
    }


def references(database: Path, asset: str, direction: str = "incoming") -> list[dict[str, object]]:
    if direction not in {"incoming", "outgoing"}:
        raise ValueError("Direction must be incoming or outgoing.")
    if not database.is_file():
        raise ValueError("Index does not exist; run scan first.")
    normalized = asset.replace("\\", "/")
    column = "target" if direction == "incoming" else "source"
    with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as db:
        rows = db.execute(
            f"SELECT source, guid, target, line, status FROM refs WHERE {column}=? ORDER BY source,line",
            (normalized,),
        ).fetchall()
    return [dict(zip(("source", "guid", "target", "line", "status"), row)) for row in rows]


def create_fixture(root: Path) -> None:
    assets = root / "Assets"
    assets.mkdir(parents=True, exist_ok=True)
    files = {
        "Hero.cs": "public class Hero {}\n",
        "Hero.cs.meta": "guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
        "Main.unity.meta": "guid: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n",
        "Main.unity": "%YAML 1.1\n--- !u!114 &1\nMonoBehaviour:\n"
        "  m_Script: {fileID: 11500000, guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa, type: 3}\n"
        "  material: {fileID: 2100000, guid: cccccccccccccccccccccccccccccccc, type: 2}\n",
    }
    for name, content in files.items():
        target = assets / name
        if target.exists():
            raise FileExistsError(target)
        target.write_text(content, encoding="utf-8")

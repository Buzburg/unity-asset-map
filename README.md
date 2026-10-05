# Unity Asset Map

**By Buzburg LLC** · Apache-2.0


> [!NOTE]
> **In Plain English:** An X-ray dependency viewer for Unity video game files. In game development, deleting or modifying an innocent-looking asset can silently break scenes and prefabs across the game. This tool scans the project's text files and maps out all connections so you know exactly what relies on a file before making changes.

Find out which scenes, prefabs, or other supported text assets reference a file before changing it. Unity Asset Map scans Unity GUID references and lets you inspect both incoming and outgoing links with source line numbers.

It builds a local SQLite index and reports unresolved GUIDs, duplicate ownership, and skipped files. Unity does not need to be running. Binary assets and dependencies that are not represented by supported text GUID references remain outside its scope.

## Start

Python 3.11 or newer, no runtime dependencies; Unity is not required:

```powershell
python -m unity_asset_map demo
```

Open `demo-output/report.html`. Original synthetic files demonstrate a scene that references a script and an unresolved material.

## Scan a real project

```powershell
python -m unity_asset_map scan C:/Projects/MyGame --database assets.sqlite --report assets.html
python -m unity_asset_map refs Assets/Scripts/Hero.cs --database assets.sqlite
python -m unity_asset_map refs Assets/Scenes/Main.unity --database assets.sqlite --direction outgoing
```

Paths in queries are project-relative. Re-run `scan` after changes; each successful scan replaces the old index transactionally. Keep the database and report outside the Unity asset directories.

Use repeated `--ignore-guid GUID` options for known external references. GUIDs beginning with sixteen zeros are classified as ignored built-in-style references when not resolved locally; this is a heuristic, not editor validation. Duplicate GUID ownership is reported as ambiguous and never assigned arbitrarily.

## Scope

The scanner recognizes literal `guid:` references, not arbitrary references encoded in JSON, runtime strings, or C# code. It skips common generated directories, symlink/junction directories, binary content, and files larger than 10 MiB. It indexes local package content when present; remotely resolved packages may appear unresolved. It does not infer nested prefab override semantics or prove that a file is safe to delete.

The project files are read-only inputs. The index and report are the only outputs. Unresolved means “not resolved by this scan,” not necessarily a broken Unity project.

## Verify and install

```powershell
python -m unittest discover -s tests -v
python -m pip install . mypy ruff
python -m mypy .
python -m ruff check .
```

Installed command: `unity-asset-map`. This folder is independently publishable; CI is configured for Windows/Linux and Python 3.11–3.13.

Inspired by [Unity Insight](https://arxiv.org/abs/2609.27585). This is an independent, limited GUID reference utility, not Unity Insight or an official Unity product. No author code or Unity assets are bundled. See LICENSE and NOTICE.
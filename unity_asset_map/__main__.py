from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
from pathlib import Path

from ._support import report, save
from .core import create_fixture, index, references


def main() -> int:
    parser = argparse.ArgumentParser(description="Index and search Unity text asset references.")
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan")
    scan.add_argument("project", type=Path)
    scan.add_argument("--database", type=Path, required=True)
    scan.add_argument("--ignore-guid", action="append", default=[])
    scan.add_argument("--report", type=Path)
    query = commands.add_parser("refs")
    query.add_argument("asset")
    query.add_argument("--database", type=Path, required=True)
    query.add_argument("--direction", choices=["incoming", "outgoing"], default="incoming")
    demo = commands.add_parser("demo")
    demo.add_argument("--output", type=Path, default=Path("demo-output"))
    args = parser.parse_args()
    try:
        result: object
        if args.command == "demo":
            args.output.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                create_fixture(root)
                database = args.output / "assets.sqlite"
                summary = index(root, database)
                summary["project"] = "Original synthetic Unity fixture"
                result = {
                    "scan": summary,
                    "who_uses_Hero": references(database, "Assets/Hero.cs"),
                    "Main_scene_dependencies": references(database, "Assets/Main.unity", "outgoing"),
                }
            save(args.output / "results.json", result)
            report(args.output / "report.html", "Unity Asset Map · see what depends on a file", result)
            print(f"Demo saved to {args.output.resolve()}")
            return 0
        if args.command == "scan":
            if args.database.resolve().is_relative_to(args.project.resolve() / "Assets"):
                raise ValueError("Keep the database outside the project's Assets directory.")
            if args.report and (
                args.report.resolve() == args.database.resolve()
                or args.report.resolve().is_relative_to(args.project.resolve() / "Assets")
            ):
                raise ValueError("Keep the report separate from the database and Assets directory.")
            result = index(args.project, args.database, set(args.ignore_guid))
            if args.report:
                report(args.report, "Unity Asset Map scan", result)
        else:
            result = references(args.database, args.asset, args.direction)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())

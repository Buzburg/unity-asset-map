from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from unity_asset_map.core import create_fixture, index, references


class AssetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "index.db"
        create_fixture(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_incoming_outgoing_and_unresolved(self) -> None:
        result = index(self.root, self.db)
        self.assertEqual(result["references"], 2)
        self.assertEqual(len(references(self.db, "Assets/Hero.cs")), 1)
        self.assertEqual(len(references(self.db, "Assets/Main.unity", "outgoing")), 2)

    def test_duplicate_is_ambiguous(self) -> None:
        (self.root / "Assets/Copy.cs").write_text("class Copy {}")
        (self.root / "Assets/Copy.cs.meta").write_text("guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n")
        index(self.root, self.db)
        self.assertEqual(references(self.db, "Assets/Hero.cs"), [])
        self.assertEqual(references(self.db, "Assets/Main.unity", "outgoing")[0]["status"], "ambiguous")

    def test_reindex_removes_stale_references(self) -> None:
        index(self.root, self.db)
        (self.root / "Assets/Main.unity").write_text("%YAML 1.1\n")
        index(self.root, self.db)
        self.assertEqual(references(self.db, "Assets/Hero.cs"), [])

    def test_ignored_external_and_binary(self) -> None:
        (self.root / "Assets/Binary.asset").write_bytes(b"\0\xff")
        result = index(self.root, self.db, {"c" * 32})
        self.assertEqual(result["unresolved"], [])
        self.assertTrue(result["skipped"])

    def test_excluded_library(self) -> None:
        (self.root / "Library").mkdir()
        (self.root / "Library/fake.asset").write_text("guid: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n")
        self.assertEqual(index(self.root, self.db)["references"], 2)


if __name__ == "__main__":
    unittest.main()

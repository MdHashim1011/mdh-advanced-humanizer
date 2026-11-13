"""Tests for tools/validate_package.py (standard library only)."""
import importlib.util
import json
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
_spec = importlib.util.spec_from_file_location("validate_package", os.path.join(REPO, "tools", "validate_package.py"))
vp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vp)

VERSIONED = ("SKILL.md", "PORTABLE.md", "CHANGELOG.md", "scripts/mdh_text.py",
             ".claude-plugin/plugin.json", ".claude-plugin/marketplace.json", ".cursor-plugin/plugin.json")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


class VersionSources(unittest.TestCase):
    """Every place a user can see the version must be compared (package audit finding F8)."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        for rel in VERSIONED:
            dest = os.path.join(self.root, *rel.split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(os.path.join(REPO, *rel.split("/")), dest)
        self.marketplace = os.path.join(self.root, ".claude-plugin", "marketplace.json")
        self.portable = os.path.join(self.root, "PORTABLE.md")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def versions(self):
        return {k: v for k, v in vp.collect_versions(self.root, None).items() if not k.startswith("SKILL.md")}

    def edit_marketplace(self, change):
        data = json.loads(read(self.marketplace))
        change(data)
        write(self.marketplace, json.dumps(data))

    def test_marketplace_plugin_version_is_compared(self):
        self.edit_marketplace(lambda d: d["plugins"][0].update(version="9.9.9"))
        self.assertIn("9.9.9", self.versions().values())

    def test_marketplace_metadata_version_is_compared(self):
        self.edit_marketplace(lambda d: d["metadata"].update(version="9.9.9"))
        self.assertIn("9.9.9", self.versions().values())

    def test_missing_optional_marketplace_version_is_not_an_error(self):
        self.edit_marketplace(lambda d: d["metadata"].pop("version"))
        self.assertNotIn(None, self.versions().values())

    def test_portable_title_version_is_compared(self):
        first, rest = read(self.portable).split("\n", 1)
        write(self.portable, first.rsplit("(v", 1)[0] + "(v9.9.9)\n" + rest)
        self.assertIn("9.9.9", self.versions().values())

    def test_portable_title_without_version_is_reported(self):
        write(self.portable, "# Portable instructions\n\nNo version here.\n")
        self.assertIsNone(self.versions()["PORTABLE.md title"])


if __name__ == "__main__":
    unittest.main()

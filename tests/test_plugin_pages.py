from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "docs" / "_ext"))

import plugin_pages


class PluginPagesTests(unittest.TestCase):
    def test_plugin_page_treats_metadata_as_text_and_ignores_readme(self):
        page = plugin_pages._render_plugin_page(
            {
                "name": "conda-example",
                "description": "<script>alert(1)</script>\n:::{include} /etc/passwd",
                "repo_url": "https://github.com/owner/example",
                "repo_full_name": "owner/example",
                "stars": 1,
                "category": "Other",
                "docs": "javascript:alert(1)",
                "topics": ["conda-plugin"],
                "entry_points": {"example`name": "example.plugin\n:::{raw} html"},
                "readme": "<script>evil_from_readme()</script>",
            }
        )

        self.assertNotIn("<script>", page)
        self.assertNotIn("\n:::{include}", page)
        self.assertNotIn(":link: javascript:", page)
        self.assertNotIn("evil_from_readme", page)

    def test_cleanup_removes_only_generated_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            category = Path(temp_dir) / "category"
            plugin = category / "plugin"
            plugin.mkdir(parents=True)
            generated = plugin / "index.md"
            generated.write_text("generated")
            manual = category / "manual.md"
            manual.write_text("keep")
            plugin_pages._GENERATED_FILES[:] = [generated]
            plugin_pages._GENERATED_DIRS[:] = [category, plugin]

            plugin_pages._cleanup_source_files(None, None)

            self.assertFalse(generated.exists())
            self.assertTrue(manual.exists())
            self.assertTrue(category.exists())
            self.assertFalse(plugin.exists())

    def test_generated_files_do_not_overwrite_authored_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            data_dir = source / "_data"
            data_dir.mkdir()
            (data_dir / "plugins.json").write_text(
                json.dumps(
                    {
                        "categories": ["Other"],
                        "plugins": [
                            {
                                "name": "conda-example",
                                "description": "Example",
                                "repo_url": "https://github.com/owner/example",
                                "repo_full_name": "owner/example",
                                "stars": 1,
                                "category": "Other",
                            }
                        ],
                    }
                )
            )
            path = source / "other" / "conda-example" / "index.md"
            path.parent.mkdir(parents=True)
            path.write_text("authored")
            app = type("App", (), {"srcdir": str(source)})()

            with self.assertRaises(FileExistsError):
                plugin_pages._generate_source_files(app)

            self.assertEqual("authored", path.read_text())
            self.assertFalse((source / "other" / "index.md").exists())


if __name__ == "__main__":
    unittest.main()

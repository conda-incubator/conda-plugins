from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import plugin_list


class FakeRepo:
    def __init__(
        self,
        full_name: str,
        *,
        stars: int = 1,
        private: bool = False,
        content: str = "",
    ):
        self.full_name = full_name
        self.name = full_name.rsplit("/", 1)[-1]
        self.description = "Repository description"
        self.html_url = f"https://github.com/{full_name}"
        self.stargazers_count = stars
        self.fork = False
        self.private = private
        self.content = content

    def get_topics(self):
        return ["conda-plugin"]

    def get_contents(self, path: str):
        return type(
            "Content",
            (),
            {"path": path, "decoded_content": self.content.encode()},
        )()


class FakeResult:
    def __init__(self, repo: FakeRepo, content: str, *, path: str = "pyproject.toml"):
        self.repository = repo
        self.decoded_content = content.encode()
        self.path = path


class PluginListTests(unittest.TestCase):
    def setUp(self):
        self.delay = plugin_list.DELAY_BETWEEN_RESULTS
        plugin_list.DELAY_BETWEEN_RESULTS = 0

    def tearDown(self):
        plugin_list.DELAY_BETWEEN_RESULTS = self.delay

    def test_discovery_requires_root_project_with_conda_entry_points(self):
        valid = """
[project]
name = "conda-example"
description = "Example"

[project.entry-points."conda"]
example = "example.plugin"

[project.urls]
Documentation = "https://example.com/docs"
"""
        results = [
            FakeResult(FakeRepo("owner/nested"), valid, path="examples/pyproject.toml"),
            FakeResult(FakeRepo("owner/empty"), "[project]\nname = 'empty'\n"),
            FakeResult(
                FakeRepo("owner/malformed"),
                "[project]\nname = 'malformed'\n"
                "[project.entry-points.conda]\nbad = 2026-01-01\n",
            ),
            FakeResult(FakeRepo("owner/private", private=True), valid),
            FakeResult(FakeRepo("owner/example"), valid, path="pyproject.toml"),
        ]

        plugins = list(plugin_list.discover_plugins(results))

        self.assertEqual(["owner/example"], [plugin["repo_full_name"] for plugin in plugins])
        self.assertEqual("https://example.com/docs", plugins[0]["docs"])
        self.assertEqual({"example": "example.plugin"}, plugins[0]["entry_points"])
        self.assertNotIn("readme", plugins[0])

    def test_deduplication_uses_normalized_name_and_is_deterministic(self):
        plugins = [
            {"name": "conda_example", "stars": 2, "repo_full_name": "z/repo"},
            {"name": "conda-example", "stars": 2, "repo_full_name": "a/repo"},
        ]

        result = plugin_list.deduplicate_plugins(plugins)

        self.assertEqual(["a/repo"], [plugin["repo_full_name"] for plugin in result])

    def test_missing_search_result_is_revalidated_directly(self):
        project = """
[project]
name = "conda-example"

[project.entry-points.conda]
example = "example.plugin"
"""
        public = FakeRepo("owner/public", content=project)
        private = FakeRepo("owner/private", private=True, content=project)
        gh = type(
            "Github",
            (),
            {
                "get_repo": lambda self, name: {
                    public.full_name: public,
                    private.full_name: private,
                }[name]
            },
        )()

        with tempfile.TemporaryDirectory() as temp_dir:
            old_data_dir = plugin_list.DATA_DIR
            plugin_list.DATA_DIR = Path(temp_dir)
            self.addCleanup(setattr, plugin_list, "DATA_DIR", old_data_dir)
            (plugin_list.DATA_DIR / "plugins.json").write_text(
                json.dumps(
                    {
                        "plugins": [
                            {"repo_full_name": private.full_name},
                        ]
                    }
                )
            )

            plugins = plugin_list.revalidate_missing_plugins(
                gh,
                [],
                {public.full_name},
            )

        self.assertEqual([public.full_name], [plugin["repo_full_name"] for plugin in plugins])

    def test_fallback_category_is_not_persisted(self):
        categories = {}
        plugin = {
            "name": "conda-example",
            "description": "No matching words",
            "entry_points": {"example": "example.plugin"},
            "repo_full_name": "owner/example",
        }

        self.assertEqual("Other", plugin_list.categorize_plugin(plugin, categories))
        self.assertEqual({}, categories)

        classifier = type(
            "Classifier",
            (),
            {"classify": lambda self, value: "Channels"},
        )()
        self.assertEqual(
            "Channels",
            plugin_list.categorize_plugin(plugin, categories, classifier),
        )
        self.assertEqual({}, categories)

    def test_classifier_bounds_untrusted_prompt_metadata(self):
        model = type(
            "Model",
            (),
            {
                "create_chat_completion": lambda self, **kwargs: (
                    setattr(self, "prompt", kwargs["messages"][0]["content"])
                    or {"choices": [{"message": {"content": "Other"}}]}
                )
            },
        )()
        classifier = object.__new__(plugin_list.PluginClassifier)
        classifier.model = model
        plugin = {
            "name": "💥" * 1_000,
            "description": "💥" * 10_000,
            "entry_points": {
                f"entry-{index}-{'💥' * 100}": "💥" * 1_000
                for index in range(100)
            },
            "topics": ["💥" * 1_000 for _ in range(100)],
        }

        self.assertEqual("Other", classifier.classify(plugin))
        self.assertLess(len(model.prompt.encode()), 1_900)

    def test_reviewed_category_takes_precedence(self):
        categories = {"owner/example": "Build tools"}
        plugin = {"repo_full_name": "owner/example"}

        self.assertEqual("Build tools", plugin_list.categorize_plugin(plugin, categories))

    def test_generated_outputs_exclude_untrusted_readme_and_volatile_timestamp(self):
        plugin = {
            "name": "conda-example",
            "description": (
                "<script>alert(1)</script> | next line "
                "[install](https://evil.example) ![track](https://evil.example/pixel)"
            ),
            "repo_url": "https://github.com/owner/example",
            "repo_full_name": "owner/example",
            "stars": 1,
            "docs": None,
            "topics": [],
            "entry_points": {"example": "example.plugin"},
            "category": "Other",
            "readme": "untrusted",
        }

        table = plugin_list.generate_readme_table([plugin])
        data = json.loads(plugin_list.generate_json([plugin]))

        self.assertNotIn("<script>", table)
        self.assertIn(r"\| next line", table)
        self.assertNotIn("[install](", table)
        self.assertNotIn("![track]", table)
        self.assertNotIn("generated_at", data)
        self.assertNotIn("readme", data["plugins"][0])

    def test_discovery_rejects_unsafe_documentation_urls(self):
        project = """
[project]
name = "conda-example"

[project.entry-points.conda]
example = "example.plugin"

[project.urls]
documentation = "javascript:alert(1)"
"""
        plugins = list(
            plugin_list.discover_plugins(
                [FakeResult(FakeRepo("owner/example"), project)]
            )
        )

        self.assertIsNone(plugins[0]["docs"])

    def test_readme_rerender_replaces_exactly_one_marker_pair(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "README.md"
            path.write_text("before\n<!-- PLUGIN_LIST -->\nold\n<!-- PLUGIN_LIST -->\nafter\n")

            plugin_list.rerender_readme(path, "new\n")

            self.assertEqual(
                "before\n<!-- PLUGIN_LIST -->\nnew\n<!-- PLUGIN_LIST -->\nafter\n",
                path.read_text(),
            )
            path.write_text("<!-- PLUGIN_LIST -->\nonly one\n")
            with self.assertRaises(ValueError):
                plugin_list.rerender_readme(path, "new\n")


if __name__ == "__main__":
    unittest.main()

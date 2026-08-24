from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "docs" / "_ext"))

import plugin_pages


def test_plugin_page_treats_metadata_as_text_and_ignores_readme():
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

    assert "<script>" not in page
    assert "\n:::{include}" not in page
    assert ":link: javascript:" not in page
    assert "evil_from_readme" not in page


def test_sphinx_html_does_not_execute_repository_metadata(tmp_path: Path):
    docs = tmp_path / "docs"
    output = tmp_path / "html"
    doctrees = tmp_path / "doctrees"
    marker = tmp_path / "include-marker.txt"
    marker.write_text("included-secret-marker")
    shutil.copytree(
        PROJECT_ROOT / "docs",
        docs,
        ignore=shutil.ignore_patterns("_build", "__pycache__"),
    )
    (docs / "_data" / "plugins.json").write_text(
        json.dumps(
            {
                "categories": ["Other"],
                "plugins": [
                    {
                        "name": "conda-example",
                        "description": (
                            '<script id="evil-script">'
                            "evil_from_description()"
                            "</script>\n"
                            ":::{raw} html\n"
                            '<img id="evil-image" '
                            'src="https://evil.example/pixel">\n'
                            ":::\n"
                            f":::{{include}} {marker}\n"
                            "[steal](javascript:evil())"
                        ),
                        "repo_url": "https://github.com/owner/example",
                        "repo_full_name": "owner/example",
                        "stars": 1,
                        "category": "Other",
                        "docs": "https://docs.example/plugin",
                        "topics": ["conda-plugin"],
                        "entry_points": {
                            "example`name": "example.plugin\n:::{raw} html"
                        },
                        "readme": "<script>evil_from_readme()</script>",
                    }
                ],
            }
        )
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-W",
            "--keep-going",
            "-b",
            "dirhtml",
            "-d",
            str(doctrees),
            ".",
            str(output),
        ],
        cwd=docs,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    rendered_pages = [
        output / "index.html",
        output / "other" / "index.html",
        output / "other" / "conda-example" / "index.html",
    ]
    assert all(path.exists() for path in rendered_pages)
    html = "\n".join(path.read_text() for path in rendered_pages)
    assert "evil_from_description()" in html
    assert '<script id="evil-script">' not in html
    assert 'src="https://evil.example' not in html
    assert 'href="javascript:' not in html
    assert "included-secret-marker" not in html
    assert "evil_from_readme" not in html
    assert 'href="https://docs.example/plugin"' in html
    assert 'href="https://github.com/owner/example"' in html


def test_cleanup_removes_only_generated_files(tmp_path: Path):
    category = tmp_path / "category"
    plugin = category / "plugin"
    plugin.mkdir(parents=True)
    generated = plugin / "index.md"
    generated.write_text("generated")
    manual = category / "manual.md"
    manual.write_text("keep")
    plugin_pages._GENERATED_FILES[:] = [generated]
    plugin_pages._GENERATED_DIRS[:] = [category, plugin]

    plugin_pages._cleanup_source_files(None, None)

    assert not generated.exists()
    assert manual.exists()
    assert category.exists()
    assert not plugin.exists()


def test_generated_plugin_slug_is_bounded_and_stable(tmp_path: Path):
    long_name = "a" * 300
    colliding_name = plugin_pages._slugify(long_name)
    data_dir = tmp_path / "_data"
    data_dir.mkdir()
    (data_dir / "plugins.json").write_text(
        json.dumps(
            {
                "categories": ["Other"],
                "plugins": [
                    {
                        "name": long_name,
                        "description": "Example",
                        "repo_url": "https://github.com/owner/long",
                        "repo_full_name": "owner/long",
                        "stars": 1,
                        "category": "Other",
                    },
                    {
                        "name": colliding_name,
                        "description": "Example",
                        "repo_url": "https://github.com/owner/short",
                        "repo_full_name": "owner/short",
                        "stars": 1,
                        "category": "Other",
                    }
                ],
            }
        )
    )
    app = type("App", (), {"srcdir": str(tmp_path)})()
    generated_slugs = []

    for _ in range(2):
        try:
            plugin_pages._generate_source_files(app)
            plugin_dirs = sorted(
                path for path in (tmp_path / "other").iterdir() if path.is_dir()
            )
            assert len(plugin_dirs) == 2
            generated_slugs.append([path.name for path in plugin_dirs])
            assert all(len(path.name) == 120 for path in plugin_dirs)
            assert all((path / "index.md").exists() for path in plugin_dirs)
        finally:
            plugin_pages._cleanup_source_files(app, None)

    assert generated_slugs[0] == generated_slugs[1]


def test_generated_files_do_not_overwrite_authored_content(tmp_path: Path):
    data_dir = tmp_path / "_data"
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
    path = tmp_path / "other" / "conda-example" / "index.md"
    path.parent.mkdir(parents=True)
    path.write_text("authored")
    app = type("App", (), {"srcdir": str(tmp_path)})()

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        plugin_pages._generate_source_files(app)

    assert path.read_text() == "authored"
    assert not (tmp_path / "other" / "index.md").exists()

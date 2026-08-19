"""Sphinx extension that generates per-plugin and per-category pages from plugins.json.

Generates real .md source files in the docs tree during ``builder-inited``
so that cross-references resolve normally. Files are cleaned up after build.

URL structure::

    solvers/
      index.md                      <- category page
      conda-libmamba-solver/
        index.md                    <- plugin page
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from docutils import nodes
from docutils.statemachine import StringList
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective

_GENERATED_DIRS: list[Path] = []
_GENERATED_FILES: list[Path] = []


_MARKDOWN_PUNCTUATION = re.compile(r"([!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~])")


def _markdown_text(value: object, limit: int | None = None) -> str:
    """Escape untrusted metadata for use as plain inline Markdown."""
    text = " ".join(str(value).split())
    if limit is not None and len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return _MARKDOWN_PUNCTUATION.sub(r"\\\1", text)


def _code_span(value: object) -> str:
    """Wrap arbitrary one-line text in a safe Markdown code span."""
    text = " ".join(str(value).split())
    longest_run = max((len(run) for run in re.findall(r"`+", text)), default=0)
    delimiter = "`" * (longest_run + 1)
    padding = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{delimiter}{padding}{text}{padding}{delimiter}"


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _load_plugins(app: Sphinx) -> dict[str, Any]:
    data_path = Path(app.srcdir) / "_data" / "plugins.json"
    if not data_path.exists():
        return {"categories": [], "plugins": []}
    data = json.loads(data_path.read_text())
    plugins = data.get("plugins", [])
    name_counts = Counter(_slugify(plugin["name"]) for plugin in plugins)
    for plugin in plugins:
        name_slug = _slugify(plugin["name"])
        if name_counts[name_slug] > 1:
            owner = plugin["repo_full_name"].split("/")[0]
            plugin["slug"] = f"{_slugify(owner)}-{name_slug}"
        else:
            plugin["slug"] = name_slug
    return data


_CATEGORY_ICONS = {
    "Solvers": "cpu",
    "Subcommands": "terminal",
    "Channels": "server",
    "Authentication": "shield-lock",
    "Environment management": "package",
    "Build tools": "tools",
    "UI and display": "paintbrush",
    "Other": "ellipsis",
}


def _render_plugin_page(plugin: dict) -> str:
    """Generate MyST markdown content for a single plugin page."""
    name = _markdown_text(plugin["name"])
    desc = _markdown_text(plugin["description"] or "No description available.")
    repo_url = plugin["repo_url"]
    repo_full_name = _markdown_text(plugin["repo_full_name"])
    stars = plugin["stars"]
    category = plugin["category"]
    docs = plugin.get("docs")
    if not isinstance(docs, str) or any(char.isspace() for char in docs):
        docs = None
    elif (parsed := urlsplit(docs)).scheme not in {"http", "https"} or not parsed.netloc:
        docs = None
    topics = plugin.get("topics", [])
    entry_points = plugin.get("entry_points", {})
    cat_icon = _CATEGORY_ICONS.get(category, "ellipsis")

    cols = 3 if docs else 2
    lines = [
        f"# {name}",
        "",
        desc,
        "",
        f"::::{{grid}} 1 1 {cols} {cols}",
        ":gutter: 3",
        "",
        f":::{{grid-item-card}} {{octicon}}`{cat_icon}` Category",
        f":link: ../",
        f"{category}",
        ":::",
        "",
        f":::{{grid-item-card}} {{octicon}}`mark-github` Repository",
        f":link: {repo_url}",
        f"{repo_full_name} ({stars} \u2b50)",
        ":::",
        "",
    ]
    if docs:
        lines.extend([
            f":::{{grid-item-card}} {{octicon}}`book` Documentation",
            f":link: {docs}",
            _markdown_text(docs),
            ":::",
            "",
        ])
    lines.append("::::")
    lines.append("")

    if topics:
        lines.append("**Topics:** " + ", ".join(_code_span(t) for t in topics))
        lines.append("")

    lines.append("---")
    lines.append("")

    if entry_points:
        lines.append(":::{dropdown} Entry points")
        lines.append(":icon: plug")
        lines.append("")
        for ep_name, ep_value in entry_points.items():
            lines.append(f"{_code_span(ep_name)} = {_code_span(ep_value)}")
            lines.append("")
        lines.append(":::")
        lines.append("")

    return "\n".join(lines)


def _render_category_page(category: str, plugins: list[dict]) -> str:
    """Generate MyST markdown content for a category index page."""
    sorted_plugins = sorted(plugins, key=lambda p: (-p["stars"], p["name"]))
    icon = _CATEGORY_ICONS.get(category, "ellipsis")
    count = len(plugins)
    lines = [
        f"# {{octicon}}`{icon}` {category}",
        "",
        f"{count} plugin{'s' if count != 1 else ''} in this category.",
        "",
        ":::::{grid} 1 1 2 2",
        ":gutter: 3",
        "",
    ]
    for p in sorted_plugins:
        desc = _markdown_text(p["description"] or "No description.", limit=120)
        name = _markdown_text(p["name"])
        repo_full_name = _markdown_text(p["repo_full_name"])
        lines.extend([
            f":::{{grid-item-card}} {name}",
            f":link: {p['slug']}/",
            "",
            desc,
            "",
            f"{{octicon}}`mark-github` {repo_full_name} ({p['stars']} \u2b50)",
            ":::",
            "",
        ])
    lines.append(":::::")
    lines.append("")
    lines.append("```{toctree}")
    lines.append(":hidden:")
    lines.append(":glob:")
    lines.append("")
    lines.append("*/index")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


class PluginListDirective(SphinxDirective):
    """Directive that renders the full plugin listing inline."""

    has_content = False
    required_arguments = 0

    def run(self) -> list[nodes.Node]:
        data = _load_plugins(self.env.app)
        plugins = data.get("plugins", [])
        if not plugins:
            para = nodes.paragraph(text="No plugin data available. Run the render script first.")
            return [para]

        content = [
            "| Name | Description | Category | Stars |",
            "|------|-------------|----------|------:|",
        ]
        for p in sorted(plugins, key=lambda p: (-p["stars"], p["name"])):
            cat_slug = _slugify(p["category"])
            content.append(
                f'| [{_markdown_text(p["name"])}]({cat_slug}/{p["slug"]}/index) '
                f'| {_markdown_text(p["description"], limit=80)} '
                f'| [{p["category"]}]({cat_slug}/index) '
                f'| {p["stars"]} |'
            )

        container = nodes.container()
        self.state.nested_parse(
            StringList(content, source="plugin-list"),
            self.content_offset,
            container,
        )
        return [container]


def _generate_source_files(app: Sphinx) -> None:
    """Write per-plugin and per-category .md files into the source tree."""
    data = _load_plugins(app)
    plugins = data.get("plugins", [])
    if not plugins:
        return

    src_dir = Path(app.srcdir)

    by_cat: dict[str, list[dict]] = {}
    for plugin in plugins:
        by_cat.setdefault(plugin["category"], []).append(plugin)

    rendered_files: list[tuple[Path, str]] = []

    for category in data.get("categories", []):
        cat_plugins = by_cat.get(category, [])
        if not cat_plugins:
            continue
        cat_slug = _slugify(category)
        cat_dir = src_dir / cat_slug
        category_file = cat_dir / "index.md"
        rendered_files.append(
            (category_file, _render_category_page(category, cat_plugins))
        )

        for plugin in cat_plugins:
            plugin_dir = cat_dir / plugin["slug"]
            plugin_file = plugin_dir / "index.md"
            rendered_files.append((plugin_file, _render_plugin_page(plugin)))

    paths = [path for path, _ in rendered_files]
    if len(paths) != len(set(paths)):
        raise RuntimeError("Generated plugin documentation paths are not unique")
    if existing := next((path for path in paths if path.exists()), None):
        raise FileExistsError(f"Refusing to overwrite existing documentation: {existing}")

    for path, content in rendered_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        _GENERATED_FILES.append(path)
        if path.parent not in _GENERATED_DIRS:
            _GENERATED_DIRS.append(path.parent)


def _cleanup_source_files(app: Sphinx, exception: Exception | None) -> None:
    """Remove generated .md files after build completes."""
    for path in _GENERATED_FILES:
        path.unlink(missing_ok=True)
    for directory in reversed(_GENERATED_DIRS):
        try:
            directory.rmdir()
        except OSError:
            pass
    _GENERATED_FILES.clear()
    _GENERATED_DIRS.clear()


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_directive("plugin-list", PluginListDirective)
    app.connect("builder-inited", _generate_source_files)
    app.connect("build-finished", _cleanup_source_files)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }

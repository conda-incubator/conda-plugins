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
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from docutils import nodes
from docutils.statemachine import StringList
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective

_GENERATED_DIRS: list[Path] = []


def _clean_readme(text: str, repo_url: str) -> str:
    """Prepare a README excerpt for embedding in a plugin page.

    Demotes headings by two levels (# -> ###) to avoid clashing with the
    page title, strips badge image lines, rewrites relative links to point
    back to the source repo.
    """
    blob_base = repo_url.rstrip("/") + "/blob/main/"
    tree_base = repo_url.rstrip("/") + "/tree/main/"

    def _rewrite_link(m: re.Match) -> str:
        label, target = m.group(1), m.group(2)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return m.group(0)
        if target.startswith("./"):
            target = target[2:]
        base = tree_base if target.endswith("/") else blob_base
        return f"[{label}]({base}{target})"

    lines = []
    for line in text.splitlines():
        if re.match(r"^\s*(\[!\[|<a\s|<img\s|!\[)", line):
            continue
        if re.match(r"^\s*\|.*\[!\[", line):
            continue
        if re.match(r"^\s*\|\s*---", line) and not lines:
            continue
        if line.startswith("#"):
            line = "##" + line
        line = re.sub(r"\[([^\]]*)\]\(([^)]+)\)", _rewrite_link, line)
        lines.append(line)
    return "\n".join(lines).strip()


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _assign_slugs(plugins: list[dict]) -> None:
    """Assign a short URL slug to each plugin, using owner prefix only for collisions."""
    name_counts = Counter(_slugify(p["name"]) for p in plugins)
    for plugin in plugins:
        name_slug = _slugify(plugin["name"])
        if name_counts[name_slug] > 1:
            owner = plugin["repo_full_name"].split("/")[0]
            plugin["slug"] = f"{_slugify(owner)}-{name_slug}"
        else:
            plugin["slug"] = name_slug


def _load_plugins(app: Sphinx) -> dict[str, Any]:
    data_path = Path(app.srcdir) / "_data" / "plugins.json"
    if not data_path.exists():
        return {"categories": [], "plugins": []}
    data = json.loads(data_path.read_text())
    _assign_slugs(data.get("plugins", []))
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
    name = plugin["name"]
    desc = plugin["description"] or "No description available."
    repo_url = plugin["repo_url"]
    repo_full_name = plugin["repo_full_name"]
    stars = plugin["stars"]
    category = plugin["category"]
    docs = plugin.get("docs")
    topics = plugin.get("topics", [])
    entry_points = plugin.get("entry_points", {})
    readme = plugin.get("readme", "")
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
            f"{docs}",
            ":::",
            "",
        ])
    lines.append("::::")
    lines.append("")

    if topics:
        lines.append("**Topics:** " + ", ".join(f"`{t}`" for t in topics))
        lines.append("")

    lines.append("---")
    lines.append("")

    if readme:
        lines.append(_clean_readme(readme, repo_url))
        lines.append("")

    if entry_points:
        lines.append(":::{dropdown} Entry points")
        lines.append(":icon: plug")
        lines.append("")
        for ep_name, ep_value in entry_points.items():
            lines.append(f"`{ep_name}` = `{ep_value}`")
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
        desc = (p["description"] or "No description.")[:120]
        lines.extend([
            f":::{{grid-item-card}} {p['name']}",
            f":link: {p['slug']}/",
            "",
            desc,
            "",
            f"{{octicon}}`mark-github` {p['repo_full_name']} ({p['stars']} \u2b50)",
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
                f'| [{p["name"]}]({cat_slug}/{p["slug"]}/index) '
                f'| {p["description"][:80]} '
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

    generated_dirs: list[Path] = []

    for category in data.get("categories", []):
        cat_plugins = by_cat.get(category, [])
        if not cat_plugins:
            continue
        cat_slug = _slugify(category)
        cat_dir = src_dir / cat_slug
        cat_dir.mkdir(parents=True, exist_ok=True)
        (cat_dir / "index.md").write_text(
            _render_category_page(category, cat_plugins)
        )
        generated_dirs.append(cat_dir)

        for plugin in cat_plugins:
            plugin_dir = cat_dir / plugin["slug"]
            plugin_dir.mkdir(parents=True, exist_ok=True)
            (plugin_dir / "index.md").write_text(_render_plugin_page(plugin))

    _GENERATED_DIRS.extend(generated_dirs)


def _cleanup_source_files(app: Sphinx, exception: Exception | None) -> None:
    """Remove generated .md files after build completes."""
    for d in _GENERATED_DIRS:
        shutil.rmtree(d, ignore_errors=True)
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

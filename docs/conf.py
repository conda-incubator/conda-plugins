"""Sphinx configuration for conda-plugins documentation."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath("_ext"))

project = html_title = "conda-plugins"
copyright = "2026, conda community"
author = "conda community"

extensions = [
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_sitemap",
    "plugin_pages",
]

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "tasklist",
]

html_theme = "conda_sphinx_theme"

html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/conda/conda-plugins",
            "icon": "fa-brands fa-square-github",
            "type": "fontawesome",
        },
    ],
}

html_context = {
    "github_user": "conda",
    "github_repo": "conda-plugins",
    "github_version": "main",
    "doc_path": "docs",
}

html_static_path = ["_static"]
html_css_files = ["css/custom.css"]

html_baseurl = "https://conda.github.io/conda-plugins/"

exclude_patterns = ["_build"]

suppress_warnings = [
    "myst.header",
    "misc.highlighting_failure",
]

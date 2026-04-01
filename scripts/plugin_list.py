"""Discover conda plugins on GitHub, categorize them, and generate data files.

Outputs:
  - README.md table (between PLUGIN_LIST markers)
  - docs/_data/plugins.json (rich metadata for Sphinx)
  - scripts/categories.toml (updated with new classifications)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import tomllib
from base64 import b64decode
from datetime import datetime, timezone
from pathlib import Path

import github
from github import GithubException

RETRY_WAIT = 60
MAX_RETRIES = 5
DELAY_BETWEEN_RESULTS = 2

SCRIPT_DIR = Path(__file__).resolve().parent
CATEGORIES_PATH = SCRIPT_DIR / "categories.toml"
DATA_DIR = SCRIPT_DIR.parent / "docs" / "_data"

VALID_CATEGORIES = [
    "Solvers",
    "Subcommands",
    "Channels",
    "Authentication",
    "Environment management",
    "Build tools",
    "UI and display",
    "Other",
]

KEYWORD_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsolv(er|ing|e)\b", re.I), "Solvers"),
    (re.compile(r"\bauth(entication|enticate|orize|oriz)?\b", re.I), "Authentication"),
    (re.compile(r"\bchannel\b", re.I), "Channels"),
    (re.compile(r"\brepodata\b", re.I), "Channels"),
    (re.compile(r"\bbuild\b.*\bpackage", re.I), "Build tools"),
    (re.compile(r"\bindex(ing|er)?\b.*\bpackage", re.I), "Build tools"),
    (re.compile(r"\bconvert\b.*\b\.conda\b", re.I), "Build tools"),
    (re.compile(r"\bsubcommand\b", re.I), "Subcommands"),
    (re.compile(r"\b(tui|text.user.interface|rich|display)\b", re.I), "UI and display"),
    (re.compile(r"\bprotect\b", re.I), "Environment management"),
    (re.compile(r"\blockfile\b", re.I), "Environment management"),
    (re.compile(r"\bactivat(e|ion)\b", re.I), "Environment management"),
    (re.compile(r"\benvironment\b", re.I), "Environment management"),
    (re.compile(r"\bvirtual.package\b", re.I), "Environment management"),
]


def _api_call(fn, label=""):
    """Call *fn* with retries on rate limit (HTTP 429/403) errors."""
    for attempt in range(MAX_RETRIES):
        try:
            return fn()
        except GithubException as exc:
            if exc.status in (403, 429):
                wait = RETRY_WAIT * (attempt + 1)
                print(
                    f"  Rate limited ({exc.status}) on {label}, "
                    f"waiting {wait}s (attempt {attempt + 1}/{MAX_RETRIES})",
                    file=sys.stderr,
                )
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Exceeded {MAX_RETRIES} retries for {label}")


def _get_page_results(search_results):
    """Yield results one at a time, retrying on rate limit during pagination."""
    page = 0
    while True:
        items = _api_call(
            lambda p=page: search_results.get_page(p),
            label=f"search page {page}",
        )
        if not items:
            break
        yield from items
        page += 1
        time.sleep(DELAY_BETWEEN_RESULTS)


def _fetch_readme(repo) -> str:
    """Fetch the repo README as text, returning empty string on failure."""
    try:
        readme = _api_call(lambda: repo.get_readme(), label=f"{repo.full_name}/README")
        return b64decode(readme.content).decode(errors="replace")
    except Exception:
        return ""


def _fetch_topics(repo) -> list[str]:
    """Fetch repo topics, returning empty list on failure."""
    try:
        return _api_call(lambda: repo.get_topics(), label=f"{repo.full_name}/topics")
    except Exception:
        return []


def search_github():
    token = os.environ.get("GITHUB_TOKEN")
    auth = github.Auth.Token(token) if token else None
    gh = github.Github(auth=auth, per_page=30)
    query = '"[project.entry-points.conda]" language:TOML'
    results = gh.search_code(query)
    total = _api_call(lambda: results.totalCount, label="search totalCount")
    if not total:
        raise RuntimeError("Did not find any results")
    print(f"Found {total} results", file=sys.stderr)
    return results


def discover_plugins(search_results, categories: dict[str, str]):
    """Yield plugin dicts with rich metadata from GitHub search results.

    Skips README and topics fetches for repos that already have explicit
    category mappings, since those fields are only needed for classification.
    """
    seen_repos = set()
    for result in _get_page_results(search_results):
        if result.name != "pyproject.toml":
            continue

        repo = result.repository
        repo_full_name = repo.full_name
        if repo_full_name in seen_repos:
            continue
        seen_repos.add(repo_full_name)

        if repo.fork:
            continue

        try:
            content = _api_call(
                lambda r=result: r.decoded_content.decode(),
                label=repo_full_name,
            )
            toml_data = tomllib.loads(content)
        except tomllib.TOMLDecodeError:
            print(f"! Couldn't decode {repo_full_name}", file=sys.stderr)
            continue
        except RuntimeError as exc:
            print(f"! Skipping {repo_full_name}: {exc}", file=sys.stderr)
            continue

        project = toml_data.get("project", {})
        needs_classification = repo_full_name not in categories

        plugin = {
            "name": project.get("name") or repo.name,
            "description": project.get("description") or repo.description or "",
            "repo_url": repo.html_url,
            "repo_full_name": repo_full_name,
            "stars": repo.stargazers_count,
            "docs": project.get("urls", {}).get("documentation"),
            "entry_points": project.get("entry-points", {}).get("conda", {}),
            "topics": _fetch_topics(repo) if needs_classification else [],
            "readme": _fetch_readme(repo) if needs_classification else "",
        }
        print(f"Processed {repo_full_name}", file=sys.stderr)
        time.sleep(DELAY_BETWEEN_RESULTS)
        yield plugin


def deduplicate_plugins(plugins: list[dict]) -> list[dict]:
    """When multiple repos ship the same plugin name, keep only the most-starred."""
    by_name: dict[str, list[dict]] = {}
    for p in plugins:
        by_name.setdefault(p["name"], []).append(p)
    result = []
    for name, group in by_name.items():
        winner = max(group, key=lambda p: p["stars"])
        if len(group) > 1:
            dropped = [p["repo_full_name"] for p in group if p is not winner]
            print(
                f"  Dedup: keeping {winner['repo_full_name']} for {name!r}, "
                f"dropping {', '.join(dropped)}",
                file=sys.stderr,
            )
        result.append(winner)
    return result


def load_categories() -> dict[str, str]:
    """Load the repo -> category mapping from categories.toml."""
    if not CATEGORIES_PATH.exists():
        return {}
    with open(CATEGORIES_PATH, "rb") as f:
        data = tomllib.load(f)
    return data.get("categories", {})


def save_categories(categories: dict[str, str]) -> None:
    """Write the category mapping back to categories.toml."""
    lines = [
        "# Category assignments for conda plugins.",
        "# Keys are GitHub \"owner/repo\" identifiers; values are one of:",
        "#   Solvers, Subcommands, Channels, Authentication,",
        "#   Environment management, Build tools, UI and display, Other",
        "",
        "[categories]",
    ]
    by_cat: dict[str, list[str]] = {}
    for repo, cat in sorted(categories.items()):
        by_cat.setdefault(cat, []).append(repo)
    for cat in VALID_CATEGORIES:
        repos = by_cat.get(cat, [])
        if not repos:
            continue
        lines.append(f"# {cat}")
        for repo in sorted(repos):
            lines.append(f'"{repo}" = "{cat}"')
        lines.append("")
    CATEGORIES_PATH.write_text("\n".join(lines) + "\n")


def _keyword_classify(plugin: dict) -> str | None:
    """Return a category based on keyword matching, or None if ambiguous."""
    text = " ".join([
        plugin.get("name", ""),
        plugin.get("description", ""),
        " ".join(plugin.get("entry_points", {}).keys()),
        plugin.get("readme", ""),
    ])
    for pattern, category in KEYWORD_RULES:
        if pattern.search(text):
            return category
    return None


def _llm_classify(plugin: dict, model: str | None = None) -> str | None:
    """Use the llm CLI to classify a plugin. Returns None on failure."""
    prompt = (
        "Classify this conda plugin into exactly one category.\n"
        f"Categories: {', '.join(VALID_CATEGORIES)}\n\n"
        f"Name: {plugin['name']}\n"
        f"Description: {plugin['description']}\n"
        f"Entry points: {', '.join(plugin.get('entry_points', {}).keys()) or 'unknown'}\n"
        f"Topics: {', '.join(plugin.get('topics', [])) or 'none'}\n"
        f"README excerpt: {plugin.get('readme', '')[:1000]}\n\n"
        "Reply with ONLY the category name, nothing else."
    )
    cmd = ["llm", "prompt", "--no-log", prompt]
    if model:
        cmd.extend(["-m", model])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"  llm failed for {plugin['name']}: {result.stderr.strip()}", file=sys.stderr)
            return None
        answer = result.stdout.strip()
        for cat in VALID_CATEGORIES:
            if cat.lower() in answer.lower():
                return cat
        print(f"  llm returned unrecognized category for {plugin['name']}: {answer!r}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("  llm command not found, skipping LLM classification", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print(f"  llm timed out for {plugin['name']}", file=sys.stderr)
        return None


def categorize_plugin(
    plugin: dict,
    categories: dict[str, str],
    *,
    model: str | None = None,
    skip_llm: bool = False,
) -> str:
    """Return the category for a plugin using the three-tier approach."""
    repo = plugin["repo_full_name"]

    if repo in categories:
        return categories[repo]

    if cat := _keyword_classify(plugin):
        print(f"  Keyword-classified {repo} as {cat}", file=sys.stderr)
        categories[repo] = cat
        return cat

    if not skip_llm:
        if cat := _llm_classify(plugin, model=model):
            print(f"  LLM-classified {repo} as {cat}", file=sys.stderr)
            categories[repo] = cat
            return cat

    categories[repo] = "Other"
    return "Other"


def generate_readme_table(plugins: list[dict]) -> str:
    """Generate the markdown table for README.md."""
    lines = [
        "| Name | Description | \u2b50 |",
        "|------|-------------|--:|",
    ]
    for p in sorted(plugins, key=lambda p: (-p["stars"], p["name"])):
        lines.append(f'| [{p["name"]}]({p["repo_url"]}) | {p["description"]} | {p["stars"]} |')
    lines.append("")
    return "\n".join(lines)


def generate_json(plugins: list[dict]) -> str:
    """Generate the JSON data file content."""
    clean = []
    for p in sorted(plugins, key=lambda p: (-p["stars"], p["name"])):
        clean.append({
            "name": p["name"],
            "description": p["description"],
            "repo_url": p["repo_url"],
            "repo_full_name": p["repo_full_name"],
            "stars": p["stars"],
            "docs": p.get("docs"),
            "topics": p.get("topics", []),
            "entry_points": p.get("entry_points", {}),
            "category": p["category"],
            "readme": p.get("readme", ""),
        })
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "categories": VALID_CATEGORIES,
        "plugins": clean,
    }
    return json.dumps(data, indent=2) + "\n"


def rerender_readme(path: str, table: str) -> None:
    """Replace the PLUGIN_LIST section in README.md."""
    text = Path(path).read_text()
    start = "<!-- PLUGIN_LIST -->\n"
    end = "\n<!-- PLUGIN_LIST -->"
    before = text[: text.index(start) + len(start)]
    after = text[text.index(end) :]
    Path(path).write_text(before + table + after)


def main():
    parser = argparse.ArgumentParser(description="Render conda plugin index")
    parser.add_argument("readme", nargs="?", default="README.md", help="Path to README.md")
    parser.add_argument("--model", default=None, help="LLM model override for categorization")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM classification entirely")
    args = parser.parse_args()

    categories = load_categories()
    print(f"Loaded {len(categories)} category mappings", file=sys.stderr)

    plugins = list(discover_plugins(search_github(), categories))
    plugins = deduplicate_plugins(plugins)

    for plugin in plugins:
        plugin["category"] = categorize_plugin(
            plugin, categories, model=args.model, skip_llm=args.skip_llm,
        )

    save_categories(categories)
    print(f"Saved {len(categories)} category mappings", file=sys.stderr)

    readme_table = generate_readme_table(plugins)
    rerender_readme(args.readme, readme_table)
    print(f"Updated {args.readme}", file=sys.stderr)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json_path = DATA_DIR / "plugins.json"
    json_path.write_text(generate_json(plugins))
    print(f"Wrote {json_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

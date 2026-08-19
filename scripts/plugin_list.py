"""Discover conda plugins on GitHub, categorize them, and generate data files.

Outputs:
  - README.md table (between PLUGIN_LIST markers)
  - docs/_data/plugins.json (rich metadata for Sphinx)

Category assignments are read from scripts/categories.toml and changed only
through review.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import time
import tomllib
from itertools import islice
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import github
from github import GithubException

RETRY_WAIT = 60
MAX_RETRIES = 5
DELAY_BETWEEN_RESULTS = 2

SCRIPT_DIR = Path(__file__).resolve().parent
CATEGORIES_PATH = SCRIPT_DIR / "categories.toml"
DATA_DIR = SCRIPT_DIR.parent / "docs" / "_data"

MODEL_NAME = "Qwen3.5-2B-Q4_K_M.gguf"
MODEL_URL = (
    "https://huggingface.co/unsloth/Qwen3.5-2B-GGUF/resolve/"
    "f6d5376be1edb4d416d56da11e5397a961aca8ae/"
    f"{MODEL_NAME}"
)
MODEL_SHA256 = "aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223"

SEARCH_QUERIES = (
    '"[project.entry-points.conda]" language:TOML',
    r'"[project.entry-points.\"conda\"]" language:TOML',
)

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

MARKDOWN_PUNCTUATION = re.compile(r"([!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~])")


def bounded_prompt_text(value: object, limit: int) -> str:
    """Collapse whitespace and limit untrusted model input by UTF-8 bytes."""
    return " ".join(str(value).split()).encode()[:limit].decode(errors="ignore")


class PluginClassifier:
    """Classify unmapped plugins with a pinned local open-weights model."""

    grammar = (
        'root ::= "Solvers" | "Subcommands" | "Channels" | '
        '"Authentication" | "Environment management" | "Build tools" | '
        '"UI and display" | "Other"'
    )
    guide = """Choose the category matching the plugin's primary purpose.
Solvers: dependency-solving engines.
Subcommands: a new conda CLI command whose purpose does not fit another category.
Channels: channel, repository, repodata, package mirroring, or package serving.
Authentication: login, credentials, tokens, or request authentication.
Environment management: creating, modifying, locking, protecting, or activating environments.
Build tools: building or indexing packages.
UI and display: terminal interfaces, output formatting, or reporter backends.
Other: none of the above.

Examples:
"Fast dependency resolution using SAT" -> Solvers
"Print a random greeting from conda" -> Subcommands
"Serve repodata from a custom package repository" -> Channels
"Log in with OAuth and attach access tokens" -> Authentication
"Create environments from lockfiles" -> Environment management
"Build conda packages from recipes" -> Build tools
"Render conda output using a rich terminal UI" -> UI and display
"Send anonymous product analytics" -> Other"""

    def __init__(self) -> None:
        from llama_cpp import Llama

        cache_root = Path(
            os.environ.get(
                "CONDA_PLUGINS_MODEL_DIR",
                Path.home() / ".cache" / "conda-plugins" / "models",
            )
        )
        cache_root.mkdir(parents=True, exist_ok=True)
        model_path = cache_root / MODEL_NAME
        valid_cache = False
        if model_path.exists():
            with model_path.open("rb") as model_file:
                valid_cache = (
                    hashlib.file_digest(model_file, "sha256").hexdigest()
                    == MODEL_SHA256
                )
        if not valid_cache:
            partial_path = model_path.with_suffix(".download")
            partial_path.unlink(missing_ok=True)
            print(f"Downloading {MODEL_NAME}", file=sys.stderr)
            try:
                request = Request(MODEL_URL, headers={"User-Agent": "conda-plugins"})
                with urlopen(request, timeout=300) as response, partial_path.open("wb") as target:
                    shutil.copyfileobj(response, target)
                with partial_path.open("rb") as model_file:
                    digest = hashlib.file_digest(model_file, "sha256").hexdigest()
                if digest != MODEL_SHA256:
                    raise RuntimeError(
                        f"Checksum mismatch for {MODEL_NAME}: "
                        f"expected {MODEL_SHA256}, got {digest}"
                    )
                partial_path.replace(model_path)
            finally:
                partial_path.unlink(missing_ok=True)

        self.model = Llama(
            model_path=str(model_path),
            n_ctx=2048,
            n_threads=min(4, os.cpu_count() or 1),
            verbose=False,
        )

    def classify(self, plugin: dict) -> str:
        from llama_cpp import LlamaGrammar

        entry_points = ", ".join(
            f"{bounded_prompt_text(name, 20)} = {bounded_prompt_text(target, 56)}"
            for name, target in islice(plugin.get("entry_points", {}).items(), 3)
        )
        topics = ", ".join(
            bounded_prompt_text(topic, 20)
            for topic in islice(plugin.get("topics", []), 4)
        )
        prompt = f"""{self.guide}

Classify this plugin:
Name: {bounded_prompt_text(plugin['name'], 48)}
Description: {bounded_prompt_text(plugin['description'], 240)}
Entry points: {entry_points or 'none'}
Topics: {topics or 'none'}

Reply with ONLY the category name."""
        result = self.model.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            seed=42,
            max_tokens=16,
            grammar=LlamaGrammar.from_string(self.grammar, verbose=False),
        )
        category = result["choices"][0]["message"]["content"].strip()
        if category not in VALID_CATEGORIES:
            raise RuntimeError(f"Model returned an invalid category: {category!r}")
        return category


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


def search_github(gh):
    """Yield code-search results for both valid conda entry-point headers."""
    found = False
    for query in SEARCH_QUERIES:
        results = gh.search_code(query)
        total = _api_call(lambda: results.totalCount, label=f"search totalCount for {query}")
        print(f"Found {total} results for {query}", file=sys.stderr)
        page = 0
        while True:
            items = _api_call(
                lambda p=page: results.get_page(p),
                label=f"search page {page}",
            )
            if not items:
                break
            found = True
            yield from items
            page += 1
            time.sleep(DELAY_BETWEEN_RESULTS)
    if not found:
        raise RuntimeError("Did not find any results")


def discover_plugins(search_results):
    """Yield plugin dicts with metadata from root-level projects."""
    seen_repos: set[str] = set()
    for result in search_results:
        # The index deliberately covers one installable project per repository.
        # Nested examples and monorepo members need a separate indexing design.
        if result.path != "pyproject.toml":
            continue

        repo = result.repository
        repo_full_name = repo.full_name
        if repo_full_name in seen_repos:
            continue

        if repo.fork or repo.private:
            continue

        try:
            content = _api_call(
                lambda r=result: r.decoded_content.decode(),
                label=repo_full_name,
            )
            toml_data = tomllib.loads(content)
        except (tomllib.TOMLDecodeError, UnicodeError):
            print(f"! Couldn't decode {repo_full_name}", file=sys.stderr)
            continue
        except (GithubException, RuntimeError):
            # Publishing a partial snapshot would silently remove a plugin.
            # Let the workflow retry on its next run instead.
            raise

        project = toml_data.get("project")
        if not isinstance(project, dict):
            continue
        entry_point_groups = project.get("entry-points", {})
        if not isinstance(entry_point_groups, dict):
            continue
        entry_points = entry_point_groups.get("conda")
        if (
            not isinstance(entry_points, dict)
            or not entry_points
            or any(
                not isinstance(name, str) or not isinstance(target, str)
                for name, target in entry_points.items()
            )
        ):
            continue

        seen_repos.add(repo_full_name)

        name = project.get("name") or repo.name
        if not isinstance(name, str) or not re.fullmatch(
            r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?", name
        ):
            print(f"! Skipping {repo_full_name}: invalid project name {name!r}", file=sys.stderr)
            continue

        description = project.get("description") or repo.description or ""
        if not isinstance(description, str):
            description = ""
        urls = project.get("urls", {})
        docs = None
        if isinstance(urls, dict):
            docs = next(
                (
                    value
                    for key, value in urls.items()
                    if str(key).casefold() == "documentation"
                ),
                None,
            )
        if not isinstance(docs, str) or any(char.isspace() for char in docs):
            docs = None
        elif (parsed := urlsplit(docs)).scheme not in {"http", "https"} or not parsed.netloc:
            docs = None

        plugin = {
            "name": name,
            "description": description,
            "repo_url": repo.html_url,
            "repo_full_name": repo_full_name,
            "stars": repo.stargazers_count,
            "docs": docs,
            "entry_points": entry_points,
            "topics": _api_call(
                lambda: repo.get_topics(),
                label=f"{repo.full_name}/topics",
            ),
        }
        print(f"Processed {repo_full_name}", file=sys.stderr)
        time.sleep(DELAY_BETWEEN_RESULTS)
        yield plugin


def revalidate_missing_plugins(
    gh,
    plugins: list[dict],
    reviewed_repos: set[str] | None = None,
) -> list[dict]:
    """Directly check known repositories omitted by GitHub code search."""
    data_path = DATA_DIR / "plugins.json"
    previous = (
        json.loads(data_path.read_text()).get("plugins", [])
        if data_path.exists()
        else []
    )
    known_repos = list(
        dict.fromkeys(
            [
                *(plugin.get("repo_full_name") for plugin in previous),
                *(reviewed_repos or set()),
            ]
        )
    )
    found_repos = {plugin["repo_full_name"] for plugin in plugins}
    for repo_full_name in known_repos:
        if not isinstance(repo_full_name, str) or repo_full_name in found_repos:
            continue
        try:
            repo = _api_call(
                lambda name=repo_full_name: gh.get_repo(name),
                label=repo_full_name,
            )
            if repo.private or repo.fork or repo.full_name in found_repos:
                continue
            content = _api_call(
                lambda r=repo: r.get_contents("pyproject.toml"),
                label=f"{repo_full_name}/pyproject.toml",
            )
        except GithubException as exc:
            if exc.status == 404:
                continue
            raise
        if isinstance(content, list):
            continue
        restored = list(
            discover_plugins(
                [
                    SimpleNamespace(
                        path=content.path,
                        repository=repo,
                        decoded_content=content.decoded_content,
                    )
                ]
            )
        )
        if restored:
            print(
                f"Restored {restored[0]['repo_full_name']} after search omission",
                file=sys.stderr,
            )
            plugins.extend(restored)
            found_repos.add(restored[0]["repo_full_name"])
    return plugins


def deduplicate_plugins(plugins: list[dict]) -> list[dict]:
    """When multiple repos ship the same plugin name, keep only the most-starred."""
    by_name: dict[str, list[dict]] = {}
    for p in plugins:
        normalized_name = re.sub(r"[-_.]+", "-", p["name"]).lower()
        by_name.setdefault(normalized_name, []).append(p)
    result = []
    for name, group in by_name.items():
        winner = sorted(group, key=lambda p: (-p["stars"], p["repo_full_name"]))[0]
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
    categories = data.get("categories", {})
    if not isinstance(categories, dict):
        raise ValueError(f"{CATEGORIES_PATH} must contain a [categories] table")
    invalid = {repo: cat for repo, cat in categories.items() if cat not in VALID_CATEGORIES}
    if invalid:
        raise ValueError(f"Invalid category assignments: {invalid}")
    return categories


def categorize_plugin(
    plugin: dict,
    categories: dict[str, str],
    classifier: PluginClassifier | None = None,
) -> str:
    """Return a reviewed category or an ephemeral model suggestion."""
    repo = plugin["repo_full_name"]

    if repo in categories:
        return categories[repo]

    return classifier.classify(plugin) if classifier else "Other"


def generate_readme_table(plugins: list[dict]) -> str:
    """Generate the markdown table for README.md."""
    lines = [
        "| Name | Description | \u2b50 |",
        "|------|-------------|--:|",
    ]
    for p in sorted(plugins, key=lambda p: (-p["stars"], p["name"])):
        description = MARKDOWN_PUNCTUATION.sub(
            r"\\\1",
            " ".join(str(p["description"]).split()),
        )
        lines.append(
            f'| [{p["name"]}]({p["repo_url"]}) | '
            f'{description} | {p["stars"]} |'
        )
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
        })
    data = {
        "categories": VALID_CATEGORIES,
        "plugins": clean,
    }
    return json.dumps(data, indent=2) + "\n"


def rerender_readme(path: str, table: str) -> None:
    """Replace the PLUGIN_LIST section in README.md."""
    text = Path(path).read_text()
    marker = "<!-- PLUGIN_LIST -->"
    positions = [match.start() for match in re.finditer(re.escape(marker), text)]
    if len(positions) != 2:
        raise ValueError(f"Expected exactly two {marker} markers in {path}")
    before = text[: positions[0] + len(marker)]
    after = text[positions[1] :]
    Path(path).write_text(before + "\n" + table + after)


def main():
    readme = sys.argv[1] if len(sys.argv) > 1 else "README.md"
    token = os.environ.get("GITHUB_TOKEN")
    auth = github.Auth.Token(token) if token else None
    gh = github.Github(auth=auth, per_page=30)

    categories = load_categories()
    print(f"Loaded {len(categories)} category mappings", file=sys.stderr)

    plugins = list(discover_plugins(search_github(gh)))
    plugins = revalidate_missing_plugins(gh, plugins, set(categories))
    plugins = deduplicate_plugins(plugins)
    classifier = (
        PluginClassifier()
        if any(plugin["repo_full_name"] not in categories for plugin in plugins)
        else None
    )

    for plugin in plugins:
        plugin["category"] = categorize_plugin(plugin, categories, classifier)

    readme_table = generate_readme_table(plugins)
    rerender_readme(readme, readme_table)
    print(f"Updated {readme}", file=sys.stderr)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json_path = DATA_DIR / "plugins.json"
    json_path.write_text(generate_json(plugins))
    print(f"Wrote {json_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

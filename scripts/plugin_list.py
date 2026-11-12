"""Discover conda plugins on GitHub, categorize them, and generate data files.

Output: docs/_data/plugins.json (metadata for Sphinx). The site is the index,
so README.md is no longer regenerated.

Category assignments are read from scripts/categories.toml and changed only
through review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
import tomllib
from collections.abc import Callable, Iterable, Iterator, Mapping
from datetime import UTC, datetime
from itertools import islice
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import github
from github import GithubException

if TYPE_CHECKING:
    from typing import TypeVar

    from github.ContentFile import ContentFile

    T = TypeVar("T")

RETRY_WAIT = 60
MAX_RETRIES = 5
# A rate limit that will not clear within this run is not worth sleeping for
MAX_WAIT = 120

# Code search allows 10 requests per minute for authenticated callers. A run
# needs a handful of them, so pages are only spaced a little; a burst that does
# hit the limit is handled by the header-aware retry in _api_call. Other calls
# draw on the 5000/hour core budget and need no delay at all.
SEARCH_DELAY = 1

# A single search returns at most 1000 results, silently truncated past that
SEARCH_CAP_WARN = 500
SEARCH_CAP_ALERT = 900
# Requests results 100 at a time, which is the API maximum
SEARCH_PAGE_SIZE = 100

# Refuse to publish an index that lost this much of the previous snapshot
MAX_SHRINK = 0.25

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
    '"[project.entry-points.conda]" language:TOML path:/',
    r'"[project.entry-points.\"conda\"]" language:TOML path:/',
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


def _rate_limit_delay(headers: Mapping[str, str], attempt: int) -> tuple[float, datetime]:
    """Seconds to wait before retrying and the time the limit resets.

    GitHub answers a rate limit with ``retry-after`` seconds or with the epoch
    of the reset in ``x-ratelimit-reset``; both are preferred over guessing.
    """
    now = time.time()
    if retry_after := headers.get("retry-after"):
        try:
            wait = float(retry_after) + 1.0
        except ValueError:
            pass
        else:
            return wait, datetime.fromtimestamp(now + wait, tz=UTC)
    if reset := headers.get("x-ratelimit-reset"):
        reset_at = float(reset)
        return max(reset_at - now, 1.0) + 1.0, datetime.fromtimestamp(reset_at, tz=UTC)
    wait = float(RETRY_WAIT * (attempt + 1))
    return wait, datetime.fromtimestamp(now + wait, tz=UTC)


def is_reviewed(
    repo_full_name: str, repo_id: int | None, categories: Mapping[str, dict]
) -> bool:
    """True when categories.toml holds a reviewed entry for this repository.

    The immutable repository id is what makes the review durable: a renamed or
    re-created repository does not inherit it.
    """
    if repo_id is None:
        return False
    return categories.get(repo_full_name, {}).get("id") == repo_id


def _repository_metadata(repo: object, label: str) -> tuple[int, list[str]]:
    """Stars and topics, which the snapshot deliberately does not cache.

    A run happens weekly, so refreshing them each time keeps the published
    counts and the sort order current. Reading the star count completes the
    search result's minimal repository with one request, and that response also
    carries the topics, so no second request is needed.
    """
    stars = _api_call(lambda: repo.stargazers_count, label=f"{label}/stars")
    topics = getattr(repo, "topics", None)
    if topics is None:
        topics = _api_call(lambda: repo.get_topics(), label=f"{label}/topics")
    return stars, list(topics)


def _inaccessible(exc: GithubException) -> bool:
    """True when the token cannot read the repository at all.

    Covers private repos and SAML-enforced organizations. Those are skipped
    rather than failing the whole run.
    """
    return exc.status in {401, 403, 451}


def _not_found(exc: GithubException) -> bool:
    """True for a 404, which is either a missing file or a removed repository."""
    return exc.status == 404


def _api_call(fn: Callable[[], T], label: str = "") -> T:
    """Call *fn* with retries on rate limit (HTTP 429/403) errors."""
    for attempt in range(MAX_RETRIES):
        try:
            return fn()
        except GithubException as exc:
            headers = {
                str(key).casefold(): str(value)
                for key, value in (exc.headers or {}).items()
            }
            message = (
                str(exc.data.get("message", ""))
                if isinstance(exc.data, dict)
                else str(exc.data or "")
            ).casefold()
            rate_limited = exc.status == 429 or (
                exc.status == 403
                and (
                    headers.get("x-ratelimit-remaining") == "0"
                    or "retry-after" in headers
                    or "rate limit" in message
                )
            )
            if rate_limited:
                wait, resets = _rate_limit_delay(headers, attempt)
                moment = resets.strftime("%H:%M:%SZ")
                if wait > MAX_WAIT:
                    raise RuntimeError(
                        f"Rate limited on {label} until {moment} ({wait:.0f}s "
                        "away), longer than this run can wait; try again later"
                    ) from exc
                print(
                    f"  Rate limited ({exc.status}) on {label}, resets at "
                    f"{moment}, waiting {wait:.0f}s "
                    f"(attempt {attempt + 1}/{MAX_RETRIES})",
                    file=sys.stderr,
                )
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Exceeded {MAX_RETRIES} retries for {label}")


def search_github(gh: github.Github) -> Iterator[ContentFile]:
    """Yield code-search results for both valid conda entry-point headers.

    Code search allows 10 requests per minute for a shared bot identity, so the
    search spends as few of them as possible: no separate result count, and the
    last page ends the loop instead of asking for an empty one.
    """
    found = False
    page_size = gh.per_page
    for query in SEARCH_QUERIES:
        results = gh.search_code(query)
        page = 0
        collected = 0
        while True:
            if page:
                # a small gap between pages; _api_call handles any 429
                time.sleep(SEARCH_DELAY)
            items = _api_call(
                lambda p=page, search_results=results: search_results.get_page(p),
                label=f"search page {page}",
            )
            if not items:
                break
            found = True
            collected += len(items)
            yield from items
            if len(items) < page_size:
                break
            page += 1

        print(f"Found {collected} results for {query}", file=sys.stderr)
        if collected >= SEARCH_CAP_ALERT:
            print(
                f"! {query} returned {collected} results, at the 1000-result "
                "search cap; partition the query before results are dropped",
                file=sys.stderr,
            )
        elif collected >= SEARCH_CAP_WARN:
            print(
                f"! {query} returned {collected} results, half way to the search "
                "cap; plan a partitioned query",
                file=sys.stderr,
            )
    if not found:
        raise RuntimeError("Did not find any results")


def discover_plugins(
    search_results: Iterable[ContentFile],
    categories: dict[str, dict] | None = None,
    previous: dict[str, dict] | None = None,
) -> Iterator[dict]:
    """Yield plugin dicts with metadata from root-level projects.

    Repositories already in the previous snapshot whose pyproject.toml has not
    changed (same blob sha) are rebuilt from that snapshot instead of being
    fetched again; the search payload alone carries everything else needed.
    """
    seen_repos: set[str] = set()
    for result in search_results:
        # The index deliberately covers one installable project per repository.
        # Nested examples and monorepo members need a separate indexing design.
        if result.path != "pyproject.toml":
            continue

        repo_full_name = result.repository.full_name
        if repo_full_name in seen_repos:
            continue

        # Every attribute read below can trigger a request for a repository the
        # token cannot see (private, SAML-enforced), so the whole body is guarded.
        try:
            plugin = _plugin_from_result(result, categories, previous)
        except GithubException as exc:
            if _inaccessible(exc):
                print(
                    f"! Skipping {repo_full_name}: not readable with this token "
                    f"({exc.status}), e.g. private or SAML-enforced",
                    file=sys.stderr,
                )
                continue
            if _not_found(exc):
                print(
                    f"! Skipping {repo_full_name}: not found (404), e.g. no "
                    "root pyproject.toml or the repository was removed",
                    file=sys.stderr,
                )
                continue
            # Publishing a partial snapshot would silently remove a plugin.
            # Let the workflow retry on its next run instead.
            raise
        except (tomllib.TOMLDecodeError, UnicodeError):
            print(f"! Couldn't decode {repo_full_name}", file=sys.stderr)
            continue

        if plugin is not None:
            seen_repos.add(repo_full_name)
            yield plugin


def _search_payload(repo: object) -> dict:
    """The repository payload the search result already carries.

    PyGithub's public accessors (``raw_data`` and every attribute) call
    ``_completeIfNeeded()``, which issues a GET for a search result's minimal
    repository, so the private payload is read directly.
    """
    raw = getattr(repo, "_rawData", None)
    return raw if isinstance(raw, dict) else {}


def _plugin_from_result(
    result: object,
    categories: dict[str, dict] | None,
    previous: dict[str, dict] | None,
    content: str | None = None,
) -> dict | None:
    """Build one plugin record, or None when the result is not a plugin."""
    repo = result.repository
    payload = _search_payload(repo)

    def field(key, default=None):
        # never touch the Repository attribute when the payload has the value:
        # PyGithub would issue a GET to complete the object
        if key in payload:
            return payload[key]
        return getattr(repo, key, default)

    repo_full_name = field("full_name")
    if field("fork", False) or field("private", False):
        return None
    repo_id = field("id")
    repo_url = field("html_url")
    repo_description = field("description") or ""

    cached = (previous or {}).get(repo_full_name, {})
    # A snapshot only carries a usable docs value when it was written while the
    # plugin was reviewed; otherwise generate_json redacted it, so re-read.
    unchanged = (
        cached.get("reviewed") is True
        and result.sha == cached.get("pyproject_sha")
        and cached.get("entry_points")
    )
    if unchanged:
        stars, topics = _repository_metadata(repo, repo_full_name)
        print(f"Processed {repo_full_name} (unchanged)", file=sys.stderr)
        return {
            "name": cached["name"],
            "description": cached["description"],
            "repo_url": repo_url,
            "repo_full_name": repo_full_name,
            "repo_id": repo_id,
            "stars": stars,
            "docs": cached["docs"],
            "entry_points": cached["entry_points"],
            "topics": topics,
            "pyproject_sha": result.sha,
        }

    if content is None:
        content = _api_call(
            lambda r=result: r.decoded_content.decode(),
            label=repo_full_name,
        )
    toml_data = tomllib.loads(content)

    project = toml_data.get("project")
    if not isinstance(project, dict):
        return None
    entry_point_groups = project.get("entry-points", {})
    if not isinstance(entry_point_groups, dict):
        return None
    entry_points = entry_point_groups.get("conda")
    if (
        not isinstance(entry_points, dict)
        or not entry_points
        or any(
            not isinstance(name, str) or not isinstance(target, str)
            for name, target in entry_points.items()
        )
    ):
        return None

    name = project.get("name") or payload.get("name") or repo.name
    if not isinstance(name, str) or not re.fullmatch(
        r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?", name
    ):
        print(f"! Skipping {repo_full_name}: invalid project name {name!r}", file=sys.stderr)
        return None

    description = project.get("description") or repo_description
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

    stars, topics = _repository_metadata(repo, repo_full_name)

    print(f"Processed {repo_full_name}", file=sys.stderr)
    return {
        "name": name,
        "description": description,
        "repo_url": repo_url,
        "repo_full_name": repo_full_name,
        "repo_id": repo_id,
        "stars": stars,
        "docs": docs,
        "entry_points": entry_points,
        "topics": topics,
        "pyproject_sha": result.sha,
    }


def load_previous_plugins() -> dict[str, dict]:
    """Previous run's entries, keyed by repository name."""
    data_path = DATA_DIR / "plugins.json"
    if not data_path.exists():
        return {}
    try:
        data = json.loads(data_path.read_text())
    except ValueError:
        return {}
    return {
        plugin["repo_full_name"]: plugin
        for plugin in data.get("plugins", [])
        if isinstance(plugin, dict) and isinstance(plugin.get("repo_full_name"), str)
    }


def revalidate_missing_plugins(
    gh: github.Github,
    plugins: list[dict],
    reviewed_repos: set[str] | None = None,
    categories: dict[str, dict] | None = None,
) -> list[dict]:
    """Directly check known repositories omitted by GitHub code search."""
    previous_plugins = load_previous_plugins()
    previous = list(previous_plugins.values())
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
        # Everything below can request a repository the token cannot see.
        source = "repository"
        try:
            repo = _api_call(
                lambda name=repo_full_name: gh.get_repo(name),
                label=repo_full_name,
            )
            if repo.private or repo.fork or repo.full_name in found_repos:
                continue
            source = "pyproject.toml"
            content = _api_call(
                lambda r=repo: r.get_contents("pyproject.toml"),
                label=f"{repo_full_name}/pyproject.toml",
            )
            if isinstance(content, list):
                continue
            restored = _plugin_from_result(
                SimpleNamespace(
                    path=content.path,
                    repository=repo,
                    sha=content.sha,
                ),
                categories,
                previous_plugins,
                content=content.decoded_content.decode(),
            )
        except GithubException as exc:
            if source == "pyproject.toml" and _not_found(exc):
                print(
                    f"! Skipping {repo_full_name}: no pyproject.toml, "
                    "so it is not a plugin",
                    file=sys.stderr,
                )
                continue
            if not (_inaccessible(exc) or _not_found(exc)):
                raise
            print(
                f"! Skipping {repo_full_name}: not readable with this token "
                f"({exc.status}), e.g. private or SAML-enforced",
                file=sys.stderr,
            )
            continue
        except (tomllib.TOMLDecodeError, UnicodeError):
            continue

        if restored:
            print(
                f"Restored {restored['repo_full_name']} after search omission",
                file=sys.stderr,
            )
            plugins.append(restored)
            found_repos.add(restored["repo_full_name"])
    return plugins


def deduplicate_plugins(
    plugins: list[dict],
    reviewed_repos: dict[str, dict],
) -> list[dict]:
    """Prefer the reviewed repository ID, then stars, for duplicate names."""
    by_name: dict[str, list[dict]] = {}
    for p in plugins:
        normalized_name = re.sub(r"[-_.]+", "-", p["name"]).lower()
        by_name.setdefault(normalized_name, []).append(p)
    result = []
    for name, group in by_name.items():
        winner = min(
            group,
            key=lambda p: (
                reviewed_repos.get(p["repo_full_name"], {}).get("id")
                != p["repo_id"],
                -p["stars"],
                p["repo_full_name"],
            ),
        )
        if len(group) > 1:
            dropped = [p["repo_full_name"] for p in group if p is not winner]
            print(
                f"  Dedup: keeping {winner['repo_full_name']} for {name!r}, "
                f"dropping {', '.join(dropped)}",
                file=sys.stderr,
            )
        result.append(winner)
    return result


def load_categories() -> dict[str, dict]:
    """Load reviewed repository IDs and categories from categories.toml."""
    if not CATEGORIES_PATH.exists():
        return {}
    with open(CATEGORIES_PATH, "rb") as f:
        data = tomllib.load(f)
    categories = data.get("categories", {})
    if not isinstance(categories, dict):
        raise ValueError(f"{CATEGORIES_PATH} must contain a [categories] table")
    invalid = {
        repo: config
        for repo, config in categories.items()
        if not isinstance(config, dict)
        or type(config.get("id")) is not int
        or config["id"] <= 0
        or config.get("category") not in VALID_CATEGORIES
    }
    if invalid:
        raise ValueError(f"Invalid category assignments: {invalid}")
    repo_ids = [config["id"] for config in categories.values()]
    if len(repo_ids) != len(set(repo_ids)):
        raise ValueError(f"Repository IDs in {CATEGORIES_PATH} must be unique")
    return categories


def categorize_plugin(
    plugin: dict,
    categories: dict[str, dict],
    classifier: PluginClassifier | None = None,
) -> str:
    """Return a reviewed category or an ephemeral model suggestion."""
    repo = plugin["repo_full_name"]

    review = categories.get(repo)
    if review and review["id"] == plugin["repo_id"]:
        return review["category"]

    return classifier.classify(plugin) if classifier else "Other"


def generate_json(plugins: list[dict], reviewed_repos: dict[str, dict]) -> str:
    """Generate JSON, publishing documentation links only after review."""
    clean = []
    for p in sorted(plugins, key=lambda p: (-p["stars"], p["name"])):
        reviewed = is_reviewed(p["repo_full_name"], p.get("repo_id"), reviewed_repos)
        clean.append({
            "name": p["name"],
            "description": p["description"],
            "repo_url": p["repo_url"],
            "repo_full_name": p["repo_full_name"],
            "repo_id": p["repo_id"],
            "stars": p["stars"],
            "docs": p.get("docs") if reviewed else None,
            # recorded so a later run knows whether the docs value above is the
            # parsed URL or the redacted placeholder
            "reviewed": reviewed,
            "topics": p.get("topics", []),
            "entry_points": p.get("entry_points", {}),
            "pyproject_sha": p.get("pyproject_sha"),
            "category": p["category"],
        })
    data = {
        "categories": VALID_CATEGORIES,
        "plugins": clean,
    }
    return json.dumps(data, indent=2) + "\n"


def report_pending(count: int) -> None:
    """Tell CI how many plugins still need a category, if it is listening."""
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"pending={count}\n")


def classify_only(categories: dict[str, dict]) -> int:
    """Fill in categories for the unreviewed plugins of an existing snapshot."""
    data_path = DATA_DIR / "plugins.json"
    plugins = json.loads(data_path.read_text())["plugins"]
    pending = [
        p
        for p in plugins
        if not is_reviewed(p["repo_full_name"], p.get("repo_id"), categories)
    ]
    if pending:
        classifier = PluginClassifier()
        for plugin in pending:
            plugin["category"] = classifier.classify(plugin)
        data_path.write_text(generate_json(plugins, categories))
        print(f"Classified {len(pending)} plugin(s)", file=sys.stderr)
    else:
        print("Nothing to classify", file=sys.stderr)
    return len(pending)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-classify",
        action="store_true",
        help="skip model suggestions; leave unreviewed plugins as Other",
    )
    parser.add_argument(
        "--classify-only",
        action="store_true",
        help="only classify unreviewed plugins in the existing snapshot",
    )
    args = parser.parse_args(argv)

    if args.classify_only:
        classify_only(load_categories())
        return

    token = os.environ.get("GITHUB_TOKEN")
    auth = github.Auth.Token(token) if token else None
    # per_page=100 keeps code search to one page per query; retry=0 hands
    # backoff to _api_call so the header values are respected
    gh = github.Github(auth=auth, per_page=SEARCH_PAGE_SIZE, retry=0)

    categories = load_categories()
    print(f"Loaded {len(categories)} category mappings", file=sys.stderr)
    previous = load_previous_plugins()
    print(f"Loaded {len(previous)} previous entries", file=sys.stderr)

    phase = time.monotonic()
    plugins = list(discover_plugins(search_github(gh), categories, previous))
    print(f"Discovery: {time.monotonic() - phase:.1f}s", file=sys.stderr)

    phase = time.monotonic()
    plugins = revalidate_missing_plugins(gh, plugins, set(categories), categories)
    print(f"Revalidation: {time.monotonic() - phase:.1f}s", file=sys.stderr)

    plugins = deduplicate_plugins(plugins, categories)

    unreviewed = [
        plugin
        for plugin in plugins
        if not is_reviewed(
            plugin["repo_full_name"], plugin.get("repo_id"), categories
        )
    ]
    needs_model = unreviewed
    classifier = None
    if needs_model and not args.no_classify:
        phase = time.monotonic()
        try:
            classifier = PluginClassifier()
        except ImportError as exc:
            raise SystemExit(
                "llama-cpp-python is not installed: use the classify "
                "environment, or pass --no-classify"
            ) from exc
        print(
            f"Classifier ready for {len(needs_model)} plugin(s): "
            f"{time.monotonic() - phase:.1f}s",
            file=sys.stderr,
        )
    elif needs_model:
        print(
            f"--no-classify: {len(needs_model)} plugin(s) left as Other",
            file=sys.stderr,
        )

    for plugin in plugins:
        plugin["category"] = categorize_plugin(plugin, categories, classifier)

    # A token or permission outage would otherwise publish a silently shrunken
    # index, commit it, and deploy it
    if not plugins:
        raise RuntimeError(
            "Refusing to publish an empty plugin index; check the token and "
            "GitHub availability"
        )
    if previous and len(plugins) < len(previous) * (1 - MAX_SHRINK):
        raise RuntimeError(
            f"Refusing to publish {len(plugins)} plugins, down from "
            f"{len(previous)}; check the token and GitHub availability"
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json_path = DATA_DIR / "plugins.json"
    json_path.write_text(generate_json(plugins, categories))
    print(f"Wrote {json_path}", file=sys.stderr)

    pending = len(unreviewed)
    report_pending(pending)
    if pending and args.no_classify:
        print(
            f"! {pending} plugin(s) still need a category; run the classify pass",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()

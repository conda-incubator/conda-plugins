import os
import sys
import time
import tomllib

import github
from github import GithubException


RETRY_WAIT = 60
MAX_RETRIES = 5


def search_github():
    gh = github.Github(os.environ.get("GITHUB_TOKEN"), per_page=30)
    results = gh.search_code('"[project.entry-points.conda]" language:TOML')
    if results.totalCount:
        return results
    raise RuntimeError("Did not find any results")


def _fetch_with_retry(fn, label=""):
    """Call *fn* with retries on rate limit (HTTP 429) and abuse errors."""
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


def results(search_results):
    seen_repos = set()
    for result in search_results:
        if result.name != "pyproject.toml":
            continue

        repo_full_name = result.repository.full_name
        if repo_full_name in seen_repos:
            continue
        seen_repos.add(repo_full_name)

        if result.repository.fork:
            continue

        try:
            content = _fetch_with_retry(
                lambda r=result: r.decoded_content.decode(),
                label=repo_full_name,
            )
            toml = tomllib.loads(content)
        except tomllib.TOMLDecodeError:
            print(f"! Couldn't decode {repo_full_name}", file=sys.stderr)
            continue
        except RuntimeError as exc:
            print(f"! Skipping {repo_full_name}: {exc}", file=sys.stderr)
            continue

        plugin = {
            "name": result.repository.name,
            "stars": result.repository.stargazers_count,
            "description": result.repository.description,
            "repo_url": result.repository.html_url,
        }
        if docs := toml.get("project", {}).get("urls", {}).get("documentation"):
            plugin["docs"] = docs
        if name := toml.get("project", {}).get("name"):
            plugin["name"] = name
        if description := toml.get("project", {}).get("description"):
            plugin["description"] = description
        print("Processed", repo_full_name, file=sys.stderr)

        # Small delay between results to stay under secondary rate limits
        time.sleep(1)

        yield plugin


def plugin_list():
    lines = [
        "| Name | Description | ⭐ |",
        "|------|-------------|--:|",
    ]
    for r in sorted(results(search_github()), key=lambda r: (-r["stars"], r["name"])):
        lines.append(f"| [{r["name"]}]({r["repo_url"]}) | {r["description"]} | {r["stars"]} |")
    lines.append("")
    return "\n".join(lines)


def rerender(path):
    lines = []
    with open(path) as f:
        keep_line = True
        for line in f:
            if line.strip() == "<!-- PLUGIN_LIST -->":
                keep_line = not keep_line
                lines.append(line)
                if not keep_line:
                    lines.append("RERENDER_PLACEHOLDER\n")
                continue
            if keep_line:
                lines.append(line)
                
    return "".join(lines).replace("RERENDER_PLACEHOLDER", plugin_list())


if __name__ == "__main__":
    new_content = rerender(sys.argv[1])
    with open(sys.argv[1], "w") as f:
        f.write(new_content)

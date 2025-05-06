import os
import sys
import tomllib

import github


def search_github():
    gh = github.Github(os.environ.get("GITHUB_TOKEN"))
    results = gh.search_code('"[project.entry-points.conda]" language:TOML')
    if results.totalCount:
        return results
    raise RuntimeError("Did not find any results")


def results(search_results):
    for result in search_results:
        if result.name != "pyproject.toml":
            continue
        if result.repository.fork:
            continue
        try:
            toml = tomllib.loads(result.decoded_content.decode())
        except tomllib.TOMLDecodeError:
            print(f"! Couldn't decode {result.repository.full_name}", file=sys.stderr)
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
        print("Processed", result.repository.full_name, file=sys.stderr)
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

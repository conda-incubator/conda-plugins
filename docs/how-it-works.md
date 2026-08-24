# How this index works

This site is generated automatically from a pipeline that discovers,
categorizes, and publishes conda plugins found on GitHub.

## Discovery

A weekly GitHub Actions workflow runs
[`scripts/plugin_list.py`](https://github.com/conda-incubator/conda-plugins/blob/main/scripts/plugin_list.py),
which searches GitHub for repositories whose root `pyproject.toml`
contains `[project.entry-points.conda]` or
`[project.entry-points."conda"]`. For each discovered repository it
collects:

- The plugin name and description from `pyproject.toml`
- GitHub stars, topics, and documentation URL
- The conda entry points declared by the plugin

Forks, private repositories, and nested example projects are filtered out
automatically. When repositories declare the same normalized project name, a
reviewed repository takes precedence before star count. Review status requires
both the current `owner/repo` name and the immutable numeric GitHub repository
ID to match. Previously indexed and reviewed repositories missing from a search
response are checked directly before removal.

## Categorization

Each plugin is assigned to one of eight categories using a committed
[`scripts/categories.toml`](https://github.com/conda-incubator/conda-plugins/blob/main/scripts/categories.toml)
file that maps known repositories and their immutable GitHub IDs to reviewed
categories. This mapping is authoritative.

For an unmapped plugin, the renderer asks the Apache-2.0
[Qwen3.5 2B](https://huggingface.co/Qwen/Qwen3.5-2B) model for a category.
It runs locally through `llama-cpp-python` using a pinned Q4_K_M GGUF,
deterministic decoding, and a grammar that permits only the eight category
names. The model sees the project name, description, entry points, and
GitHub topics. It does not receive repository README content.

The result is a suggestion for the generated index only. The renderer never
writes it to `categories.toml`. A reviewed mapping therefore overrides the
model on every later run. If the model chooses **Other**, the plugin remains
there until a human adds a more specific mapping.

An unmapped plugin links only to its GitHub repository. Its project-supplied
documentation URL is published after a reviewer records the repository name,
immutable ID, and category in `scripts/categories.toml`.

The categories are:

- Solvers -- alternative dependency solvers
- Subcommands -- new CLI commands
- Channels -- channel and repodata manipulation
- Authentication -- auth providers and credential storage
- Environment management -- environment creation, modification,
  protection, lockfiles, and activation
- Build tools -- package building and indexing
- UI and display -- TUI, rich output, and display enhancements
- Other -- plugins that don't fit the above

Anyone can open a pull request to correct or stabilize a category in
`scripts/categories.toml`.

## Data generation

The script produces two outputs:

`README.md`
: The plugin table between `<!-- PLUGIN_LIST -->` markers is
  rewritten with the latest data, keeping the repository browsable
  on GitHub without visiting this site.

`docs/_data/plugins.json`
: A JSON file with metadata for every plugin, including its name,
  description, stars, category, entry points, topics, and a documentation
  URL for reviewed repositories. Repository READMEs are not copied into the
  site. This is the data source for the Sphinx build.

The script reads reviewed assignments from `scripts/categories.toml`
but never modifies them. The read-only render job passes only these two files
to a separate commit job, which writes any changes to the repository.

## Site generation

A separate GitHub Actions workflow builds this Sphinx site from the
JSON data using a custom extension
([`docs/_ext/plugin_pages.py`](https://github.com/conda-incubator/conda-plugins/blob/main/docs/_ext/plugin_pages.py))
that generates a page for each plugin and each category at build time.
The result is deployed to GitHub Pages.

## Running locally

The entire pipeline can be run on a developer's machine:

```bash
pixi run -e render render    # discover + categorize + generate data
pixi run -e docs docs        # build the Sphinx site
pixi run -e docs docs-serve  # serve at http://localhost:8000
```

## Source code

The full source for this index lives at
[conda-incubator/conda-plugins](https://github.com/conda-incubator/conda-plugins).

# How this index works

This site is generated automatically from a pipeline that discovers,
categorizes, and publishes conda plugins found on GitHub.

## Discovery

A weekly GitHub Actions workflow runs
[`scripts/plugin_list.py`](https://github.com/conda/conda-plugins/blob/main/scripts/plugin_list.py),
which searches GitHub for repositories whose `pyproject.toml` contains
`[project.entry-points.conda]`. For each discovered repository it
collects:

- The plugin name and description from `pyproject.toml`
- GitHub stars, topics, and documentation URL
- The conda entry points declared by the plugin
- The repository README (used for categorization and display)

Forks and duplicate repositories are filtered out automatically.

## Categorization

Each plugin is assigned to one of eight categories using a three-tier
approach designed to be sustainable and transparent:

Tier 1 -- Explicit mapping
: A committed
  [`scripts/categories.toml`](https://github.com/conda/conda-plugins/blob/main/scripts/categories.toml)
  file maps each known repository to its category. This is the source
  of truth and is checked first. Once a plugin is mapped here, it
  stays in that category until a human changes it.

Tier 2 -- Keyword heuristic
: For plugins not yet in `categories.toml`, the script applies
  keyword matching against the plugin's name, description, entry-point
  names, and README content. For example, "solver" in the name maps to
  Solvers, "auth" maps to Authentication, "subcommand" in the README
  maps to Subcommands, and so on.

Tier 3 -- Local LLM
: When the keyword heuristic cannot confidently classify a plugin
  (it would fall into "Other"), the script calls the
  [llm](https://llm.datasette.io/) CLI tool to classify it. This
  runs a small open-source model
  ([SmolLM2-360M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct),
  Apache 2.0, ~300 MB) locally on the GitHub Actions runner via
  [llm-gguf](https://github.com/simonw/llm-gguf). No data leaves
  the machine, no API keys are needed, and the model is cached
  between runs. The result is written back to `categories.toml` so
  the LLM is only consulted once per plugin.

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

If the automatic classification is wrong, anyone can open a pull
request updating `scripts/categories.toml`.

## Data generation

The script produces three outputs:

`README.md`
: The plugin table between `<!-- PLUGIN_LIST -->` markers is
  rewritten with the latest data, keeping the repository browsable
  on GitHub without visiting this site.

`docs/_data/plugins.json`
: A JSON file with rich metadata for every plugin (name, description,
  stars, category, entry points, topics, documentation URL). This is
  the data source for the Sphinx site.

`scripts/categories.toml`
: Updated with any new classifications from tiers 2 and 3.

All three files are committed automatically by the weekly workflow.

## Site generation

A separate GitHub Actions workflow builds this Sphinx site from the
JSON data using a custom extension
([`docs/_ext/plugin_pages.py`](https://github.com/conda/conda-plugins/blob/main/docs/_ext/plugin_pages.py))
that generates a page for each plugin and each category at build time.
The result is deployed to GitHub Pages.

## Running locally

The entire pipeline can be run on a developer's machine:

```bash
pixi run -e render render    # discover + categorize + generate data
pixi run -e docs docs        # build the Sphinx site
pixi run -e docs docs-serve  # serve at http://localhost:8000
```

The `--model` flag lets you override the LLM model, and `--skip-llm`
disables LLM classification entirely (useful for quick iterations).

## Source code

The full source for this index lives at
[conda/conda-plugins](https://github.com/conda/conda-plugins).

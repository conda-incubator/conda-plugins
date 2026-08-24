# Getting your plugin listed

Any conda plugin published on GitHub is automatically discovered and
added to this index. There is nothing special you need to do beyond
publishing your plugin.

## Requirements

Your repository must:

1. Contain a `pyproject.toml` at the repository root.
2. Declare at least one entry point under `[project.entry-points.conda]`
   or `[project.entry-points."conda"]`.
3. Not be a fork of another repository (forks are filtered out).
4. Be publicly visible on GitHub (private repositories are filtered out).

## Example pyproject.toml

```toml
[project]
name = "conda-my-plugin"
description = "A short description of what my plugin does"

[project.entry-points.conda]
my-plugin = "conda_my_plugin.plugin"

[project.urls]
documentation = "https://my-plugin.readthedocs.io"
```

The `project.name` and `project.description` fields are used for the
plugin listing. If `project.urls.documentation` is set, the link appears
after the repository receives a reviewed category mapping tied to its immutable
numeric GitHub repository ID.

## Categorization

Known plugins are categorized using reviewed mappings. A pinned local
Qwen3.5 2B model suggests a category for each unmapped plugin without
modifying the reviewed mappings. To correct or stabilize its category,
open a pull request updating
[`scripts/categories.toml`](https://github.com/conda-incubator/conda-plugins/blob/main/scripts/categories.toml)
in the conda-plugins repository. Record the repository's current `owner/repo`
name, numeric GitHub ID, and category in the existing inline-table format.

## Building a plugin from scratch

See the official [conda plugin tutorial](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/index.html)
and the [conda-plugin-template](https://github.com/conda/conda-plugin-template)
repository for a starter project.

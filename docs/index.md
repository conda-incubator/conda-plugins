# conda-plugins

A browsable index of [conda plugins](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/index.html)
discovered across GitHub. Updated weekly.

Plugins extend conda with new solvers, subcommands, authentication
backends, environment management features, and more. Anyone can
publish a conda plugin by adding
`[project.entry-points.conda]` to their `pyproject.toml`.

## Browse by category

::::::::{grid} 2 2 3 4
:gutter: 3

:::::::{grid-item-card} {octicon}`cpu` Solvers
:link: solvers/
Alternative dependency solvers for conda.
:::::::

:::::::{grid-item-card} {octicon}`terminal` Subcommands
:link: subcommands/
New CLI commands for conda.
:::::::

:::::::{grid-item-card} {octicon}`server` Channels
:link: channels/
Channel and repodata manipulation.
:::::::

:::::::{grid-item-card} {octicon}`shield-lock` Authentication
:link: authentication/
Authentication providers and identity.
:::::::

:::::::{grid-item-card} {octicon}`package` Environment management
:link: environment-management/
Environment creation, modification, and protection.
:::::::

:::::::{grid-item-card} {octicon}`tools` Build tools
:link: build-tools/
Package building and indexing.
:::::::

:::::::{grid-item-card} {octicon}`paintbrush` UI and display
:link: ui-and-display/
TUI, rich output, and display enhancements.
:::::::

:::::::{grid-item-card} {octicon}`ellipsis` Other
:link: other/
Other plugins.
:::::::

::::::::

## All plugins

```{plugin-list}
```

## Get started

- [About conda plugins](about) -- plugin hooks and what they can do
- [How this index works](how-it-works) -- discovery, categorization, and site generation
- [Create your own](contributing) -- how to build and publish a plugin
- [conda plugin docs](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/index.html) -- official developer guide
- [conda-plugin-template](https://github.com/conda/conda-plugin-template) -- starter template repository

```{toctree}
:hidden:
:caption: Plugins
:glob:

*/index
```

```{toctree}
:hidden:
:caption: About

about
how-it-works
contributing
```

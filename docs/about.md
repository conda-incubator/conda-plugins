# About conda plugins

conda's [plugin system](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/index.html)
lets anyone extend conda with new functionality. Plugins are regular
Python packages that declare entry points under
`[project.entry-points.conda]` in their `pyproject.toml`.

## What plugins can do

Plugins can hook into many parts of conda's lifecycle via
[plugin hooks](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/index.html#using-other-plugin-hooks).
Each hook has its own documentation page in the conda developer guide:

[Auth handlers](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/auth_handlers.html)
: Handle channel authentication and credential storage.

[Environment exporters](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/environment_exporters.html)
: Export environments in custom formats.

[Environment specifiers](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/environment_specifiers.html)
: Provide alternative environment specification formats.

[Health checks](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/health_checks.html)
: Run diagnostic checks on environments.

[Package extractors](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/package_extractors.html)
: Extract packages from custom archive formats.

[Pre-commands](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/pre_commands.html) / [Post-commands](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/post_commands.html)
: Run code before or after built-in conda commands.

[Pre-transactions](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/pre_transaction_actions.html) / [Post-transactions](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/post_transaction_actions.html)
: Hook into environment transactions (installs, updates, removes).

[PrefixData loaders](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/prefix_data_loaders.html)
: Customize how installed package metadata is read.

[Reporter backends](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/reporter_backends.html)
: Provide custom output formats for conda commands.

[Request headers](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/request_headers.html)
: Inject HTTP headers into channel requests.

[Settings](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/settings.html)
: Register custom configuration options.

[Solvers](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/solvers.html)
: Provide alternative dependency resolution backends.

[Subcommands](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/subcommands.html)
: Add new `conda <name>` CLI commands.

[Virtual packages](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/virtual_packages.html)
: Provide virtual package information to the solver.

For the full API reference, see the
[Plugin API docs](https://docs.conda.io/projects/conda/en/latest/dev-guide/api/conda/plugins/index.html).

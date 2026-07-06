# 🔌 Conda Plugins 🔌

A collection of [conda plugins](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/index.html).

To learn about how to implement your own custom plugins, check out our [tutorial template repo](https://github.com/conda/conda-plugin-template).

## Plugins List

<!-- PLUGIN_LIST -->
| Name | Description | ⭐ |
|------|-------------|--:|
| [conda-libmamba-solver](https://github.com/conda/conda-libmamba-solver) | The fast mamba solver, now in conda | 246 |
| [conda-smithy](https://github.com/conda-forge/conda-smithy) | A package to create repositories for conda recipes, and automate their building with CI tools on Linux, OSX and Windows. | 179 |
| [conda-tree](https://github.com/conda-incubator/conda-tree) | conda dependency tree helper | 174 |
| [menuinst](https://github.com/conda/menuinst) | cross platform install of menu items | 49 |
| [conda-pypi](https://github.com/conda/conda-pypi) | Better PyPI interoperability for the conda ecosystem. | 36 |
| [conda_index](https://github.com/conda/conda-index) | conda index, formerly part of conda-build. Create channels from collections of packages. | 11 |
| [anaconda-auth](https://github.com/anaconda/anaconda-auth) | A client auth library for Anaconda APIs | 8 |
| [conda-lockfiles](https://github.com/conda/conda-lockfiles) | Support different lockfiles in conda. | 7 |
| [conda-spawn](https://github.com/conda/conda-spawn) | Activate conda environments in new shell processes. | 6 |
| [anaconda-assistant-mcp](https://github.com/anaconda/assistant-sdk) | The Anaconda Assistant MCP plugin | 4 |
| [conda-anaconda-telemetry](https://github.com/anaconda/conda-anaconda-telemetry) | A conda plugin for Anaconda Telemetry | 3 |
| [conda-global](https://github.com/conda-incubator/conda-global) | Global tool installation for conda — install CLI tools into isolated environments and make them available on PATH via trampolines | 3 |
| [conda-tui](https://github.com/conda-incubator/conda-tui) | A Text User Interface for conda | 3 |
| [random-walk](https://github.com/beeankha/SimplePythonStuff) | My random walk subcommand plugin | 3 |
| [conda-completion](https://github.com/conda-incubator/conda-completion) | Fast shell tab completion for conda and all its plugins | 1 |
| [conda-history-d](https://github.com/jjhelmus/conda-history-d) | conda plugin which records a detailed history of environments in a history.d directory. | 1 |
| [conda-npm](https://github.com/aterrel/conda-npm) | conda-npm | 1 |
| [conda-ops](https://github.com/acwooding/conda-ops) | Conda plugin to maintain environments and projects reproducibly. | 1 |
| [conda-pypi-channel](https://github.com/jaimergp/conda-pypi-channel) | Expose a PyPI index as a conda channel, on the fly. | 1 |
| [conda-repodata](https://github.com/kenodegard/conda-repodata) | Conda plugin to locally manipulate or inspect the repodata.json. | 1 |
| [anaconda-auth](https://github.com/testifysec/anaconda-auth) | A client auth library for Anaconda APIs | 0 |
| [conda-broker](https://github.com/jezdez/conda-broker) | User-visible service supervision for long-running conda-adjacent processes | 0 |
| [conda-declarative](https://github.com/jaimergp/conda-declarative) | Declarative workflows for conda environment handling. | 0 |
| [conda-dev-request-headers](https://github.com/jezdez/conda-dev-request-headers) | Development-only conda plugin for injecting scoped HTTP request headers | 0 |
| [conda-env-spec-v2](https://github.com/peytondmurray/conda-env-spec-v2) | A V2 environment spec for conda. | 0 |
| [conda-graph-rebuilt](https://github.com/sophieblock/conda-lab) | Rebuilt conda graph plugin demonstrating plugin architecture | 0 |
| [conda-random-solver](https://github.com/costrouc/conda-random-solver) | A random conda solver | 0 |
| [conda-random-subcommand](https://github.com/costrouc/conda-random-subcomand) | A random conda subcommand | 0 |
| [conda-wasm](https://github.com/jezdez/conda-wasm) | Browser runtime and conda plugins for WebAssembly conda environments | 0 |

<!-- PLUGIN_LIST -->

[libmamba-shield]: https://img.shields.io/github/release/conda/conda-libmamba-solver.svg
[libmamba-releases]: https://github.com/conda/conda-libmamba-solver/releases
[libmamba-contributors]: https://github.com/conda/conda-libmamba-solver/graphs/contributors
[mamba project]: https://mamba.readthedocs.io/en/latest/

[auth-shield]: https://img.shields.io/github/v/release/conda-incubator/conda-auth.svg
[auth-releases]: https://github.com/conda-incubator/conda-auth/releases
[auth-contributors]: https://github.com/conda-incubator/conda-auth/graphs/contributors

[lock-shield]: https://img.shields.io/github/v/release/conda/conda-lock.svg
[lock-releases]: https://github.com/conda/conda-lock/releases
[lock-contributors]: https://github.com/conda/conda-lock/graphs/contributors

[protect-shield]: https://img.shields.io/github/v/release/conda-incubator/conda-protect.svg
[protect-releases]: https://github.com/conda-incubator/conda-protect/releases
[protect-contributors]: https://github.com/conda-incubator/conda-protect/graphs/contributors
[pre/post-command blog post]: https://conda.org/blog/2023-07-31-latest-conda-release-includes-new-plugin-hooks#conda-protect-and-the-pre-command-hook

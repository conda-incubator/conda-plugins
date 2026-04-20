# 🔌 Conda Plugins 🔌

A collection of [conda plugins](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/index.html).

To learn about how to implement your own custom plugins, check out our [tutorial template repo](https://github.com/conda/conda-plugin-template).

## Plugins List

<!-- PLUGIN_LIST -->
| Name | Description | ⭐ |
|------|-------------|--:|
| [conda_lock](https://github.com/conda/conda-lock) | Lockfiles for conda | 555 |
| [conda-build](https://github.com/conda/conda-build) | tools for building conda packages | 395 |
| [conda-libmamba-solver](https://github.com/conda/conda-libmamba-solver) | The fast mamba solver, now in conda | 244 |
| [conda-smithy](https://github.com/conda-forge/conda-smithy) | A package to create repositories for conda recipes, and automate their building with CI tools on Linux, OSX and Windows. | 176 |
| [menuinst](https://github.com/conda/menuinst) | cross platform install of menu items | 48 |
| [conda-pypi](https://github.com/conda/conda-pypi) | Better PyPI interoperability for the conda ecosystem. | 26 |
| [conda-protect](https://github.com/conda-incubator/conda-protect) | Protects conda environments to avoid mistakenly modifying them | 16 |
| [ascii-graph](https://github.com/conda/conda-plugin-template) | My ascii graph subcommand plugin | 11 |
| [conda-rattler-solver](https://github.com/conda-incubator/conda-rattler-solver) | The fast pixi solver, now in conda | 11 |
| [conda_index](https://github.com/conda/conda-index) | conda index, formerly part of conda-build. Create channels from collections of packages. | 11 |
| [anaconda-auth](https://github.com/anaconda/anaconda-auth) | A client auth library for Anaconda APIs | 8 |
| [conda-spawn](https://github.com/conda-incubator/conda-spawn) | Activate conda environments in new shell processes. | 7 |
| [conda-which](https://github.com/kelvinou01/conda-which) | What package does this file belong to? | 7 |
| [conda-auth](https://github.com/conda-incubator/conda-auth) | A conda plugin for handling multiple authentication schemes | 5 |
| [anaconda-assistant-mcp](https://github.com/anaconda/assistant-sdk) | The Anaconda Assistant MCP plugin | 4 |
| [conda-anaconda-tos](https://github.com/anaconda/conda-anaconda-tos) | Conda subcommand to view, accept, and interact with a channel's Terms of Service (ToS). | 4 |
| [conda-emscripten](https://github.com/jezdez/conda-express) | Emscripten-specific conda plugins: solver (resolvo via cx-wasm), package extractor, and virtual packages | 4 |
| [conda-lockfiles](https://github.com/conda-incubator/conda-lockfiles) | Support different lockfiles in conda. | 4 |
| [conda-self](https://github.com/conda-incubator/conda-self) | A self command for conda | 4 |
| [conda-subchannel](https://github.com/conda-incubator/conda-subchannel) | Create subsets of conda channels thanks to CEP-15 metadata. | 4 |
| [nvidia-virtual-packages](https://github.com/conda-incubator/nvidia-virtual-packages) | Provides conda virtual packages for NVIDIA hardware. | 4 |
| [conda-anaconda-telemetry](https://github.com/anaconda/conda-anaconda-telemetry) | A conda plugin for Anaconda Telemetry | 3 |
| [conda-tui](https://github.com/conda-incubator/conda-tui) | A Text User Interface for conda | 3 |
| [string-art](https://github.com/beeankha/SimplePythonStuff) | My string art subcommand plugin | 3 |
| [conda-libmamba-solver](https://github.com/Gujilde163904STI/lifi-project) | The fast mamba solver, now in conda | 2 |
| [captain-planet](https://github.com/kalawac/simple-bash-plugin) | Plugin for POSIX shells that calls the conda processes used for activate, deactivate, reactivate, hook, and command | 1 |
| [conda-checkpoints](https://github.com/conda-incubator/conda-checkpoints) | conda plugin to save lockfiles to your environment after each environment modification | 1 |
| [conda-classic-solver](https://github.com/conda/conda-classic-solver) | The `classic` solver used in `conda` | 1 |
| [conda-history-d](https://github.com/jjhelmus/conda-history-d) | conda plugin which records a detailed history of environments in a history.d directory. | 1 |
| [conda-npm](https://github.com/aterrel/conda-npm) | conda-npm | 1 |
| [conda-ops](https://github.com/acwooding/conda-ops) | Conda plugin to maintain environments and projects reproducibly. | 1 |
| [conda-presto](https://github.com/jezdez/conda-presto) | Resolve conda environment.yml files to fully pinned package lists with SHA256 hashes | 1 |
| [conda-pypi-channel](https://github.com/jaimergp/conda-pypi-channel) | Expose a PyPI index as a conda channel, on the fly. | 1 |
| [conda-repodata](https://github.com/kenodegard/conda-repodata) | Conda plugin to locally manipulate or inspect the repodata.json. | 1 |
| [conda-workspaces](https://github.com/conda-incubator/conda-workspaces) | Project-scoped multi-environment workspace management for conda, with pixi compatibility | 1 |
| [condact](https://github.com/conda-incubator/conda-shell) | Conda shell hook and subcommand for shell plugins | 1 |
| [anaconda-auth](https://github.com/testifysec/anaconda-auth) | A client auth library for Anaconda APIs | 0 |
| [anaconda-auth](https://github.com/ahm4d-312/Code_space) | A client auth library for Anaconda APIs | 0 |
| [conda-declarative](https://github.com/jaimergp/conda-declarative) | Declarative workflows for conda environment handling. | 0 |
| [conda-disable-init](https://github.com/jennan/conda_disable_init) | Disable conda init command | 0 |
| [conda-env-spec-v2](https://github.com/peytondmurray/conda-env-spec-v2) | A V2 environment spec for conda. | 0 |
| [conda-forge-conda-plugins](https://github.com/regro/conda-forge-conda-plugins) | conda plugins for the conda-forge ecosystem | 0 |
| [conda-global](https://github.com/conda-incubator/conda-global) | Global tool installation for conda — install CLI tools into isolated environments and make them available on PATH via trampolines | 0 |
| [conda-graph-rebuilt](https://github.com/sophieblock/conda-lab) | Rebuilt conda graph plugin demonstrating plugin architecture | 0 |
| [conda-random-solver](https://github.com/costrouc/conda-random-solver) | A random conda solver | 0 |
| [conda-random-subcommand](https://github.com/costrouc/conda-random-subcomand) | A random conda subcommand | 0 |
| [conda-restricted](https://github.com/jezdez/conda-restricted) | A conda plugin to restrict the SEARCH_PATH for conda configuration files | 0 |
| [conda-rich](https://github.com/conda-incubator/conda-rich) | Conda plugin which uses rich components for its display | 0 |
| [conda-test-header-plugin](https://github.com/anaconda/docker-examples) | A plugin for injecting headers (just for testing) | 0 |
| [conda-toml-spec](https://github.com/peytondmurray/conda-toml-spec) | Toml environment specification for conda | 0 |

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

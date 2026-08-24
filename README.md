# 🔌 Conda Plugins 🔌

A collection of [conda plugins](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/index.html).

Browse the full plugin index at **https://conda-incubator.github.io/conda-plugins/**

To learn about how to implement your own custom plugins, check out
the [conda plugin docs](https://docs.conda.io/projects/conda/en/latest/dev-guide/plugins/index.html)
and the [tutorial template repo](https://github.com/conda/conda-plugin-template).

## Plugins List

<!-- PLUGIN_LIST -->
| Name | Description | ⭐ |
|------|-------------|--:|
| [conda_lock](https://github.com/conda/conda-lock) | Lockfiles for conda | 562 |
| [conda-build](https://github.com/conda/conda-build) | tools for building conda packages | 400 |
| [conda-libmamba-solver](https://github.com/conda/conda-libmamba-solver) | The fast mamba solver, now in conda | 247 |
| [conda-smithy](https://github.com/conda-forge/conda-smithy) | A package to create repositories for conda recipes, and automate their building with CI tools on Linux, OSX and Windows. | 179 |
| [conda-tree](https://github.com/conda-incubator/conda-tree) | conda dependency tree helper | 174 |
| [menuinst](https://github.com/conda/menuinst) | cross platform install of menu items | 49 |
| [conda-pypi](https://github.com/conda/conda-pypi) | Better PyPI interoperability for the conda ecosystem. | 41 |
| [conda-rattler-solver](https://github.com/conda/conda-rattler-solver) | The fast pixi solver, now in conda | 17 |
| [conda-protect](https://github.com/conda-incubator/conda-protect) | Protects conda environments to avoid mistakenly modifying them | 16 |
| [conda_index](https://github.com/conda/conda-index) | conda index, formerly part of conda-build. Create channels from collections of packages. | 11 |
| [anaconda-auth](https://github.com/anaconda/anaconda-auth) | A client auth library for Anaconda APIs | 9 |
| [conda-content-trust](https://github.com/conda/conda-content-trust) | Signing and verification tools, geared toward the conda ecosystem. | 9 |
| [conda-auth](https://github.com/conda-incubator/conda-auth) | A conda plugin for handling multiple authentication schemes | 7 |
| [conda-lockfiles](https://github.com/conda/conda-lockfiles) | Support different lockfiles in conda. | 7 |
| [conda-which](https://github.com/kelvinou01/conda-which) | What package does this file belong to\? | 7 |
| [conda-global](https://github.com/conda-incubator/conda-global) | Global tool installation for conda — install CLI tools into isolated environments and make them available on PATH via trampolines | 6 |
| [conda-spawn](https://github.com/conda/conda-spawn) | Activate conda environments in new shell processes. | 6 |
| [conda-workspaces](https://github.com/conda-incubator/conda-workspaces) | Project-scoped multi-environment workspace management for conda, with pixi compatibility | 6 |
| [conda-self](https://github.com/conda/conda-self) | A self command for conda | 5 |
| [conda-anaconda-tos](https://github.com/anaconda/conda-anaconda-tos) | Conda subcommand to view, accept, and interact with a channel's Terms of Service \(ToS\). | 4 |
| [conda-subchannel](https://github.com/conda-incubator/conda-subchannel) | Create subsets of conda channels thanks to CEP-15 metadata. | 4 |
| [nvidia-virtual-packages](https://github.com/conda-incubator/nvidia-virtual-packages) | Provides conda virtual packages for NVIDIA hardware. | 4 |
| [conda-anaconda-telemetry](https://github.com/anaconda/conda-anaconda-telemetry) | A conda plugin for Anaconda Telemetry | 3 |
| [conda-tui](https://github.com/conda-incubator/conda-tui) | A Text User Interface for conda | 3 |
| [conda-exec](https://github.com/conda-incubator/conda-exec) | Ephemeral package execution for conda -- run any conda package without installing it | 2 |
| [captain-planet](https://github.com/kalawac/simple-bash-plugin) | Plugin for POSIX shells that calls the conda processes used for activate, deactivate, reactivate, hook, and command | 1 |
| [conda-checkpoints](https://github.com/conda-incubator/conda-checkpoints) | conda plugin to save lockfiles to your environment after each environment modification | 1 |
| [conda-classic-solver](https://github.com/conda/conda-classic-solver) | The \`classic\` solver used in \`conda\` | 1 |
| [conda-completion](https://github.com/conda-incubator/conda-completion) | Fast shell tab completion for conda and all its plugins | 1 |
| [conda-controlplane](https://github.com/sophieblock/conda-controlplane) | Inspect conda base control-plane tooling \(solvers/auth/platform, compiler metas, packaging helpers\). | 1 |
| [conda-history-d](https://github.com/jjhelmus/conda-history-d) | conda plugin which records a detailed history of environments in a history.d directory. | 1 |
| [conda-npm](https://github.com/aterrel/conda-npm) | conda-npm | 1 |
| [conda-ops](https://github.com/acwooding/conda-ops) | Conda plugin to maintain environments and projects reproducibly. | 1 |
| [conda-presto](https://github.com/jezdez/conda-presto) | Resolve, inspect, and cache conda solve results through CLI, HTTP, CI, and solver integrations | 1 |
| [conda-pypi-channel](https://github.com/jaimergp/conda-pypi-channel) | Expose a PyPI index as a conda channel, on the fly. | 1 |
| [conda-repodata](https://github.com/kenodegard/conda-repodata) | Conda plugin to locally manipulate or inspect the repodata.json. | 1 |
| [conda-sboms](https://github.com/conda-incubator/conda-sboms) | Generate software bills of materials from conda environments | 1 |
| [conda-ship](https://github.com/jezdez/conda-ship) | Conda plugin entry point for the conda-ship runtime builder. | 1 |
| [condact](https://github.com/conda-incubator/conda-shell) | Conda shell hook and subcommand for shell plugins | 1 |
| [anaconda-channel-guide](https://github.com/anaconda/anaconda-channel-guide) | A plugin that intercepts PackageNotFoundErrors and checks if the package exists in other channels. | 0 |
| [conda-broker](https://github.com/jezdez/conda-broker) | User-visible service supervision for long-running conda-adjacent processes | 0 |
| [conda-declarative](https://github.com/jaimergp/conda-declarative) | Declarative workflows for conda environment handling. | 0 |
| [conda-declarative-input-states](https://github.com/peytondmurray/conda-declarative-input-states) | Declarative input states for conda | 0 |
| [conda-dev-request-headers](https://github.com/jezdez/conda-dev-request-headers) | Development-only conda plugin for injecting scoped HTTP request headers | 0 |
| [conda-disable-init](https://github.com/jennan/conda_disable_init) | Disable conda init command | 0 |
| [conda-env-spec-v2](https://github.com/peytondmurray/conda-env-spec-v2) | A V2 environment spec for conda. | 0 |
| [conda-forge-conda-plugins](https://github.com/regro/conda-forge-conda-plugins) | conda plugins for the conda-forge ecosystem | 0 |
| [conda-random-solver](https://github.com/costrouc/conda-random-solver) | A random conda solver | 0 |
| [conda-random-subcommand](https://github.com/costrouc/conda-random-subcomand) | A random conda subcommand | 0 |
| [conda-restricted](https://github.com/jezdez/conda-restricted) | A conda plugin to restrict the SEARCH\_PATH for conda configuration files | 0 |
| [conda-rich](https://github.com/conda-incubator/conda-rich) | Conda plugin which uses rich components for its display | 0 |
| [conda-serviceinst](https://github.com/Adam-D-Lewis/conda-serviceinst) | Thin conda plugin that auto-triggers serviceinst on package install/remove | 0 |
| [conda-sigstore](https://github.com/jezdez/conda-sigstore) | Create and verify Sigstore attestations for conda packages | 0 |
| [conda-toml-spec](https://github.com/peytondmurray/conda-toml-spec) | Toml environment specification for conda | 0 |
<!-- PLUGIN_LIST -->

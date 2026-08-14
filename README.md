# tendcf

Configuration management for a mixed, intermittently-connected fleet:
Apple Silicon Macs, Linux (x86_64 and aarch64), and Android devices
reached through [Termux](https://termux.dev/).

Most of the configuration will be written by AI coding agents. People
still decide what should happen. A person whose computer is managed
should be able to read a proposed change in ordinary language and refuse
it — using **their** AI, not ours.

**Start here:** [`docs/paper/tendcf-architecture-guide.md`](docs/paper/tendcf-architecture-guide.md)

That guide is the vetted current-state description. Where any other
living document disagrees on the current design, **the guide wins**.

| Path | What |
| --- | --- |
| [`docs/architecture/architecture-DEFINITIVE-v3.md`](docs/architecture/architecture-DEFINITIVE-v3.md) | Implementer map (decisions, build order, protection). Must agree with the guide. |
| [`docs/paper/tendcf-architecture-paper.md`](docs/paper/tendcf-architecture-paper.md) | Technical paper |
| [`schema/`](schema/), [`examples/`](examples/), [`bin/schema_lint.py`](bin/schema_lint.py) | Site Model contract, fixtures, lint |
| [`examples/broken/`](examples/broken/) | Twelve deliberately broken fixtures the lint must catch |
| [djbclark/nix2cf](https://github.com/djbclark/nix2cf) | Compiler (Site Model → CFEngine Augments). Not this repo. |

Nothing described here is deployed. Some data formats exist and are
checked. The compiler, the on-device executor, and the consent surface
are still to be built.

```bash
bin/schema_lint.py
bin/check_protected_docs.py
```

CI runs both on every push and pull request. Locally, D27 also runs as a
commit-msg hook once git uses this repo's hooks:

```bash
git config core.hooksPath .githooks
```

Edits to `docs/architecture/architecture-DEFINITIVE-v3.md` need an
`Approved-change: <reason>` trailer on the commit.

License: [GPL-3.0-or-later](LICENSE).

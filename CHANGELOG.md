# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/); this project uses semantic
versioning.

## [Unreleased]

### Added
- Framework-free eol.network API client (`netbox_eol.client.EolClient`) for the
  `/api/v1/integrations/*` API: bulk `match` / `kev/lookup`, keyed
  `search`, mandatory User-Agent, ≤100 chunking, `q<2` pre-filter, retry/backoff
  with real error-code mapping, and tier/`vendor_resolved` parsing into typed
  dataclasses. 14 hermetic unit tests.
- `EolNetworkConfig(PluginConfig)` package skeleton; `min_version = 4.2.0`.
- CI (lint + framework-free unit tests on Python 3.10–3.12 + NetBox 4.2 framework test).

### TODO before first release
- Add the `LICENSE` file (Apache-2.0 — declared in `pyproject.toml`).
- Steps 3–7 of the build sequence (models, sync job, UI, REST API, docs).

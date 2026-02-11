# Checkpoint - 2026-02-11

## Scope

- Applied minor but high-leverage efficiency and reliability improvements.
- Updated project documentation to reflect these changes.

## Code Changes

- `api/middleware.py`
  - Rate-limit checks now prune stale timestamps per client on every check.
  - Cache key generation now normalizes case, whitespace, and `all`-style regulation aliases.
- `src/generation/__init__.py`
  - Added optional/lazy import behavior so prompt utilities remain importable without full runtime dependencies.
- `src/storage/weaviate_client.py`
  - Added graceful import fallback when `weaviate-client` is not installed, with clear runtime errors only when connection/setup is attempted.
- `tests/test_middleware.py`
  - Added tests for cache key normalization and per-client stale timestamp pruning.

## Documentation Updates

- `README.md`
  - Added "Recent Impactful Changes (2026-02-11)".
  - Added "Context Checkpoints" link to this file.
- `docs/ARCHITECTURE.md`
  - Added "Recent Efficiency Updates (2026-02-11)" section.

## Validation

- Ran focused tests:
  - `python -m pytest tests/test_middleware.py -q`
  - `python -m pytest tests/test_citation.py tests/test_citation_verifier.py -q`

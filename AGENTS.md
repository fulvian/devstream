# Repository Guidelines

## Project Structure & Module Organization
- `src/devstream/` hosts production code following the src-layout; key packages include `core` for abstractions, `planning` for orchestration, and `memory` for persistence.
- Tests live in `tests/` and are grouped by scope: `unit/`, `integration/`, and `standalone/`; shared fixtures sit in `tests/fixtures/`.
- Reusable automation lives in `scripts/`, while configuration assets stay under `config/` and reference docs under `docs/`. Runtime artifacts belong in `data/` and `logs/` and should not be committed.

## Build, Test, and Development Commands
- Bootstrap dependencies with `make install`; use `make dev` to add test/performance extras and install pre-commit hooks.
- Start the CLI locally with `poetry run python -m devstream.cli.main serve --reload`.
- Core quality commands:
```
make format         # black + isort
make lint           # ruff, mypy, bandit
make test           # full pytest suite
make test-unit      # focused unit run
make test-coverage  # HTML + terminal coverage
```
- Use `make db-init` or `make db-reset` whenever schema changes affect the SQLite data files.

## Coding Style & Naming Conventions
- Python formatting is enforced by Black (88 cols) and isort; Ruff extends PEP 8 with bugbear, naming, and security rules. Stick to four-space indentation and avoid trailing whitespace.
- Keep functions fully typed—`mypy --strict` runs in CI—so declare explicit return types and rely on `structlog` for structured logging instead of `print`.
- Modules and packages use `snake_case`, classes use `PascalCase`, and constants stay uppercase with underscores.

## Testing Guidelines
- Add pytest modules named `test_<feature>.py` to mirror the package you touch.
- Apply existing markers (`@pytest.mark.integration`, `@pytest.mark.requires_ollama`, etc.) to isolate slow or external dependencies.
- Target ≥95% coverage for new code and ensure `make test-coverage` passes before opening a PR.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (`feat(memory): add hybrid scoring`) and keep branches scoped (`feature/`, `fix/`, `docs/`, `refactor/`).
- Pull requests should summarize the change, highlight affected modules, and list validation commands; attach logs or screenshots when user-facing behavior shifts.
- Run `make lint test` locally and update docs (`docs/`, `PROJECT_STRUCTURE.md`, or `README.md`) whenever behavior or structure changes.

## Configuration & Agent Notes
- Project automation relies on `.claude/agents/` and hook scripts; rerun `make setup` after touching agent or hook definitions.
- Sensitive settings belong in `.env` or `config/`; never commit credentials. Document new variables in `README.md` or the relevant guide.

# Contributing

## Development Setup

```bash
uv sync --extra dev
pnpm --dir frontend install
pnpm --dir frontend build
```

Run the backend and frontend development servers in separate terminals:

```bash
uv run python main.py serve
pnpm --dir frontend dev
```

## Quality Gates

```bash
uv run pytest
uv run ruff check src tests scripts main.py
uv run mypy
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend test:run
pnpm --dir frontend build
```

Keep Python source and test filenames in lower camel case. React component filenames use PascalCase. Do not commit runtime data, models, uploaded media, generated evidence or CodeGraph indexes.

## Pull Requests

- Describe the user-visible outcome and any migration steps.
- Include tests for behavior changes.
- Keep unrelated refactors out of the same change.
- Update Chinese and English documentation when interfaces or workflows change.

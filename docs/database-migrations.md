# Database Migrations

The default database is:

```text
storage/helmet_workbench.sqlite3
```

Override it with `HELMET_WORKBENCH_DATABASE_URL`.

Apply the latest schema:

```bash
uv run python main.py upgrade-db
```

Create a migration during development:

```bash
uv run alembic -c migrations/alembic.ini revision --autogenerate -m "describe change"
uv run alembic -c migrations/alembic.ini upgrade head
```

The database stores relative media paths. Back up the database and the entire `storage/` directory together.

"""Guard against schema drift between models.py and the Alembic migration.

The rest of the suite builds its schema with `Base.metadata.create_all`, which
never touches Alembic. That's fast and right for unit tests, but it leaves a
hole: `0001_initial.py` is hand-written, so a column added to `models.py` would
pass every other test and then fail on deploy, when `alembic upgrade head` is
what actually builds the production database.

This test runs the real migration into a throwaway SQLite file and diffs the
resulting schema against the ORM metadata.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from app.db import Base
from app import models  # noqa: F401  — import for the side effect of registering tables

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _alembic_schema(db_path: Path) -> dict[str, set[str]]:
    """Run `alembic upgrade head` into `db_path` and return {table: {columns}}."""
    env = {
        **os.environ,
        # env.py reads this through get_settings(), which is lru_cached — so it
        # has to be set for a fresh process, not mutated in-process.
        "DATABASE_URL": f"sqlite+aiosqlite:///{db_path.as_posix()}",
    }
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(
            f"alembic upgrade head failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        inspector = inspect(engine)
        return {
            table: {col["name"] for col in inspector.get_columns(table)}
            for table in inspector.get_table_names()
            if table != "alembic_version"
        }
    finally:
        engine.dispose()


def _model_schema() -> dict[str, set[str]]:
    return {
        table.name: {col.name for col in table.columns}
        for table in Base.metadata.sorted_tables
    }


def test_migration_creates_exactly_the_tables_the_models_declare(tmp_path: Path) -> None:
    migrated = _alembic_schema(tmp_path / "drift_check.db")
    declared = _model_schema()

    missing = set(declared) - set(migrated)
    extra = set(migrated) - set(declared)

    assert not missing, f"models.py declares tables the migration never creates: {sorted(missing)}"
    assert not extra, f"migration creates tables models.py does not declare: {sorted(extra)}"


def test_migration_columns_match_the_models_column_for_column(tmp_path: Path) -> None:
    migrated = _alembic_schema(tmp_path / "drift_check.db")
    declared = _model_schema()

    drift: dict[str, dict[str, list[str]]] = {}
    for table, declared_cols in declared.items():
        migrated_cols = migrated.get(table, set())
        missing = sorted(declared_cols - migrated_cols)
        extra = sorted(migrated_cols - declared_cols)
        if missing or extra:
            drift[table] = {"missing_from_migration": missing, "not_in_models": extra}

    assert not drift, f"schema drift between models.py and 0001_initial.py: {drift}"

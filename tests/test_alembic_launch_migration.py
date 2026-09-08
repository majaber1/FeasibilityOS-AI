"""Tests for Wave 5 Alembic migration (0022_launch_actuals_os).

Exercises Alembic DDL directly against an isolated database:
1. Verify single head 0022_launch_actuals_os and revision chain from 0021_validation_os.
2. Upgrade to 0021 (verifying pre-Wave-5 state).
3. Upgrade to 0022 / head (verifying Wave 5 tables, columns, nullable semantics, FKs, indexes).
4. Verify actuals nullable semantics (missing != zero).
5. Insert and read records through migrated schema.
6. Downgrade to 0021 (verifying safe removal of Wave 5 tables and retention of Waves 1-4).
7. Re-upgrade back to head.
"""
import os
from pathlib import Path
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
DATABASE_DIR = REPO_ROOT / "database"
MIGRATIONS_DIR = DATABASE_DIR / "migrations"


@pytest.fixture
def alembic_config(tmp_path):
    """Creates a clean disposable SQLite database and configured Alembic Config."""
    db_file = tmp_path / "test_launch_migration.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    ini_path = DATABASE_DIR / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", db_url)

    os.environ["DATABASE_URL"] = db_url
    os.environ["POSTGRES_URL"] = db_url

    return cfg, db_url, db_file


def test_alembic_single_head_and_revision_chain():
    """Verify Alembic migration tree has a single head and expected revision lineage for Wave 5."""
    cfg = Config(str(DATABASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))

    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1, f"Expected exactly 1 migration head, found: {heads}"
    assert heads[0] in ("0022_launch_actuals_os", "0023_growth_os", "0024_wave6_integrity"), f"Expected head to be 0022, 0023, or 0024, got {heads[0]}"

    rev_0022 = script.get_revision("0022_launch_actuals_os")
    assert rev_0022.down_revision == "0021_validation_os"

    rev_0021 = script.get_revision("0021_validation_os")
    assert rev_0021.down_revision == "0020_opportunity_fit_matching"


def test_alembic_migration_0021_to_0022_upgrade_and_downgrade(alembic_config):
    """Full lifecycle migration test exercising 0021 -> 0022 upgrade, schema verification, data roundtrip, downgrade, and re-upgrade."""
    cfg, db_url, _ = alembic_config

    engine = sa.create_engine(db_url)

    # --- STEP 1: Upgrade to 0021 (Wave 4) ---
    command.upgrade(cfg, "0021_validation_os")

    inspector_0021 = sa.inspect(engine)
    tables_0021 = set(inspector_0021.get_table_names())

    # Verify Wave 4 tables exist
    assert "validation_workspaces" in tables_0021
    assert "validation_hypotheses" in tables_0021
    assert "validation_decisions" in tables_0021

    # Verify Wave 5 tables DO NOT yet exist at 0021
    wave5_tables = {
        "launch_workspaces",
        "launch_milestones",
        "launch_tasks",
        "launch_baseline_snapshots",
        "launch_actual_periods",
        "launch_reforecasts",
    }
    for t in wave5_tables:
        assert t not in tables_0021, f"Table {t} should not exist before 0022 migration"

    # --- STEP 2: Upgrade to head (0022_launch_actuals_os) ---
    command.upgrade(cfg, "head")

    inspector_0022 = sa.inspect(engine)
    tables_0022 = set(inspector_0022.get_table_names())

    # Verify all Wave 5 tables now exist
    for t in wave5_tables:
        assert t in tables_0022, f"Table {t} must exist after 0022 migration"

    # --- STEP 3: Verify Column semantics on launch_actual_periods (nullable actuals) ---
    actual_columns = {c["name"]: c for c in inspector_0022.get_columns("launch_actual_periods")}
    assert actual_columns["actual_revenue"]["nullable"] is True, "actual_revenue must be nullable"
    assert actual_columns["actual_capex"]["nullable"] is True, "actual_capex must be nullable"
    assert actual_columns["actual_opex_salaries"]["nullable"] is True, "actual_opex_salaries must be nullable"
    assert actual_columns["total_actual_opex"]["nullable"] is True, "total_actual_opex must be nullable"
    assert actual_columns["net_cashflow"]["nullable"] is True, "net_cashflow must be nullable"
    assert "source_type" in actual_columns
    assert "source_reference" in actual_columns

    # Verify milestone columns
    milestone_columns = {c["name"]: c for c in inspector_0022.get_columns("launch_milestones")}
    assert milestone_columns["budget_allocated"]["nullable"] is True, "budget_allocated must be nullable"
    assert "is_suggested" in milestone_columns
    assert "owner_name" in milestone_columns

    # Verify task columns
    task_columns = {c["name"]: c for c in inspector_0022.get_columns("launch_tasks")}
    assert "title" in task_columns
    assert "owner_name" in task_columns
    assert "status" in task_columns
    assert "is_critical" in task_columns

    # --- STEP 4: Insert and read a minimal Wave 5 record through migrated schema ---
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO users (email, hashed_password, full_name, role_key, locale, is_active, created_at, updated_at) "
                "VALUES ('founder@example.com', 'hash123', 'Founder', 'user', 'ar', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        user_id = conn.execute(sa.text("SELECT id FROM users WHERE email='founder@example.com'")).scalar()

        conn.execute(
            sa.text(
                "INSERT INTO projects (name, industry, investment, stage, workflow_status, owner_id, created_at, updated_at) "
                f"VALUES ('Test Project', 'tech', 50000.0, 'IDEA', 'DRAFT', {user_id}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        proj_id = conn.execute(sa.text(f"SELECT id FROM projects WHERE owner_id={user_id}")).scalar()

        conn.execute(
            sa.text(
                "INSERT INTO feasibility_studies (project_id, title, study_type, status, current_step, payload, created_at, updated_at) "
                f"VALUES ({proj_id}, 'Study 1', 'COMPREHENSIVE', 'ACTIVE', 1, '{{}}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        study_id = conn.execute(sa.text(f"SELECT id FROM feasibility_studies WHERE project_id={proj_id}")).scalar()

        # Insert launch workspace
        conn.execute(
            sa.text(
                "INSERT INTO launch_workspaces (study_id, project_id, user_id, status, created_at, updated_at) "
                f"VALUES ({study_id}, {proj_id}, {user_id}, 'PLANNED', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        ws_id = conn.execute(sa.text(f"SELECT id FROM launch_workspaces WHERE study_id={study_id}")).scalar()
        assert ws_id is not None

        # Insert milestone with null budget
        conn.execute(
            sa.text(
                "INSERT INTO launch_milestones (workspace_id, category, title, status, budget_allocated, is_suggested, created_at, updated_at) "
                f"VALUES ({ws_id}, 'REGULATORY', 'CR & License', 'PENDING', NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        m_id = conn.execute(sa.text(f"SELECT id FROM launch_milestones WHERE workspace_id={ws_id}")).scalar()
        assert m_id is not None

        # Insert task
        conn.execute(
            sa.text(
                "INSERT INTO launch_tasks (workspace_id, milestone_id, title, status, is_critical, created_at, updated_at) "
                f"VALUES ({ws_id}, {m_id}, 'Visit municipality portal', 'PENDING', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        task_id = conn.execute(sa.text(f"SELECT id FROM launch_tasks WHERE workspace_id={ws_id}")).scalar()
        assert task_id is not None

        # Insert actual period with missing revenue (NULL) and explicit zero capex
        conn.execute(
            sa.text(
                "INSERT INTO launch_actual_periods (workspace_id, period_label, period_order, actual_revenue, actual_capex, source_type, created_at, updated_at) "
                f"VALUES ({ws_id}, 'M01', 1, NULL, 0.0, 'USER_ENTERED', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        row = conn.execute(
            sa.text(f"SELECT actual_revenue, actual_capex, source_type FROM launch_actual_periods WHERE workspace_id={ws_id}")
        ).mappings().first()
        assert row["actual_revenue"] is None, "Missing actual revenue must be NULL"
        assert row["actual_capex"] == 0.0, "Explicit 0.0 capex must be preserved"
        assert row["source_type"] == "USER_ENTERED"

    # --- STEP 5: Downgrade back to 0021 ---
    command.downgrade(cfg, "0021_validation_os")

    inspector_downgrade = sa.inspect(engine)
    tables_downgraded = set(inspector_downgrade.get_table_names())

    # Verify Wave 5 tables dropped
    for t in wave5_tables:
        assert t not in tables_downgraded, f"Table {t} should have been dropped during downgrade"

    # Verify Wave 1-4 tables remain intact
    assert "users" in tables_downgraded
    assert "projects" in tables_downgraded
    assert "feasibility_studies" in tables_downgraded
    assert "validation_workspaces" in tables_downgraded

    # --- STEP 6: Re-upgrade to head (idempotency check) ---
    command.upgrade(cfg, "head")
    inspector_reupgrade = sa.inspect(engine)
    tables_reupgraded = set(inspector_reupgrade.get_table_names())
    for t in wave5_tables:
        assert t in tables_reupgraded, f"Table {t} must be recreated upon re-upgrade"

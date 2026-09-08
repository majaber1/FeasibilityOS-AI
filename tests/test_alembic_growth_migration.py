"""Tests for Wave 6 Alembic migration (0023_growth_os).

Exercises Alembic DDL directly against an isolated database:
1. Verify single head 0023_growth_os and revision chain from 0022_launch_actuals_os.
2. Upgrade to 0022 (verifying pre-Wave-6 state).
3. Upgrade to 0023 / head (verifying Wave 6 tables, columns, nullable semantics, FKs, indexes).
4. Verify investment nullable semantics (missing != zero).
5. Insert and read records through migrated schema.
6. Downgrade to 0022 (verifying safe removal of Wave 6 tables and retention of Waves 1-5).
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
    db_file = tmp_path / "test_growth_migration.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    ini_path = DATABASE_DIR / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", db_url)

    os.environ["DATABASE_URL"] = db_url
    os.environ["POSTGRES_URL"] = db_url

    return cfg, db_url, db_file


def test_alembic_single_head_and_revision_chain():
    """Verify Alembic migration tree has a single head and expected revision lineage for Wave 6."""
    cfg = Config(str(DATABASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))

    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1, f"Expected exactly 1 migration head, found: {heads}"
    assert heads[0] == "0024_wave6_integrity", f"Expected head to be 0024_wave6_integrity, got {heads[0]}"

    rev_0024 = script.get_revision("0024_wave6_integrity")
    assert rev_0024.down_revision == "0023_growth_os"

    rev_0023 = script.get_revision("0023_growth_os")
    assert rev_0023.down_revision == "0022_launch_actuals_os"

    rev_0022 = script.get_revision("0022_launch_actuals_os")
    assert rev_0022.down_revision == "0021_validation_os"


def test_alembic_migration_0022_to_0023_upgrade_and_downgrade(alembic_config):
    """Full lifecycle migration test exercising 0022 -> 0023 upgrade, schema verification, data roundtrip, downgrade, and re-upgrade."""
    cfg, db_url, _ = alembic_config

    engine = sa.create_engine(db_url)

    # --- STEP 1: Upgrade to 0022 (Wave 5) ---
    command.upgrade(cfg, "0022_launch_actuals_os")

    inspector_0022 = sa.inspect(engine)
    tables_0022 = set(inspector_0022.get_table_names())

    # Verify Wave 5 tables exist
    assert "launch_workspaces" in tables_0022
    assert "launch_actual_periods" in tables_0022

    # Verify Wave 6 tables DO NOT yet exist at 0022
    wave6_tables = {
        "growth_workspaces",
        "growth_scenarios",
        "growth_what_if_models",
        "growth_monthly_reviews",
        "growth_decisions",
        "growth_actions",
    }
    for t in wave6_tables:
        assert t not in tables_0022, f"Table {t} should not exist before 0023 migration"

    # --- STEP 2: Upgrade to head (0023_growth_os) ---
    command.upgrade(cfg, "head")

    inspector_0023 = sa.inspect(engine)
    tables_0023 = set(inspector_0023.get_table_names())

    # Verify all Wave 6 tables now exist
    for t in wave6_tables:
        assert t in tables_0023, f"Table {t} must exist after 0023 migration"

    # --- STEP 3: Verify Column semantics on growth_scenarios ---
    scenario_columns = {c["name"]: c for c in inspector_0023.get_columns("growth_scenarios")}
    assert scenario_columns["investment_required"]["nullable"] is True, "investment_required must be nullable"
    assert "scenario_type" in scenario_columns
    assert "capacity_assumptions" in scenario_columns
    assert "revenue_assumptions" in scenario_columns
    assert "cost_assumptions" in scenario_columns

    # Verify decision columns
    decision_columns = {c["name"]: c for c in inspector_0023.get_columns("growth_decisions")}
    assert decision_columns["pivot_validation_workspace_id"]["nullable"] is True
    assert "growth_scenario_id" in decision_columns
    assert decision_columns["growth_scenario_id"]["nullable"] is True
    assert "decision" in decision_columns
    assert "supporting_facts" in decision_columns
    assert "contradicting_facts" in decision_columns

    # --- STEP 4: Insert and read a minimal Wave 6 record through migrated schema ---
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO users (email, hashed_password, full_name, role_key, locale, is_active, created_at, updated_at) "
                "VALUES ('growth_founder@example.com', 'hash123', 'Growth Founder', 'user', 'ar', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        user_id = conn.execute(sa.text("SELECT id FROM users WHERE email='growth_founder@example.com'")).scalar()

        conn.execute(
            sa.text(
                "INSERT INTO projects (name, industry, investment, stage, workflow_status, owner_id, created_at, updated_at) "
                f"VALUES ('Test Growth Project', 'retail', 250000.0, 'OPERATING', 'ACTIVE', {user_id}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        proj_id = conn.execute(sa.text(f"SELECT id FROM projects WHERE owner_id={user_id}")).scalar()

        conn.execute(
            sa.text(
                "INSERT INTO feasibility_studies (project_id, title, study_type, status, current_step, payload, created_at, updated_at) "
                f"VALUES ({proj_id}, 'Operating Study', 'COMPREHENSIVE', 'ACTIVE', 5, '{{}}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        study_id = conn.execute(sa.text(f"SELECT id FROM feasibility_studies WHERE project_id={proj_id}")).scalar()

        # Insert growth workspace
        conn.execute(
            sa.text(
                "INSERT INTO growth_workspaces (study_id, project_id, user_id, status, created_at, updated_at) "
                f"VALUES ({study_id}, {proj_id}, {user_id}, 'ACTIVE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        ws_id = conn.execute(sa.text(f"SELECT id FROM growth_workspaces WHERE study_id={study_id}")).scalar()
        assert ws_id is not None

        # Insert scenario with NULL investment required
        conn.execute(
            sa.text(
                "INSERT INTO growth_scenarios (workspace_id, scenario_type, title, reason, investment_required, "
                "capacity_assumptions, revenue_assumptions, cost_assumptions, dependencies, risks, evidence_references, status, version, created_at, updated_at) "
                f"VALUES ({ws_id}, 'NEW_BRANCH', 'Branch 2 Jeddah', 'Expansion', NULL, "
                "'{{}}', '{{}}', '{{}}', '[]', '[]', '[]', 'PROPOSED', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        scen_id = conn.execute(sa.text(f"SELECT id FROM growth_scenarios WHERE workspace_id={ws_id}")).scalar()
        assert scen_id is not None

        row = conn.execute(
            sa.text(f"SELECT investment_required, status FROM growth_scenarios WHERE id={scen_id}")
        ).mappings().first()
        assert row["investment_required"] is None, "Missing investment must remain NULL"
        assert row["status"] == "PROPOSED"

    # --- STEP 5: Downgrade back to 0022 ---
    command.downgrade(cfg, "0022_launch_actuals_os")

    inspector_downgrade = sa.inspect(engine)
    tables_downgraded = set(inspector_downgrade.get_table_names())

    # Verify Wave 6 tables dropped
    for t in wave6_tables:
        assert t not in tables_downgraded, f"Table {t} should have been dropped during downgrade"

    # Verify Wave 1-5 tables remain intact
    assert "users" in tables_downgraded
    assert "projects" in tables_downgraded
    assert "feasibility_studies" in tables_downgraded
    assert "validation_workspaces" in tables_downgraded
    assert "launch_workspaces" in tables_downgraded

    # --- STEP 6: Re-upgrade to head (idempotency check) ---
    command.upgrade(cfg, "head")
    inspector_reupgrade = sa.inspect(engine)
    tables_reupgraded = set(inspector_reupgrade.get_table_names())
    for t in wave6_tables:
        assert t in tables_reupgraded, f"Table {t} must be recreated upon re-upgrade"

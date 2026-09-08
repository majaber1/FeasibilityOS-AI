"""Tests for Wave 4 Alembic migration (0021_validation_os).

Exercises Alembic DDL directly against an isolated database:
1. Upgrade to 0020 (verifying pre-Wave-4 state).
2. Upgrade to 0021 / head (verifying Wave 4 schema, columns, defaults, FKs, indexes).
3. Verify Wave 5 tables are strictly excluded.
4. Verify evidence_direction safe default ('NEUTRAL', never 'SUPPORTING').
5. Insert and read records through migrated schema.
6. Downgrade to 0020 (verifying safe removal of Wave 4 tables and retention of Waves 1-3).
7. Upgrade back to head (verifying idempotent re-application).
"""
import os
import sys
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
    db_file = tmp_path / "test_migration.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    ini_path = DATABASE_DIR / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", db_url)

    # Also set env so env.py pick it up if needed
    os.environ["DATABASE_URL"] = db_url
    os.environ["POSTGRES_URL"] = db_url

    return cfg, db_url, db_file


def test_alembic_single_head_and_revision_chain():
    """Verify Alembic migration tree has a single head and expected revision lineage."""
    cfg = Config(str(DATABASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))

    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1, f"Expected exactly 1 migration head, found: {heads}"
    assert heads[0] in ("0021_validation_os", "0022_launch_actuals_os", "0023_growth_os", "0024_wave6_integrity")

    rev_0021 = script.get_revision("0021_validation_os")
    assert rev_0021.down_revision == "0020_opportunity_fit_matching"

    rev_0020 = script.get_revision("0020_opportunity_fit_matching")
    assert rev_0020.down_revision == "0019_verified_opportunities"


def test_alembic_migration_0020_to_0021_upgrade_and_downgrade(alembic_config):
    """Full lifecycle migration test exercising 0020 -> 0021 upgrade, schema verification, data roundtrip, downgrade, and re-upgrade."""
    cfg, db_url, _ = alembic_config

    engine = sa.create_engine(db_url)

    # --- STEP 1: Upgrade to 0020 ---
    command.upgrade(cfg, "0020_opportunity_fit_matching")

    inspector_0020 = sa.inspect(engine)
    tables_0020 = set(inspector_0020.get_table_names())

    # Verify Waves 1-3 tables exist
    assert "users" in tables_0020
    assert "projects" in tables_0020
    assert "feasibility_studies" in tables_0020
    assert "verified_opportunities" in tables_0020
    assert "opportunity_fit_profiles" in tables_0020

    # Verify Wave 4 tables DO NOT yet exist at 0020
    wave4_tables = {
        "validation_workspaces",
        "validation_hypotheses",
        "validation_experiments",
        "validation_evidence",
        "validation_decisions",
    }
    for t in wave4_tables:
        assert t not in tables_0020, f"Table {t} should not exist before 0021 migration"

    # Verify Wave 5 tables DO NOT exist
    assert "launch_workspaces" not in tables_0020
    assert "launch_milestones" not in tables_0020

    # --- STEP 2: Upgrade to 0021_validation_os ---
    command.upgrade(cfg, "0021_validation_os")

    inspector_0021 = sa.inspect(engine)
    tables_0021 = set(inspector_0021.get_table_names())

    # Verify all Wave 4 tables now exist
    for t in wave4_tables:
        assert t in tables_0021, f"Table {t} must exist after 0021 migration"

    # Verify Wave 5 tables are strictly excluded
    assert "launch_workspaces" not in tables_0021, "Wave 5 launch_workspaces must NOT be created in Wave 4 migration"
    assert "launch_milestones" not in tables_0021, "Wave 5 launch_milestones must NOT be created in Wave 4 migration"
    assert "launch_actual_metrics" not in tables_0021, "Wave 5 launch_actual_metrics must NOT be created in Wave 4 migration"

    # --- STEP 3: Verify Column semantics on validation_evidence ---
    evidence_columns = {c["name"]: c for c in inspector_0021.get_columns("validation_evidence")}
    assert "evidence_direction" in evidence_columns, "validation_evidence.evidence_direction column must exist"
    assert "is_simulated" in evidence_columns
    assert "evidence_strength" in evidence_columns
    assert "structured_payload" in evidence_columns
    assert "source_url" in evidence_columns

    ev_dir_col = evidence_columns["evidence_direction"]
    assert not ev_dir_col["nullable"], "evidence_direction must be non-nullable"

    # Verify default is NEUTRAL, NEVER SUPPORTING
    default_str = str(ev_dir_col.get("default") or "")
    assert "NEUTRAL" in default_str, f"evidence_direction default must be NEUTRAL, got '{default_str}'"
    assert "SUPPORTING" not in default_str, "evidence_direction default must NEVER be SUPPORTING"

    # --- STEP 4: Verify Foreign Keys & Indexes ---
    fks_workspaces = [fk["referred_table"] for fk in inspector_0021.get_foreign_keys("validation_workspaces")]
    assert "projects" in fks_workspaces
    assert "users" in fks_workspaces

    fks_hypotheses = [fk["referred_table"] for fk in inspector_0021.get_foreign_keys("validation_hypotheses")]
    assert "validation_workspaces" in fks_hypotheses

    fks_evidence = [fk["referred_table"] for fk in inspector_0021.get_foreign_keys("validation_evidence")]
    assert "validation_workspaces" in fks_evidence

    fks_decisions = [fk["referred_table"] for fk in inspector_0021.get_foreign_keys("validation_decisions")]
    assert "validation_workspaces" in fks_decisions

    # --- STEP 5: Insert and read a minimal Wave 4 record through migrated schema ---
    with engine.begin() as conn:
        # Create minimal user, project, study
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

        # Insert into validation_workspaces
        conn.execute(
            sa.text(
                "INSERT INTO validation_workspaces (project_id, study_id, user_id, status, created_at, updated_at) "
                f"VALUES ({proj_id}, {study_id}, {user_id}, 'NEEDS_EVIDENCE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        ws_id = conn.execute(sa.text(f"SELECT id FROM validation_workspaces WHERE project_id={proj_id}")).scalar()
        assert ws_id is not None

        # Insert into validation_hypotheses
        conn.execute(
            sa.text(
                "INSERT INTO validation_hypotheses (workspace_id, hypothesis_type, statement, importance, status, created_at, updated_at) "
                f"VALUES ({ws_id}, 'CUSTOMER_PROBLEM', 'Customers need automated billing', 'CRITICAL', 'TESTING', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        hypo_id = conn.execute(sa.text(f"SELECT id FROM validation_hypotheses WHERE workspace_id={ws_id}")).scalar()
        assert hypo_id is not None

        # Insert into validation_evidence using default direction
        conn.execute(
            sa.text(
                "INSERT INTO validation_evidence (workspace_id, hypothesis_id, evidence_type, title, source_type, evidence_strength, is_simulated, created_at, updated_at) "
                f"VALUES ({ws_id}, {hypo_id}, 'USER_RECORDED', 'Initial Survey', 'USER_RECORDED', 'MODERATE', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        ev_row = conn.execute(
            sa.text(f"SELECT id, evidence_direction, is_simulated FROM validation_evidence WHERE workspace_id={ws_id}")
        ).mappings().first()
        assert ev_row is not None
        assert ev_row["evidence_direction"] == "NEUTRAL", f"Expected default NEUTRAL, got {ev_row['evidence_direction']}"
        assert ev_row["is_simulated"] in (False, 0)

        # Insert decision
        conn.execute(
            sa.text(
                "INSERT INTO validation_decisions (workspace_id, decision, decision_reason, evidence_snapshot, created_at, updated_at) "
                f"VALUES ({ws_id}, 'GO', 'All validated', '{{}}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        dec_id = conn.execute(sa.text(f"SELECT id FROM validation_decisions WHERE workspace_id={ws_id}")).scalar()
        assert dec_id is not None

    # --- STEP 6: Downgrade back to 0020 ---
    command.downgrade(cfg, "0020_opportunity_fit_matching")

    inspector_downgrade = sa.inspect(engine)
    tables_downgraded = set(inspector_downgrade.get_table_names())

    # Verify Wave 4 tables removed
    for t in wave4_tables:
        assert t not in tables_downgraded, f"Table {t} should have been dropped during downgrade"

    # Verify Wave 1-3 tables remain intact
    assert "users" in tables_downgraded
    assert "projects" in tables_downgraded
    assert "feasibility_studies" in tables_downgraded
    assert "verified_opportunities" in tables_downgraded
    assert "opportunity_fit_profiles" in tables_downgraded

    # --- STEP 7: Re-upgrade to 0021 (idempotency check) ---
    command.upgrade(cfg, "0021_validation_os")
    inspector_reupgrade = sa.inspect(engine)
    tables_reupgraded = set(inspector_reupgrade.get_table_names())
    for t in wave4_tables:
        assert t in tables_reupgraded, f"Table {t} must be recreated upon re-upgrade"

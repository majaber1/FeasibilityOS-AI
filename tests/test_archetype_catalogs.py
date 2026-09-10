"""Catalog invariants for archetype-adaptive AI feasibility workflow."""
from __future__ import annotations

from ai_engine.archetypes import (
    ARCHETYPE_ASSUMPTION_KEYS,
    ARCHETYPE_QUESTIONS,
    ARCHETYPE_RISK_THEMES,
    assumption_keys_for,
    questions_for,
    saas_marker_hits,
)


REQUIRED = {
    "saas_digital",
    "real_estate",
    "data_center",
    "services",
    "retail",
    "industrial",
    "franchise",
}
NON_SAAS = REQUIRED - {"saas_digital"}


def test_all_archetypes_have_question_catalogs():
    assert REQUIRED.issubset(ARCHETYPE_QUESTIONS.keys())
    for archetype in REQUIRED:
        assert questions_for(archetype, "en"), archetype
        assert questions_for(archetype, "ar"), archetype


def test_non_saas_questions_exclude_saas_markers():
    for archetype in NON_SAAS:
        hits = saas_marker_hits(questions_for(archetype, "en") + questions_for(archetype, "ar"))
        assert hits == [], f"{archetype} leaked SaaS markers: {hits}"


def test_real_estate_questions_cover_construction_drivers():
    blob = " ".join(questions_for("real_estate", "en")).lower()
    for needle in ("land", "construction", "unit", "sale", "rent"):
        assert needle in blob, needle


def test_data_center_questions_cover_infrastructure_drivers():
    blob = " ".join(questions_for("data_center", "en")).lower()
    for needle in ("mw", "tier", "pue", "rack", "occupancy", "kwh"):
        assert needle in blob, needle


def test_services_questions_are_marketplace_not_saas():
    blob = " ".join(questions_for("services", "en")).lower()
    assert "take-rate" in blob or "commission" in blob or "take rate" in blob
    assert "trip" in blob or "transaction" in blob
    assert "cac" not in blob
    assert "churn" not in blob


def test_assumption_keys_differ_by_archetype():
    saas = set(assumption_keys_for("saas_digital"))
    real_estate = set(assumption_keys_for("real_estate"))
    data_center = set(assumption_keys_for("data_center"))
    services = set(assumption_keys_for("services"))
    assert "cac" in saas
    assert "land_cost" in real_estate or "construction_boq" in real_estate
    assert "it_load_mw" in data_center or "price_per_kw_month" in data_center
    assert "take_rate" in services or "average_trip_value" in services
    assert "cac" not in real_estate
    assert "cac" not in data_center


def test_risk_themes_bound_per_archetype():
    assert ARCHETYPE_RISK_THEMES["real_estate"]
    assert ARCHETYPE_RISK_THEMES["data_center"]
    assert ARCHETYPE_RISK_THEMES["services"]
    assert ARCHETYPE_ASSUMPTION_KEYS["real_estate"]

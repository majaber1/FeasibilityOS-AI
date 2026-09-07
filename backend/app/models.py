"""
ORM models for Saudi Business | سعودي بزنس.

Types are kept portable (generic String/Integer/Float/JSON) so the same models
run on SQLite (tests) and PostgreSQL (production). Every table has created_at /
updated_at timestamps and appropriate indexes and foreign keys.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_ar: Mapped[Optional[str]] = mapped_column(String(200))
    cr_number: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    sector: Mapped[Optional[str]] = mapped_column(String(100))

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    projects: Mapped[list["Project"]] = relationship(back_populates="organization")


class Role(TimestampMixin, Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    permissions: Mapped[dict] = mapped_column(JSON, default=dict)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(200))
    locale: Mapped[str] = mapped_column(String(5), default="ar")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    role_key: Mapped[str] = mapped_column(String(50), ForeignKey("roles.key"), default="entrepreneur")
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"))

    organization: Mapped[Optional["Organization"]] = relationship(back_populates="users")
    projects: Mapped[list["Project"]] = relationship(back_populates="owner")


class AccountToken(TimestampMixin, Base):
    """Single-use, hashed email-verification or password-reset token."""

    __tablename__ = "account_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    purpose: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    investment: Mapped[float] = mapped_column(Float, nullable=False)
    stage: Mapped[str] = mapped_column(String(30), default="idea")
    workflow_status: Mapped[str] = mapped_column(String(30), default="created")
    # Soft-archive: archived projects are hidden from the default list but
    # never hard-deleted, so dependent feasibility studies / reports are not
    # orphaned. is_archived is the authoritative flag; archived_at records when.
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"))

    owner: Mapped[Optional["User"]] = relationship(back_populates="projects")
    organization: Mapped[Optional["Organization"]] = relationship(back_populates="projects")
    studies: Mapped[list["FeasibilityStudy"]] = relationship(back_populates="project")


class FeasibilityStudy(TimestampMixin, Base):
    __tablename__ = "feasibility_studies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    study_type: Mapped[str] = mapped_column(String(50), default="general")
    status: Mapped[str] = mapped_column(String(30), default="draft")
    current_step: Mapped[int] = mapped_column(Integer, default=1)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)

    project: Mapped["Project"] = relationship(back_populates="studies")
    assumptions: Mapped[list["FinancialAssumption"]] = relationship(back_populates="study")
    results: Mapped[list["FinancialResult"]] = relationship(back_populates="study")
    scenarios: Mapped[list["SensitivityScenario"]] = relationship(back_populates="study")
    evidence_items: Mapped[list["EvidenceItem"]] = relationship(back_populates="study")
    study_assumptions: Mapped[list["StudyAssumption"]] = relationship(
        back_populates="study", foreign_keys="StudyAssumption.study_id"
    )
    business_profile: Mapped[Optional["BusinessProfile"]] = relationship(back_populates="study", uselist=False)
    source_opportunity_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("verified_opportunities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_opportunity_version: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    source_opportunity_lineage: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    source_opportunity: Mapped[Optional["VerifiedOpportunity"]] = relationship(foreign_keys=[source_opportunity_id])


class FinancialAssumption(TimestampMixin, Base):
    __tablename__ = "financial_assumptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("feasibility_studies.id"), index=True, nullable=False)
    capex: Mapped[float] = mapped_column(Float, default=0.0)
    opex_annual: Mapped[float] = mapped_column(Float, default=0.0)
    revenue_year1: Mapped[float] = mapped_column(Float, default=0.0)
    growth_rate: Mapped[float] = mapped_column(Float, default=0.0)
    discount_rate: Mapped[float] = mapped_column(Float, default=0.10)
    horizon_years: Mapped[int] = mapped_column(Integer, default=5)

    study: Mapped["FeasibilityStudy"] = relationship(back_populates="assumptions")


class FinancialResult(TimestampMixin, Base):
    __tablename__ = "financial_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("feasibility_studies.id"), index=True, nullable=False)
    roi: Mapped[Optional[float]] = mapped_column(Float)
    npv: Mapped[Optional[float]] = mapped_column(Float)
    irr: Mapped[Optional[float]] = mapped_column(Float)
    payback_years: Mapped[Optional[float]] = mapped_column(Float)
    break_even: Mapped[Optional[float]] = mapped_column(Float)
    verdict: Mapped[Optional[str]] = mapped_column(String(30))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)

    study: Mapped["FeasibilityStudy"] = relationship(back_populates="results")


class SensitivityScenario(TimestampMixin, Base):
    __tablename__ = "sensitivity_scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("feasibility_studies.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50))  # conservative | base | optimistic
    revenue_delta: Mapped[float] = mapped_column(Float, default=0.0)
    npv: Mapped[Optional[float]] = mapped_column(Float)
    irr: Mapped[Optional[float]] = mapped_column(Float)

    study: Mapped["FeasibilityStudy"] = relationship(back_populates="scenarios")


class BusinessProfile(TimestampMixin, Base):
    """Structured, reusable business facts for a Study (one profile per study).

    Both the feasibility flow and the funding flow (Entry 3: "أبحث عن تمويل")
    read/write this same row, so a user who already described their business
    is never asked to re-enter it. Distinct from Project (name/industry/
    investment/stage, the lightweight root record) and from the later
    CompanyFinancialProfile (period financial statements for existing
    businesses) -- this is the qualitative "what is this business" record.
    """

    __tablename__ = "business_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("feasibility_studies.id"), unique=True, index=True, nullable=False)

    business_activity: Mapped[Optional[str]] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    region: Mapped[Optional[str]] = mapped_column(String(100))
    customer_segment: Mapped[Optional[str]] = mapped_column(String(200))

    capacity_value: Mapped[Optional[float]] = mapped_column(Float)
    capacity_unit: Mapped[Optional[str]] = mapped_column(String(50))

    legal_entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    ownership_notes: Mapped[Optional[str]] = mapped_column(Text)

    is_existing_business: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    company_age_years: Mapped[Optional[float]] = mapped_column(Float)
    current_revenue: Mapped[Optional[float]] = mapped_column(Float)

    study: Mapped["FeasibilityStudy"] = relationship(back_populates="business_profile")


class CompanyFinancialPeriod(TimestampMixin, Base):
    """One period (e.g. "FY2024") of an existing company's financial profile.

    Every metric is nullable -- a metric the user/document doesn't provide
    stays NULL, it is never defaulted to zero or estimated. `source`
    classifies how trustworthy the whole period record is; `document_id`
    optionally traces it to a specific uploaded document (see
    ExtractedFinancialFact for line-item-level provenance when that level of
    detail is needed). Distinct from BusinessProfile (qualitative facts) and
    from FinancialAssumption/FinancialResult (the new-business feasibility
    model) -- this is period financial-statement data for a business that
    already exists.
    """

    __tablename__ = "company_financial_periods"
    __table_args__ = (UniqueConstraint("study_id", "period", name="uq_company_financial_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("feasibility_studies.id"), index=True, nullable=False)
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("documents.id"))
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))

    period: Mapped[str] = mapped_column(String(50), nullable=False)
    # financial_statement|bank_statement|user_confirmed|audited_statement|management_account|unverified
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="unverified")

    revenue: Mapped[Optional[float]] = mapped_column(Float)
    gross_profit: Mapped[Optional[float]] = mapped_column(Float)
    ebitda: Mapped[Optional[float]] = mapped_column(Float)
    operating_profit: Mapped[Optional[float]] = mapped_column(Float)
    net_profit: Mapped[Optional[float]] = mapped_column(Float)
    cash: Mapped[Optional[float]] = mapped_column(Float)
    current_assets: Mapped[Optional[float]] = mapped_column(Float)
    current_liabilities: Mapped[Optional[float]] = mapped_column(Float)
    total_assets: Mapped[Optional[float]] = mapped_column(Float)
    total_liabilities: Mapped[Optional[float]] = mapped_column(Float)
    equity: Mapped[Optional[float]] = mapped_column(Float)
    existing_debt: Mapped[Optional[float]] = mapped_column(Float)
    annual_debt_service: Mapped[Optional[float]] = mapped_column(Float)
    accounts_receivable: Mapped[Optional[float]] = mapped_column(Float)
    inventory: Mapped[Optional[float]] = mapped_column(Float)
    capital_expenditure: Mapped[Optional[float]] = mapped_column(Float)
    # Needed for Interest Coverage (operating_profit / interest_expense) in
    # the Phase 11 financial health engine -- distinct from
    # annual_debt_service (principal + interest, used for DSCR).
    interest_expense: Mapped[Optional[float]] = mapped_column(Float)

    study: Mapped["FeasibilityStudy"] = relationship()


class ScenarioRun(TimestampMixin, Base):
    """An immutable, deterministic scenario snapshot for a study.

    Explicit assumption overrides layered on top of the study's active
    assumptions at computation time -- never a blanket +/-% shock, and never
    a mutation of the study's actual assumptions (Base assumptions are
    untouched; see app.api.scenarios). source_assumption_values records the
    full input set actually used (both from base assumptions and from
    overrides) with enough detail to reproduce or explain the result later,
    even after the underlying assumptions change. financial_result_snapshot
    freezes the computed output; calculation_version records which formula
    version produced it so a future engine change never silently
    reinterprets an old snapshot.
    """

    __tablename__ = "scenario_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("feasibility_studies.id"), index=True, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))

    scenario_type: Mapped[str] = mapped_column(String(20), nullable=False)  # CONSERVATIVE|BASE|OPTIMISTIC
    scenario_name: Mapped[str] = mapped_column(String(200), nullable=False)

    assumption_overrides: Mapped[dict] = mapped_column(JSON, default=dict)
    source_assumption_values: Mapped[dict] = mapped_column(JSON, default=dict)
    financial_result_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    calculation_version: Mapped[str] = mapped_column(String(50), nullable=False)

    study: Mapped["FeasibilityStudy"] = relationship()


class StudyDecision(TimestampMixin, Base):
    """An immutable, explainable decision snapshot for a study.

    Derived deterministically (see app.services.decision_engine) from the
    study's evidence count and its latest BASE/CONSERVATIVE ScenarioRun
    snapshots -- never an arbitrary AI-generated success score. Each POST
    creates a new record rather than overwriting the last one, so the
    decision history (e.g. CONDITIONAL_GO -> GO after an assumption
    improved) stays inspectable, matching the same immutable-snapshot
    pattern as ScenarioRun.
    """

    __tablename__ = "study_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("feasibility_studies.id"), index=True, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))

    decision: Mapped[str] = mapped_column(String(30), nullable=False)  # GO|CONDITIONAL_GO|NO_GO|INSUFFICIENT_EVIDENCE
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    conditions: Mapped[list] = mapped_column(JSON, default=list)
    key_drivers: Mapped[list] = mapped_column(JSON, default=list)
    key_risks: Mapped[list] = mapped_column(JSON, default=list)

    evidence_references: Mapped[list] = mapped_column(JSON, default=list)
    scenario_references: Mapped[dict] = mapped_column(JSON, default=dict)

    study: Mapped["FeasibilityStudy"] = relationship()


class CollateralItem(TimestampMixin, Base):
    """A single collateral asset recorded for a study (Wave 2: Funding Intelligence).

    Values are stored and explained, never converted into an assumed
    lendable/borrowing amount here -- market value is not lendable value,
    and no lender haircut is applied (see app.services.collateral). A
    verified_value may only be set when verification_status is
    DOCUMENT_SUPPORTED or VERIFIED -- typing a number never itself verifies
    it. Consistency (non-negative values, encumbrance_amount only present
    when the encumbrance status requires it, encumbrance_amount never
    exceeding the asset's value) is enforced in the API layer
    (app.services.collateral.validate_consistency) so it applies the same
    way to both create and partial update.
    """

    __tablename__ = "collateral_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("feasibility_studies.id"), index=True, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))

    # PROPERTY|EQUIPMENT|CASH|RECEIVABLES|GUARANTEE|OTHER
    collateral_type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    reported_value: Mapped[float] = mapped_column(Float, nullable=False)
    verified_value: Mapped[Optional[float]] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="SAR", nullable=False)

    valuation_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    valuation_source: Mapped[Optional[str]] = mapped_column(String(200))

    ownership_status: Mapped[Optional[str]] = mapped_column(String(100))

    # UNENCUMBERED|PARTIALLY_ENCUMBERED|FULLY_ENCUMBERED|UNKNOWN
    encumbrance_status: Mapped[str] = mapped_column(String(30), default="UNKNOWN", nullable=False)
    encumbrance_amount: Mapped[Optional[float]] = mapped_column(Float)
    lien_holder: Mapped[Optional[str]] = mapped_column(String(200))

    # UNVERIFIED|USER_REPORTED|DOCUMENT_SUPPORTED|VERIFIED
    verification_status: Mapped[str] = mapped_column(String(30), default="USER_REPORTED", nullable=False)

    notes: Mapped[Optional[str]] = mapped_column(Text)

    study: Mapped["FeasibilityStudy"] = relationship()


class FundingProgram(TimestampMixin, Base):
    """A verified Saudi funding program (Wave 2: Funding Intelligence).

    Represents genuine funding programs from official Saudi development finance
    institutions (e.g. SDB, Kafalah, SME Bank, SIDF, TDF, ADF).
    Every program record stores explicit limits, terms, and eligibility rules
    with provenance links back to official sources (.gov.sa portals).
    No limits or eligibility criteria are invented.
    """

    __tablename__ = "funding_programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    provider_ar: Mapped[str] = mapped_column(String(150), nullable=False)
    program_name_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    program_name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    description_ar: Mapped[Optional[str]] = mapped_column(Text)
    description_en: Mapped[Optional[str]] = mapped_column(Text)

    # DIRECT_LOAN | GUARANTEE | CO_FINANCING | WORKING_CAPITAL | GRANT
    program_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # STARTUP | EXISTING | EXPANSION | ALL
    target_business_stage: Mapped[str] = mapped_column(String(50), default="ALL", nullable=False)
    target_sectors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    financing_min: Mapped[Optional[float]] = mapped_column(Float)
    financing_max: Mapped[Optional[float]] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="SAR", nullable=False)
    term_months: Mapped[Optional[int]] = mapped_column(Integer)
    grace_period_months: Mapped[Optional[int]] = mapped_column(Integer)

    # Structured rules
    owner_contribution_rule: Mapped[Optional[dict]] = mapped_column(JSON)
    collateral_rule: Mapped[Optional[dict]] = mapped_column(JSON)
    guarantee_rule: Mapped[Optional[dict]] = mapped_column(JSON)
    revenue_rule: Mapped[Optional[dict]] = mapped_column(JSON)
    business_age_rule: Mapped[Optional[dict]] = mapped_column(JSON)
    other_eligibility_rules: Mapped[Optional[list]] = mapped_column(JSON)

    # Source & Provenance
    official_source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="OFFICIAL_PROVIDER", nullable=False)
    source_owner: Mapped[str] = mapped_column(String(200), nullable=False)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    last_verified_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    effective_from: Mapped[Optional[str]] = mapped_column(String(50))
    effective_to: Mapped[Optional[str]] = mapped_column(String(50))

    # VERIFIED_CURRENT | VERIFIED_PARTIAL | UNVERIFIED | STALE | CHANGED | DISCONTINUED
    verification_status: Mapped[str] = mapped_column(String(30), default="VERIFIED_CURRENT", index=True, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)

    rules: Mapped[list["FundingProgramRule"]] = relationship(
        back_populates="program", cascade="all, delete-orphan", order_by="FundingProgramRule.id"
    )


class FundingProgramRule(TimestampMixin, Base):
    """Granular rule provenance record for a funding program rule.

    Every important requirement (financing limit, owner equity, collateral,
    term, revenue threshold, age) retains evidence linking it to the exact
    section, article, or URL on the official source.
    """

    __tablename__ = "funding_program_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("funding_programs.id", ondelete="CASCADE"), index=True, nullable=False)
    rule_key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), default="ELIGIBILITY", nullable=False)
    structured_value: Mapped[dict] = mapped_column(JSON, nullable=False)
    description_ar: Mapped[Optional[str]] = mapped_column(Text)
    description_en: Mapped[Optional[str]] = mapped_column(Text)

    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_reference: Mapped[Optional[str]] = mapped_column(String(255))
    source_authority: Mapped[str] = mapped_column(String(100), default="OFFICIAL_PROVIDER", nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    verified_by: Mapped[Optional[str]] = mapped_column(String(100), default="OFFICIAL_REGISTRY")
    rule_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    program: Mapped["FundingProgram"] = relationship(back_populates="rules")



class EvidenceItem(TimestampMixin, Base):
    """A single sourced fact attached to a study, with full provenance.

    Every factual claim a study's analysis, report, or AI advisor relies on
    must trace back to a row here (or be recorded as an explicit
    StudyAssumption). authority_level and source_type together let the UI/API
    tell a VERIFIED_FACT apart from an UNVERIFIED claim; both are always
    computed/validated server-side (see app.services.source_registry) so
    client input can never self-certify as official evidence.
    """

    __tablename__ = "evidence_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("feasibility_studies.id"), index=True, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))

    # official_statistic|regulation|funding_program|market_report|news|survey|user_document|ai_inference|other
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_name: Mapped[Optional[str]] = mapped_column(String(200))
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    publisher: Mapped[Optional[str]] = mapped_column(String(200))

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    value_number: Mapped[Optional[float]] = mapped_column(Float)
    value_text: Mapped[Optional[str]] = mapped_column(String(300))
    unit: Mapped[Optional[str]] = mapped_column(String(50))

    geography: Mapped[Optional[str]] = mapped_column(String(100))
    sector: Mapped[Optional[str]] = mapped_column(String(100))

    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    # Temporal validity: when this fact is/was actually in effect, distinct
    # from when it was published or retrieved. superseded_by_id lets a newer
    # snapshot supersede an older one without deleting audit history.
    effective_from: Mapped[Optional[datetime]] = mapped_column(DateTime)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime)
    superseded_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("evidence_items.id"))

    confidence: Mapped[str] = mapped_column(String(20), default="medium")  # low|medium|high
    # verified|user_provided|unverified -- never "fact" without one of these.
    verification_status: Mapped[str] = mapped_column(String(30), default="unverified", nullable=False)
    # OFFICIAL_PRIMARY|OFFICIAL_SECONDARY|REGULATOR|REPUTABLE_INSTITUTION|
    # COMMERCIAL_SOURCE|USER_DOCUMENT|AI_INFERENCE|UNVERIFIED
    authority_level: Mapped[str] = mapped_column(String(30), default="UNVERIFIED", nullable=False)

    # The actual retrieved text/quote the claim is based on, plus a checksum
    # so later edits/staleness are detectable.
    snapshot_text: Mapped[Optional[str]] = mapped_column(Text)
    snapshot_hash: Mapped[Optional[str]] = mapped_column(String(64))

    study: Mapped["FeasibilityStudy"] = relationship(back_populates="evidence_items")


class StudyAssumption(TimestampMixin, Base):
    """A versioned, provenance-tagged assumption used in a study's analysis.

    Distinct from EvidenceItem: an assumption is a value the study *uses*
    (rent, headcount, utilization...), which may or may not be derived from
    evidence. Writing a new assumption for a key that already has an active
    row retires the old row (is_active=False) and bumps version rather than
    overwriting it, so the assumption's history stays inspectable.
    """

    __tablename__ = "study_assumptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("feasibility_studies.id"), index=True, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    evidence_id: Mapped[Optional[int]] = mapped_column(ForeignKey("evidence_items.id"))

    key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    label_en: Mapped[str] = mapped_column(String(200), nullable=False)
    label_ar: Mapped[str] = mapped_column(String(200), nullable=False)

    value_number: Mapped[Optional[float]] = mapped_column(Float)
    value_text: Mapped[Optional[str]] = mapped_column(String(300))
    unit: Mapped[Optional[str]] = mapped_column(String(50))

    # USER|EVIDENCE_DERIVED|AI_SUGGESTED|DEFAULT -- AI_SUGGESTED must never be
    # silently treated as a verified market fact by any downstream consumer.
    origin: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(20), default="medium")
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    study: Mapped["FeasibilityStudy"] = relationship(back_populates="study_assumptions", foreign_keys=[study_id])
    evidence: Mapped[Optional["EvidenceItem"]] = relationship()


class IdeaBankEntry(TimestampMixin, Base):
    __tablename__ = "idea_bank_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title_en: Mapped[str] = mapped_column(String(200), nullable=False)
    title_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str] = mapped_column(String(100), index=True)
    summary_en: Mapped[Optional[str]] = mapped_column(Text)
    summary_ar: Mapped[Optional[str]] = mapped_column(Text)
    problem: Mapped[Optional[str]] = mapped_column(Text)
    solution: Mapped[Optional[str]] = mapped_column(Text)
    revenue_model: Mapped[Optional[str]] = mapped_column(String(200))
    investment_min: Mapped[Optional[float]] = mapped_column(Float)
    investment_max: Mapped[Optional[float]] = mapped_column(Float)
    difficulty: Mapped[Optional[str]] = mapped_column(String(20))
    time_to_launch: Mapped[Optional[str]] = mapped_column(String(50))
    vision2030_alignment: Mapped[Optional[str]] = mapped_column(String(200))
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="published")
    source: Mapped[Optional[str]] = mapped_column(String(300))


class FranchiseOpportunity(TimestampMixin, Base):
    __tablename__ = "franchise_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand: Mapped[str] = mapped_column(String(200), nullable=False)
    description_en: Mapped[Optional[str]] = mapped_column(Text)
    description_ar: Mapped[Optional[str]] = mapped_column(Text)
    sector: Mapped[str] = mapped_column(String(100), index=True)
    country: Mapped[Optional[str]] = mapped_column(String(80))
    regions: Mapped[list] = mapped_column(JSON, default=list)
    investment_min: Mapped[Optional[float]] = mapped_column(Float)
    investment_max: Mapped[Optional[float]] = mapped_column(Float)
    franchise_fee: Mapped[Optional[float]] = mapped_column(Float)
    royalty_model: Mapped[Optional[str]] = mapped_column(String(150))
    required_space: Mapped[Optional[str]] = mapped_column(String(100))
    application_url: Mapped[Optional[str]] = mapped_column(String(500))
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    verification_status: Mapped[str] = mapped_column(String(30), default="demo")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class InvestmentOpportunity(TimestampMixin, Base):
    """Investor-facing catalog: projects/ventures open for outside investment.

    Distinct from Project (a founder's own feasibility workspace) -- an
    opportunity is what an investor browses and filters by ticket size.
    expected_return_percent is always an indicative, source-labeled estimate,
    never presented as a guarantee (see Source of truth README section 6).
    """

    __tablename__ = "investment_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title_en: Mapped[str] = mapped_column(String(200), nullable=False)
    title_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str] = mapped_column(String(100), index=True)
    summary_en: Mapped[Optional[str]] = mapped_column(Text)
    summary_ar: Mapped[Optional[str]] = mapped_column(Text)
    stage: Mapped[str] = mapped_column(String(30), default="mvp")  # idea|mvp|early_revenue|growth
    risk_level: Mapped[str] = mapped_column(String(20), default="medium")  # low|medium|high
    investment_min: Mapped[Optional[float]] = mapped_column(Float, index=True)
    investment_max: Mapped[Optional[float]] = mapped_column(Float)
    expected_return_percent: Mapped[Optional[float]] = mapped_column(Float)
    funding_goal: Mapped[Optional[float]] = mapped_column(Float)
    funding_committed: Mapped[Optional[float]] = mapped_column(Float, default=0)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"))
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    verification_status: Mapped[str] = mapped_column(String(30), default="demo")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class MultazimRequirement(TimestampMixin, Base):
    __tablename__ = "multazim_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    title_en: Mapped[str] = mapped_column(String(200), nullable=False)
    title_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    description_en: Mapped[Optional[str]] = mapped_column(Text)
    description_ar: Mapped[Optional[str]] = mapped_column(Text)
    authority: Mapped[Optional[str]] = mapped_column(String(150))
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500))


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"))
    # Optional link into a specific study (e.g. an existing company's
    # financial statements attached to a funding study). Nullable/additive so
    # existing project-only documents (funding proposal uploads) are unaffected.
    study_id: Mapped[Optional[int]] = mapped_column(ForeignKey("feasibility_studies.id"), index=True)
    # financial_statement|bank_statement|cr_document|asset_schedule|
    # debt_schedule|guarantee|project_proposal|other
    document_type: Mapped[Optional[str]] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(100))
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    storage_ref: Mapped[Optional[str]] = mapped_column(String(500))

    extracted_facts: Mapped[list["ExtractedFinancialFact"]] = relationship(back_populates="document")


class ExtractedFinancialFact(TimestampMixin, Base):
    """A structured fact traced to a specific uploaded document.

    There is currently no automated OCR/document-understanding integration
    configured in this environment (see docs/architecture/CURRENT_STATE_AUDIT.md);
    every row here is entered by a human who read the source document, which
    is why extraction_status defaults to "user_entered" rather than an
    automated-confidence tier. The schema is forward-compatible with an
    automated pipeline (extraction_status/confidence are free strings, not a
    DB enum) so that capability can be added later without a migration --
    but nothing in this codebase currently claims to parse documents
    automatically, and a low-confidence row must never be presented as a
    verified financial fact (see review_status).
    """

    __tablename__ = "extracted_financial_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("feasibility_studies.id"), index=True, nullable=False)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))

    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value_number: Mapped[Optional[float]] = mapped_column(Float)
    value_text: Mapped[Optional[str]] = mapped_column(String(300))
    unit: Mapped[Optional[str]] = mapped_column(String(50))
    period: Mapped[Optional[str]] = mapped_column(String(50))
    source_location: Mapped[Optional[str]] = mapped_column(String(200))

    extraction_status: Mapped[str] = mapped_column(String(30), default="user_entered", nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), default="high", nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), default="confirmed", nullable=False)

    document: Mapped["Document"] = relationship(back_populates="extracted_facts")
    study: Mapped["FeasibilityStudy"] = relationship()


class Report(TimestampMixin, Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("feasibility_studies.id"), index=True, nullable=False)
    fmt: Mapped[str] = mapped_column(String(10))  # pdf | docx
    locale: Mapped[str] = mapped_column(String(5), default="ar")
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    storage_ref: Mapped[Optional[str]] = mapped_column(String(500))


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (UniqueConstraint("id", name="uq_audit_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity: Mapped[Optional[str]] = mapped_column(String(100))
    entity_id: Mapped[Optional[int]] = mapped_column(Integer)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


# ---------------------------------------------------------------------------
# Business Qualification & Readiness | التأهيل والجاهزية  (Saudi Business)
#
# Lightweight, business-facing readiness tracking for SMEs / establishments:
# qualification profiles, per-requirement status, and a *summarized* request
# for a deeper Multazim (institutional GRC) assessment. This intentionally does
# NOT implement full GRC (control libraries, evidence vault, risk register,
# internal audit, policy lifecycle) — that lives in the separate Multazim
# product. Only the summarized cross-product hand-off is modeled here.
# ---------------------------------------------------------------------------


class QualificationProfile(TimestampMixin, Base):
    """A company's Business Qualification & Readiness profile.

    Owned by a user (and optionally scoped to a project). Aggregates readiness
    across categories such as tender readiness, funding readiness, Saudization,
    and commercial/operational readiness.
    """

    __tablename__ = "qualification_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), index=True)

    company_name_en: Mapped[Optional[str]] = mapped_column(String(200))
    company_name_ar: Mapped[Optional[str]] = mapped_column(String(200))
    cr_number: Mapped[Optional[str]] = mapped_column(String(50))  # Commercial Registration
    sector: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    company_size: Mapped[Optional[str]] = mapped_column(String(30))  # micro|small|medium|large
    saudization_rate: Mapped[Optional[float]] = mapped_column(Float)  # 0..1

    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    category_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    recommendations: Mapped[list] = mapped_column(JSON, default=list)

    owner: Mapped[Optional["User"]] = relationship()
    requirements: Mapped[list["QualificationRequirement"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class QualificationRequirement(TimestampMixin, Base):
    """A single eligibility / readiness requirement within a profile.

    Categories (business-facing, not GRC controls): tender, funding, licenses,
    certificates, saudization, commercial, operational, eligibility.
    Status is one of: missing | pending | valid | expired | not_applicable.
    """

    __tablename__ = "qualification_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("qualification_profiles.id"), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(50), index=True)
    title_en: Mapped[str] = mapped_column(String(200), nullable=False)
    title_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    description_en: Mapped[Optional[str]] = mapped_column(Text)
    description_ar: Mapped[Optional[str]] = mapped_column(Text)
    authority: Mapped[Optional[str]] = mapped_column(String(150))
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="missing")
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("documents.id"))
    declared_reference: Mapped[Optional[str]] = mapped_column(String(300))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    source_url: Mapped[Optional[str]] = mapped_column(String(500))

    profile: Mapped["QualificationProfile"] = relationship(back_populates="requirements")


class MultazimAssessmentRequest(TimestampMixin, Base):
    """A request from Saudi Business for a deeper external Multazim assessment.

    Saudi Business only stores the request and a *summarized* result payload
    (score + short bilingual summary). It never stores the full institutional
    GRC assessment (controls, evidence, findings) — that stays in Multazim.
    """

    __tablename__ = "multazim_assessment_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("qualification_profiles.id"), index=True, nullable=False
    )
    requested_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    scope: Mapped[Optional[str]] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="requested")

    summary_score: Mapped[Optional[float]] = mapped_column(Float)
    summary_en: Mapped[Optional[str]] = mapped_column(Text)
    summary_ar: Mapped[Optional[str]] = mapped_column(Text)


class SalesLead(TimestampMixin, Base):
    """A captured sales/investor-interest lead from the public Pricing page.

    Intentionally NOT a payment or subscription record -- Saudi Business does
    not process payments. This is a contact-capture inbox for a human sales
    follow-up (email/call), the actual first step of a B2B sales pipeline.
    """

    __tablename__ = "sales_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    plan: Mapped[str] = mapped_column(String(50), default="starter")  # starter|professional|enterprise
    intent: Mapped[str] = mapped_column(String(50), default="subscribe")  # subscribe|enterprise|investor|consultant
    message: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="new")  # new|contacted|closed


class ServiceEntitlement(TimestampMixin, Base):
    __tablename__ = "service_entitlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    service_key: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    plan: Mapped[str] = mapped_column(String(30), default="starter")
    quota: Mapped[Optional[int]] = mapped_column(Integer)
    used: Mapped[int] = mapped_column(Integer, default=0)
    reset_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


class Proposal(TimestampMixin, Base):
    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    proposal_type: Mapped[str] = mapped_column(String(50), default="commercial")
    status: Mapped[str] = mapped_column(String(30), default="draft")
    locale: Mapped[str] = mapped_column(String(5), default="ar")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    feasibility_study_id: Mapped[Optional[int]] = mapped_column(ForeignKey("feasibility_studies.id"))


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    title_en: Mapped[str] = mapped_column(String(200), nullable=False)
    title_ar: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text)
    entity: Mapped[Optional[str]] = mapped_column(String(100))
    entity_id: Mapped[Optional[int]] = mapped_column(Integer)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)


class AnalyticsEvent(TimestampMixin, Base):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    service_key: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    entity: Mapped[Optional[str]] = mapped_column(String(100))
    entity_id: Mapped[Optional[int]] = mapped_column(Integer)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class VerifiedOpportunity(TimestampMixin, Base):
    """Verified Opportunity & Franchise Registry (Wave 3).

    Persists genuine Saudi business opportunities and franchise opportunities
    with full provenance traceable to official authorities (Monsha'at, Furas /
    Invest Saudi, Saudi Franchise Center, verified brand disclosures).
    Never invents economics, demand, or investment amounts.
    """

    __tablename__ = "verified_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    title_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    title_en: Mapped[str] = mapped_column(String(255), nullable=False)
    # BUSINESS_OPPORTUNITY | FRANCHISE
    opportunity_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    sector: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    subsector: Mapped[Optional[str]] = mapped_column(String(150))
    business_model: Mapped[Optional[str]] = mapped_column(String(100))
    target_customer: Mapped[Optional[str]] = mapped_column(String(100))
    geography: Mapped[str] = mapped_column(String(100), default="KSA_NATIONAL", nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    region: Mapped[Optional[str]] = mapped_column(String(100))

    # Published financial limits (strictly nullable if not officially published)
    investment_min: Mapped[Optional[float]] = mapped_column(Float)
    investment_max: Mapped[Optional[float]] = mapped_column(Float)
    franchise_fee: Mapped[Optional[float]] = mapped_column(Float)
    royalty_model: Mapped[Optional[str]] = mapped_column(String(200))
    required_space: Mapped[Optional[str]] = mapped_column(String(100))
    business_stage: Mapped[Optional[str]] = mapped_column(String(50), default="STARTUP")

    description_ar: Mapped[Optional[str]] = mapped_column(Text)
    description_en: Mapped[Optional[str]] = mapped_column(Text)
    brand_name: Mapped[Optional[str]] = mapped_column(String(200))

    # Source & Provenance
    official_source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_owner: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="OFFICIAL_GOVERNMENT", nullable=False)
    source_evidence: Mapped[Optional[dict]] = mapped_column(JSON)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    last_verified_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    effective_from: Mapped[Optional[str]] = mapped_column(String(50))
    effective_to: Mapped[Optional[str]] = mapped_column(String(50))
    source_last_modified: Mapped[Optional[str]] = mapped_column(String(50))

    # UNVERIFIED | VERIFIED_PARTIAL | VERIFIED_CURRENT | STALE | CHANGED | DISCONTINUED
    verification_status: Mapped[str] = mapped_column(String(30), default="UNVERIFIED", index=True, nullable=False)
    data_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Structured facts classification: published, platform_normalized, unknown, user_assumptions_needed
    facts_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    # Field-level provenance: explicit mapping of material decision fields to source excerpts & status
    field_provenance: Mapped[dict] = mapped_column(JSON, default=dict)

    version_history: Mapped[list["OpportunityVersionHistory"]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan", order_by="OpportunityVersionHistory.id.desc()"
    )


class OpportunityVersionHistory(TimestampMixin, Base):
    """Immutable revision history for verified opportunities."""

    __tablename__ = "opportunity_version_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(
        ForeignKey("verified_opportunities.id", ondelete="CASCADE"), index=True, nullable=False
    )
    data_version: Mapped[str] = mapped_column(String(20), nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    changed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    change_reason: Mapped[str] = mapped_column(String(255), nullable=False)

    opportunity: Mapped["VerifiedOpportunity"] = relationship(back_populates="version_history")


class OpportunityFitProfile(TimestampMixin, Base):
    """User Opportunity Fit Profile (Wave 3B).

    Stores user constraints and preferences for matching against verified opportunities.
    User inputs (capital, sectors, regions) are strictly labeled as USER_INPUT / USER_ASSUMPTION.
    """

    __tablename__ = "opportunity_fit_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    available_capital: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    capital_constraint_type: Mapped[str] = mapped_column(String(20), default="HARD", nullable=False)  # HARD | PREFERENCE

    preferred_sectors: Mapped[list[str]] = mapped_column(JSON, default=list)
    excluded_sectors: Mapped[list[str]] = mapped_column(JSON, default=list)  # Hard constraint

    preferred_opportunity_types: Mapped[list[str]] = mapped_column(JSON, default=list)  # ["FRANCHISE", "BUSINESS_OPPORTUNITY"]
    opportunity_type_constraint: Mapped[str] = mapped_column(String(20), default="PREFERENCE", nullable=False)  # HARD | PREFERENCE

    target_region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    preferred_business_models: Mapped[list[str]] = mapped_column(JSON, default=list)
    target_customer: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # B2B | B2C | ANY
    experience_sectors: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship()
    match_runs: Mapped[list["OpportunityMatchRun"]] = relationship(
        back_populates="fit_profile", cascade="all, delete-orphan", order_by="OpportunityMatchRun.id.desc()"
    )


class OpportunityMatchRun(TimestampMixin, Base):
    """Snapshot of a deterministic matching evaluation against verified opportunities."""

    __tablename__ = "opportunity_match_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    fit_profile_id: Mapped[int] = mapped_column(
        ForeignKey("opportunity_fit_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    fit_profile_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    fit_profile_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    calculation_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    fit_profile: Mapped["OpportunityFitProfile"] = relationship(back_populates="match_runs")
    results: Mapped[list["OpportunityMatchResult"]] = relationship(
        back_populates="match_run", cascade="all, delete-orphan", order_by="OpportunityMatchResult.id.asc()"
    )


class OpportunityMatchResult(TimestampMixin, Base):
    """Immutable evaluation result of a single opportunity against a user fit profile run."""

    __tablename__ = "opportunity_match_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_run_id: Mapped[int] = mapped_column(
        ForeignKey("opportunity_match_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    opportunity_id: Mapped[int] = mapped_column(
        ForeignKey("verified_opportunities.id", ondelete="CASCADE"), index=True, nullable=False
    )
    opportunity_version: Mapped[str] = mapped_column(String(20), nullable=False)
    verification_status_at_eval: Mapped[str] = mapped_column(String(30), nullable=False)
    # MATCH | POSSIBLE_MATCH | NEEDS_INFORMATION | NOT_MATCHED | NOT_EVALUATED
    match_state: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    criteria_evaluations: Mapped[dict] = mapped_column(JSON, default=dict)
    summary_reason: Mapped[str] = mapped_column(Text, nullable=False)
    missing_information: Mapped[list[str]] = mapped_column(JSON, default=list)

    match_run: Mapped["OpportunityMatchRun"] = relationship(back_populates="results")
    opportunity: Mapped["VerifiedOpportunity"] = relationship()


# ==============================================================================
# WAVE 4 — VALIDATION OS MODELS
# ==============================================================================

class ValidationWorkspace(TimestampMixin, Base):
    """Evidence-driven validation workspace for a business project/feasibility study (Wave 4)."""

    __tablename__ = "validation_workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    study_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("feasibility_studies.id", ondelete="CASCADE"), index=True, nullable=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # NEEDS_EVIDENCE | IN_PROGRESS | PARTIALLY_VALIDATED | VALIDATED | NOT_VALIDATED
    status: Mapped[str] = mapped_column(String(30), default="NEEDS_EVIDENCE", nullable=False)

    project: Mapped["Project"] = relationship()
    study: Mapped[Optional["FeasibilityStudy"]] = relationship()
    user: Mapped["User"] = relationship()

    hypotheses: Mapped[list["ValidationHypothesis"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", order_by="ValidationHypothesis.id.asc()"
    )
    experiments: Mapped[list["ValidationExperiment"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", order_by="ValidationExperiment.id.asc()"
    )
    evidence: Mapped[list["ValidationEvidence"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", order_by="ValidationEvidence.id.desc()"
    )
    decisions: Mapped[list["ValidationDecision"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", order_by="ValidationDecision.id.desc()"
    )


class ValidationHypothesis(TimestampMixin, Base):
    """Core hypothesis tested during market validation."""

    __tablename__ = "validation_hypotheses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("validation_workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # CUSTOMER_PROBLEM | CUSTOMER_SEGMENT | VALUE_PROPOSITION | DEMAND | WILLINGNESS_TO_PAY | PRICE | CHANNEL | COMPETITOR_POSITIONING | BUSINESS_MODEL
    hypothesis_type: Mapped[str] = mapped_column(String(50), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    # CRITICAL | HIGH | MEDIUM | LOW
    importance: Mapped[str] = mapped_column(String(20), default="HIGH", nullable=False)
    # NOT_TESTED | TESTING | SUPPORTED | PARTIALLY_SUPPORTED | NOT_SUPPORTED | INCONCLUSIVE
    status: Mapped[str] = mapped_column(String(30), default="NOT_TESTED", nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    workspace: Mapped["ValidationWorkspace"] = relationship(back_populates="hypotheses")
    experiments: Mapped[list["ValidationExperiment"]] = relationship(
        back_populates="hypothesis"
    )
    evidence: Mapped[list["ValidationEvidence"]] = relationship(
        back_populates="hypothesis"
    )


class ValidationExperiment(TimestampMixin, Base):
    """Structured validation test or experiment designed to produce evidence."""

    __tablename__ = "validation_experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("validation_workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    hypothesis_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("validation_hypotheses.id", ondelete="SET NULL"), index=True, nullable=True
    )
    # CUSTOMER_INTERVIEW | SURVEY | LANDING_PAGE | WAITLIST | PRE_ORDER | QUOTE_REQUEST | SALES_OUTREACH | PRICE_TEST | COMPETITOR_RESEARCH | MANUAL_MARKET_RESEARCH | OTHER
    experiment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(Text, nullable=False)
    planned_sample_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    success_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    # PLANNED | RUNNING | COMPLETED | CANCELLED
    status: Mapped[str] = mapped_column(String(30), default="PLANNED", nullable=False)
    start_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    workspace: Mapped["ValidationWorkspace"] = relationship(back_populates="experiments")
    hypothesis: Mapped[Optional["ValidationHypothesis"]] = relationship(back_populates="experiments")
    evidence: Mapped[list["ValidationEvidence"]] = relationship(
        back_populates="experiment"
    )


class ValidationEvidence(TimestampMixin, Base):
    """Traceable, grounded empirical proof supporting or rejecting a hypothesis."""

    __tablename__ = "validation_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("validation_workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    hypothesis_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("validation_hypotheses.id", ondelete="SET NULL"), index=True, nullable=True
    )
    experiment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("validation_experiments.id", ondelete="SET NULL"), index=True, nullable=True
    )
    # USER_RECORDED | DOCUMENT | URL_SOURCE | SURVEY | INTERVIEW | TRANSACTION | PREORDER | WAITLIST | ANALYTICS | EXPERIMENT_RESULT | OFFICIAL_SOURCE
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # USER_RECORDED | DOCUMENT | URL_SOURCE | OFFICIAL_SOURCE | SYSTEM_TRACKED
    source_type: Mapped[str] = mapped_column(String(50), default="USER_RECORDED", nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_owner: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    raw_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    occurred_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # STRONG | MODERATE | WEAK
    evidence_strength: Mapped[str] = mapped_column(String(20), default="MODERATE", nullable=False)
    # SUPPORTING | REFUTING | NEUTRAL
    evidence_direction: Mapped[str] = mapped_column(String(20), default="NEUTRAL", nullable=False)
    # If simulated (e.g. AI personas/drafts), flagged true and excluded from validation proof
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Detailed factual payload (interview responses, survey samples/numerators, conversion counts, quotes)
    structured_payload: Mapped[dict] = mapped_column(JSON, default=dict)

    workspace: Mapped["ValidationWorkspace"] = relationship(back_populates="evidence")
    hypothesis: Mapped[Optional["ValidationHypothesis"]] = relationship(back_populates="evidence")
    experiment: Mapped[Optional["ValidationExperiment"]] = relationship(back_populates="evidence")


class ValidationDecision(TimestampMixin, Base):
    """Immutable record of an evidence-backed validation decision."""

    __tablename__ = "validation_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("validation_workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # GO | GO_WITH_CONDITIONS | PIVOT | STOP
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    decision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    conditions: Mapped[list[str]] = mapped_column(JSON, default=list)
    # Immutable snapshot of supported, contradicting, and missing evidence at decision time
    evidence_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    decision_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    decided_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    workspace: Mapped["ValidationWorkspace"] = relationship(back_populates="decisions")


# =============================================================================
# Wave 5: Launch & Actuals Execution OS Models
# =============================================================================

class LaunchWorkspace(TimestampMixin, Base):
    """Execution and actuals management workspace for a launched venture."""

    __tablename__ = "launch_workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(
        ForeignKey("feasibility_studies.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # PLANNED | IN_PROGRESS | BLOCKED | LAUNCHED | PAUSED | CANCELLED
    status: Mapped[str] = mapped_column(String(50), default="PLANNED", nullable=False)
    target_launch_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    actual_launch_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    milestones: Mapped[list["LaunchMilestone"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", order_by="LaunchMilestone.id"
    )
    tasks: Mapped[list["LaunchTask"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", order_by="LaunchTask.id"
    )
    baseline_snapshots: Mapped[list["LaunchBaselineSnapshot"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", order_by="LaunchBaselineSnapshot.id.desc()"
    )
    actual_periods: Mapped[list["LaunchActualPeriod"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", order_by="LaunchActualPeriod.period_order"
    )
    reforecasts: Mapped[list["LaunchReforecast"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", order_by="LaunchReforecast.version_number.desc()"
    )


class LaunchMilestone(TimestampMixin, Base):
    """Pre-launch and launch execution milestone with budget and actual tracking."""

    __tablename__ = "launch_milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("launch_workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # REGULATORY | LOCATION | EQUIPMENT | TEAM | MARKETING | OPERATIONS
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    completed_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # PENDING | IN_PROGRESS | COMPLETED | BLOCKED | DELAYED
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    # Budgets are never synthetically invented; null until explicitly set or approved
    budget_allocated: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    actual_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    owner_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dependency_milestone_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("launch_milestones.id", ondelete="SET NULL"), nullable=True
    )
    is_suggested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    workspace: Mapped["LaunchWorkspace"] = relationship(back_populates="milestones")
    tasks: Mapped[list["LaunchTask"]] = relationship(
        back_populates="milestone", cascade="all, delete-orphan", order_by="LaunchTask.id"
    )


class LaunchTask(TimestampMixin, Base):
    """Specific actionable task belonging to a launch milestone."""

    __tablename__ = "launch_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("launch_workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    milestone_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("launch_milestones.id", ondelete="CASCADE"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    due_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    completed_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # PENDING | IN_PROGRESS | COMPLETED | BLOCKED | CANCELLED
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    dependency_task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("launch_tasks.id", ondelete="SET NULL"), nullable=True
    )
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    workspace: Mapped["LaunchWorkspace"] = relationship(back_populates="tasks")
    milestone: Mapped[Optional["LaunchMilestone"]] = relationship(back_populates="tasks")


class LaunchBaselineSnapshot(TimestampMixin, Base):
    """Immutable snapshot of the feasibility study's financial projections frozen at launch."""

    __tablename__ = "launch_baseline_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("launch_workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    snapshot_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_investment: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    monthly_projections: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    frozen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    source_study_revision: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    validation_decision_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("validation_decisions.id", ondelete="SET NULL"), nullable=True
    )
    validation_decision_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_opportunity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_opportunity_version: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    funding_context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    calculation_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    workspace: Mapped["LaunchWorkspace"] = relationship(back_populates="baseline_snapshots")


class LaunchActualPeriod(TimestampMixin, Base):
    """Actual performance figures recorded for a specific operational period (e.g. Month 1, Month 2).

    Missing entries remain NULL / UNKNOWN. Zero strictly means the user entered 0.0.
    """

    __tablename__ = "launch_actual_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("launch_workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    period_label: Mapped[str] = mapped_column(String(50), nullable=False)  # "M01", "2026-M01"
    period_order: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_revenue: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    transactions_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    acquired_customers_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    average_ticket_size: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_capex: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    actual_opex_salaries: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    actual_opex_rent: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    actual_opex_utilities: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    actual_opex_marketing: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    actual_opex_cogs: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    actual_opex_other: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    total_actual_opex: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    net_cashflow: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    closing_cash_balance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # USER_ENTERED | IMPORTED | SYSTEM_INTEGRATION | DOCUMENT_BACKED
    source_type: Mapped[str] = mapped_column(String(50), default="USER_ENTERED", nullable=False)
    source_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    recorded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    workspace: Mapped["LaunchWorkspace"] = relationship(back_populates="actual_periods")


class LaunchReforecast(TimestampMixin, Base):
    """Dynamic scenario reforecast combining historical actuals with adjusted forward assumptions."""

    __tablename__ = "launch_reforecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("launch_workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    reforecast_title: Mapped[str] = mapped_column(String(255), nullable=False)
    adjustment_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    growth_rate_adjustment_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    opex_adjustment_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    monthly_burn_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    remaining_runway_months: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cash_flow_positive_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    financial_break_even_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reforecast_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    workspace: Mapped["LaunchWorkspace"] = relationship(back_populates="reforecasts")


# ==============================================================================
# WAVE 6 — GROWTH OS MODELS
# ==============================================================================

class GrowthWorkspace(TimestampMixin, Base):
    """Growth and scaling operating workspace for an operating business (Wave 6)."""

    __tablename__ = "growth_workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(
        ForeignKey("feasibility_studies.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # ACTIVE | PAUSED | PIVOTED | STOPPED
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)

    study: Mapped["FeasibilityStudy"] = relationship()
    project: Mapped["Project"] = relationship()
    user: Mapped["User"] = relationship()

    scenarios: Mapped[list["GrowthScenario"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", order_by="GrowthScenario.id.desc()"
    )
    what_if_models: Mapped[list["GrowthWhatIfModel"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", order_by="GrowthWhatIfModel.id.desc()"
    )
    monthly_reviews: Mapped[list["GrowthMonthlyReview"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", order_by="GrowthMonthlyReview.version_number.desc()"
    )
    decisions: Mapped[list["GrowthDecision"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", order_by="GrowthDecision.decision_version.desc()"
    )
    actions: Mapped[list["GrowthAction"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", order_by="GrowthAction.id.asc()"
    )


class GrowthScenario(TimestampMixin, Base):
    """Persisted growth or expansion proposal (not a predictive forecast guarantee)."""

    __tablename__ = "growth_scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("growth_workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # NEW_BRANCH | NEW_CITY | NEW_REGION | NEW_PRODUCT | NEW_SERVICE | CAPACITY_EXPANSION | HIRING | MARKETING_EXPANSION | FRANCHISE_EXPANSION | OTHER
    scenario_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    location_region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Unknown values remain NULL; never generate default or synthetic investment
    investment_required: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    capacity_assumptions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    revenue_assumptions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    cost_assumptions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    dependencies: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    risks: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    evidence_references: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # DRAFT | PROPOSED | EVALUATED | ACCEPTED | REJECTED
    status: Mapped[str] = mapped_column(String(50), default="PROPOSED", nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    workspace: Mapped["GrowthWorkspace"] = relationship(back_populates="scenarios")
    what_if_models: Mapped[list["GrowthWhatIfModel"]] = relationship(back_populates="scenario")


class GrowthWhatIfModel(TimestampMixin, Base):
    """Deterministic what-if execution record strictly separating facts from user assumptions."""

    __tablename__ = "growth_what_if_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("growth_workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scenario_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("growth_scenarios.id", ondelete="SET NULL"), index=True, nullable=True
    )
    # BASE | DOWNSIDE | UPSIDE | CUSTOM
    model_type: Mapped[str] = mapped_column(String(50), default="CUSTOM", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # Component containers explicitly labeled
    user_assumptions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # USER_ASSUMPTION
    baseline_inputs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)   # BASELINE
    actual_inputs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)     # ACTUAL
    derived_outputs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)   # PLATFORM_DERIVED
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    workspace: Mapped["GrowthWorkspace"] = relationship(back_populates="what_if_models")
    scenario: Mapped[Optional["GrowthScenario"]] = relationship(back_populates="what_if_models")


class GrowthMonthlyReview(TimestampMixin, Base):
    """Immutable monthly business review snapshot freezing operational metrics and decisions."""

    __tablename__ = "growth_monthly_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("growth_workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    review_period: Mapped[str] = mapped_column(String(50), nullable=False)  # "2026-M01", "M03"
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    actual_periods_covered: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # HEALTHY | WATCH | AT_RISK | INSUFFICIENT_DATA
    health_state: Mapped[str] = mapped_column(String(50), nullable=False)
    health_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    trend_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    unit_economics_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    risks_snapshot: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    variances_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    cash_runway_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    open_actions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    scenarios_evaluated: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    missing_information: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    workspace: Mapped["GrowthWorkspace"] = relationship(back_populates="monthly_reviews")


class GrowthDecision(TimestampMixin, Base):
    """Immutable strategic decision explicitly confirmed by the business owner."""

    __tablename__ = "growth_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("growth_workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # SCALE | FIX | PIVOT | HOLD | STOP | NEEDS_INFORMATION
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    decision_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    decision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_facts: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    contradicting_facts: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    unknowns: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    user_assumptions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    risks: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    conditions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    recommended_next_actions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # Linked Wave 4 validation workspace for PIVOT decisions
    pivot_validation_workspace_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("validation_workspaces.id", ondelete="SET NULL"), nullable=True
    )
    # Linked Wave 6 growth scenario for SCALE decisions
    growth_scenario_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("growth_scenarios.id", ondelete="SET NULL"), nullable=True
    )
    re_evaluation_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    decided_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    workspace: Mapped["GrowthWorkspace"] = relationship(back_populates="decisions")
    pivot_validation_workspace: Mapped[Optional["ValidationWorkspace"]] = relationship()
    growth_scenario: Mapped[Optional["GrowthScenario"]] = relationship()
    actions: Mapped[list["GrowthAction"]] = relationship(back_populates="decision")


class GrowthAction(TimestampMixin, Base):
    """Actionable remediation or expansion implementation task."""

    __tablename__ = "growth_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("growth_workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    decision_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("growth_decisions.id", ondelete="SET NULL"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # REMEDIATION | EXPANSION_STEP | INFORMATION_GATHERING
    action_type: Mapped[str] = mapped_column(String(50), default="REMEDIATION", nullable=False)
    # OPERATIONS | FINANCIAL | MARKETING | GOVERNANCE
    category: Mapped[str] = mapped_column(String(50), default="OPERATIONS", nullable=False)
    owner_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    due_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(50), default="MEDIUM", nullable=True)
    # PENDING | IN_PROGRESS | COMPLETED | CANCELLED
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    workspace: Mapped["GrowthWorkspace"] = relationship(back_populates="actions")
    decision: Mapped[Optional["GrowthDecision"]] = relationship(back_populates="actions")







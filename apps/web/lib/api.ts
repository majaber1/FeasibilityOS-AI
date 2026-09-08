// Defaults to a same-origin path proxied to the backend by the secure
// cookie-authenticated route handler at
// app/api/backend/[...path]/route.ts -- this avoids needing any CORS
// configuration on the backend (see backend/app/core/config.py: production
// denies cross-origin requests by default unless CORS_ORIGINS is
// explicitly set, which this deployment does not require). Override with
// an absolute URL via NEXT_PUBLIC_API_BASE_URL if you point this frontend
// at a different backend.
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "/api/backend";

export type ApiError = {
  detail?: string | Array<{ msg?: string; loc?: Array<string | number> }>;
  message?: string;
};

function apiErrorMessage(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") return fallback;
  const error = data as ApiError;
  if (typeof error.detail === "string") return error.detail;
  if (Array.isArray(error.detail)) {
    const messages = error.detail
      .map((item) => {
        if (!item || typeof item !== "object") return null;
        const field = Array.isArray(item.loc) ? item.loc.at(-1) : null;
        return item.msg ? `${field ? `${String(field)}: ` : ""}${item.msg}` : null;
      })
      .filter((item): item is string => Boolean(item));
    if (messages.length) return messages.join("، ");
  }
  if (typeof error.message === "string") return error.message;
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API_BASE + path, {
    ...init,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : {};
  if (!res.ok) {
    const message = apiErrorMessage(data, res.statusText || "Request failed");
    throw new Error(message);
  }
  return data as T;
}

function authedRequest<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  return request<T>(path, {
    ...init,
    headers: { Authorization: "Bearer " + token, ...(init?.headers ?? {}) },
  });
}

export type TokenResponse = { access_token: string; token_type: string };
export type UserProfile = {
  id: number;
  email: string;
  full_name?: string | null;
  role_key: string;
  locale: string;
  email_verified: boolean;
};

const TOKEN_KEY = "sb_token";

export function saveToken(token: string) {
  if (typeof window !== "undefined") {
    // Store only a non-secret UI hint. The real credential is an HTTP-only
    // SameSite cookie issued by /api/session/login and cannot be read by JS.
    localStorage.setItem(TOKEN_KEY, token === "session" ? "session" : token);
    window.dispatchEvent(new Event("sb-auth-change"));
  }
}
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}
export function clearToken() {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
    void fetch("/api/session/logout", { method: "POST", credentials: "same-origin" });
    window.dispatchEvent(new Event("sb-auth-change"));
  }
}

export function login(email: string, password: string) {
  return fetch("/api/session/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ email, password }),
  }).then(async (res) => {
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(apiErrorMessage(data, res.statusText || "Sign in failed"));
    return data as TokenResponse;
  });
}

export function register(payload: {
  email: string;
  password: string;
  full_name?: string;
  role_key?: string;
  locale?: string;
}) {
  return request<UserProfile>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function me(token: string) {
  return request<UserProfile>("/auth/me", {
    headers: { Authorization: "Bearer " + token },
  });
}

// --- Projects ---------------------------------------------------------------

export type Project = {
  id: number;
  owner_id: number | null;
  name: string;
  industry: string;
  investment: number;
  stage: string;
  created_at: string;
  workflow_status: string;
  is_archived: boolean;
  persisted: boolean;
};

export function listProjects(token: string, includeArchived = false) {
  return authedRequest<Project[]>("/projects/" + (includeArchived ? "?include_archived=true" : ""), token);
}

export function getProject(token: string, projectId: number) {
  return authedRequest<Project>(`/projects/${projectId}`, token);
}

export function createProject(token: string, payload: { name: string; industry: string; investment: number; stage?: string }) {
  return authedRequest<Project>("/projects/", token, { method: "POST", body: JSON.stringify(payload) });
}

export function updateProject(token: string, projectId: number, payload: Partial<Pick<Project, "name" | "industry" | "investment" | "stage">>) {
  return authedRequest<Project>(`/projects/${projectId}`, token, { method: "PATCH", body: JSON.stringify(payload) });
}

export function setProjectArchived(token: string, projectId: number, archived: boolean) {
  return authedRequest<Project>(`/projects/${projectId}/${archived ? "archive" : "unarchive"}`, token, { method: "POST" });
}

// --- Feasibility studies ------------------------------------------------------

export type FinancialResultOut = {
  roi_percent: number | null;
  payback_years: number | null;
  npv: number | null;
  irr_percent: number | null;
  break_even?: number | null;
  verdict: string;
  sensitivity: Array<{
    revenue_change_percent: number;
    npv: number | null;
    irr_percent: number | null;
    verdict: string;
  }>;
};

export type Study = {
  id: number;
  project_id: number;
  title: string;
  study_type: string;
  status: string;
  current_step: number;
  revision: number;
  payload: Record<string, unknown>;
  result: FinancialResultOut | null;
};

export type StudySaveState = "idle" | "saving" | "saved" | "error";

export function listStudies(token: string, projectId?: number) {
  const qs = projectId ? "?project_id=" + projectId : "";
  return authedRequest<Study[]>("/feasibility/" + qs, token);
}

export function getStudy(token: string, studyId: number) {
  return authedRequest<Study>("/feasibility/" + studyId, token);
}

export function createStudy(
  token: string,
  payload: { title: string; industry: string; investment: number; study_type?: string; project_id?: number },
) {
  return authedRequest<Study>("/feasibility/", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function saveStudyStep(token: string, studyId: number, step: number, data: Record<string, unknown>, expectedRevision?: number) {
  return authedRequest<Study>("/feasibility/" + studyId + "/step", token, {
    method: "PATCH",
    body: JSON.stringify({ step, data, expected_revision: expectedRevision }),
  });
}

export function computeStudy(
  token: string,
  studyId: number,
  payload: { annual_cash_flows: number[]; discount_rate?: number },
) {
  return authedRequest<Study>("/feasibility/" + studyId + "/compute", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function computeStudyFromAssumptions(token: string, studyId: number) {
  return authedRequest<Study>(`/feasibility/${studyId}/compute-from-assumptions`, token, { method: "POST" });
}

export function reportDownloadUrl(studyId: number, fmt: "pdf" | "docx", locale: "ar" | "en") {
  return API_BASE + "/reports/study/" + studyId + "?fmt=" + fmt + "&locale=" + locale;
}

// --- Quick idea check (Entry 1: "لدي فكرة مشروع") -----------------------------

export type QuickIdeaCheckStatus = "PROMISING" | "NEEDS_VALIDATION" | "INSUFFICIENT_DATA" | "HIGH_UNCERTAINTY";

export type QuickIdeaCheckPayload = {
  idea_text: string;
  estimated_capital: number;
  city?: string;
  region?: string;
  customer_segment?: string;
  goal?: string;
  is_existing_business?: boolean;
  project_id?: number;
};

export type QuickIdeaCheckResult = {
  project_id: number;
  study_id: number;
  status: QuickIdeaCheckStatus;
  industry_guess: string | null;
  regulatory_complexity_hint: string;
  known_fields: string[];
  missing_fields: string[];
  evidence_coverage: number;
  assumption_coverage: number;
  main_uncertainties: string[];
  recommended_next_step: string;
};

export function submitQuickIdeaCheck(token: string, payload: QuickIdeaCheckPayload) {
  return authedRequest<QuickIdeaCheckResult>("/quick-idea-check/", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// --- Business profile (structured, reusable business facts) -----------------

export type BusinessProfile = {
  study_id: number;
  business_activity: string | null;
  description: string | null;
  city: string | null;
  region: string | null;
  customer_segment: string | null;
  capacity_value: number | null;
  capacity_unit: string | null;
  legal_entity_type: string | null;
  ownership_notes: string | null;
  is_existing_business: boolean;
  company_age_years: number | null;
  current_revenue: number | null;
};

export type BusinessProfileUpdate = Partial<Omit<BusinessProfile, "study_id">>;

export async function getBusinessProfile(token: string, studyId: number): Promise<BusinessProfile | null> {
  const res = await fetch(`${API_BASE}/studies/${studyId}/business-profile/`, {
    credentials: "same-origin",
    headers: { Authorization: "Bearer " + token },
  });
  if (res.status === 404) return null;
  const data = await res.json();
  if (!res.ok) throw new Error(apiErrorMessage(data, res.statusText || "Request failed"));
  return data as BusinessProfile;
}

export function saveBusinessProfile(token: string, studyId: number, payload: BusinessProfileUpdate) {
  return authedRequest<BusinessProfile>(`/studies/${studyId}/business-profile/`, token, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

// --- Company financial profile (Wave 2: existing-business period statements) --

export const FINANCIAL_PERIOD_SOURCES = [
  "financial_statement", "bank_statement", "user_confirmed",
  "audited_statement", "management_account", "unverified",
] as const;
export type FinancialPeriodSource = (typeof FINANCIAL_PERIOD_SOURCES)[number];

export type CompanyFinancialPeriod = {
  id: number;
  study_id: number;
  period: string;
  source: FinancialPeriodSource;
  document_id: number | null;
  revenue: number | null;
  gross_profit: number | null;
  ebitda: number | null;
  operating_profit: number | null;
  net_profit: number | null;
  cash: number | null;
  current_assets: number | null;
  current_liabilities: number | null;
  total_assets: number | null;
  total_liabilities: number | null;
  equity: number | null;
  existing_debt: number | null;
  annual_debt_service: number | null;
  accounts_receivable: number | null;
  inventory: number | null;
  capital_expenditure: number | null;
  interest_expense: number | null;
};

export type FinancialPeriodUpdate = Partial<Omit<CompanyFinancialPeriod, "id" | "study_id" | "period" | "document_id">>;

export function listFinancialPeriods(token: string, studyId: number) {
  return authedRequest<CompanyFinancialPeriod[]>(`/studies/${studyId}/financial-periods/`, token);
}

export function saveFinancialPeriod(token: string, studyId: number, period: string, payload: FinancialPeriodUpdate) {
  return authedRequest<CompanyFinancialPeriod>(`/studies/${studyId}/financial-periods/${encodeURIComponent(period)}`, token, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

// --- Financial health (Wave 2) -------------------------------------------------

export type MetricStatus = "CALCULATED" | "MISSING_DATA" | "NOT_APPLICABLE";

export type HealthMetric = { status: MetricStatus; value: number | null; unit: string | null };

export type FinancialHealth = {
  study_id: number;
  period: string;
  prior_period: string | null;
  metrics: Record<string, HealthMetric>;
  summary: Record<string, string>;
};

export async function getFinancialHealth(token: string, studyId: number): Promise<FinancialHealth | null> {
  const res = await fetch(`${API_BASE}/studies/${studyId}/financial-health/`, {
    credentials: "same-origin",
    headers: { Authorization: "Bearer " + token },
  });
  if (res.status === 404) return null;
  const data = await res.json();
  if (!res.ok) throw new Error(apiErrorMessage(data, res.statusText || "Request failed"));
  return data as FinancialHealth;
}

// --- Funding gap (Wave 2) -------------------------------------------------------

export type FundingGap = {
  study_id: number;
  total_project_requirement: number;
  requirement_source: string;
  owner_available_capital: number;
  owner_available_capital_status: MetricStatus;
  existing_available_facilities: number;
  existing_available_facilities_status: MetricStatus;
  funding_gap: number;
  missing_inputs: string[];
};

export function getFundingGap(token: string, studyId: number) {
  return authedRequest<FundingGap>(`/studies/${studyId}/funding-gap/`, token);
}

// --- Borrowing capacity (Wave 2) -------------------------------------------------

export type BorrowingCapacity = {
  study_id: number;
  period: string;
  status: "CALCULATED" | "INSUFFICIENT_DATA";
  base_capacity: number | null;
  stress_capacity: number | null;
  primary_constraint: string | null;
  secondary_constraint: string | null;
  financial_support: string;
  missing_inputs: string[];
  missing_underwriting_inputs: string[];
  assumptions_used: Record<string, number>;
  disclaimer: string;
};

export async function getBorrowingCapacity(token: string, studyId: number): Promise<BorrowingCapacity | null> {
  const res = await fetch(`${API_BASE}/studies/${studyId}/borrowing-capacity/`, {
    credentials: "same-origin",
    headers: { Authorization: "Bearer " + token },
  });
  if (res.status === 404) return null;
  const data = await res.json();
  if (!res.ok) throw new Error(apiErrorMessage(data, res.statusText || "Request failed"));
  return data as BorrowingCapacity;
}

// --- Collateral (Wave 2) ---------------------------------------------------------

export const COLLATERAL_TYPES = ["PROPERTY", "EQUIPMENT", "CASH", "RECEIVABLES", "GUARANTEE", "OTHER"] as const;
export type CollateralType = (typeof COLLATERAL_TYPES)[number];

export const COLLATERAL_VERIFICATION_STATUSES = ["UNVERIFIED", "USER_REPORTED", "DOCUMENT_SUPPORTED", "VERIFIED"] as const;
export type CollateralVerificationStatus = (typeof COLLATERAL_VERIFICATION_STATUSES)[number];

export const ENCUMBRANCE_STATUSES = ["UNENCUMBERED", "PARTIALLY_ENCUMBERED", "FULLY_ENCUMBERED", "UNKNOWN"] as const;
export type EncumbranceStatus = (typeof ENCUMBRANCE_STATUSES)[number];

export type CollateralItem = {
  id: number;
  study_id: number;
  collateral_type: CollateralType;
  description: string;
  reported_value: number;
  verified_value: number | null;
  currency: string;
  valuation_date: string | null;
  valuation_source: string | null;
  ownership_status: string | null;
  encumbrance_status: EncumbranceStatus;
  encumbrance_amount: number | null;
  lien_holder: string | null;
  verification_status: CollateralVerificationStatus;
  notes: string | null;
};

export type CollateralCreatePayload = {
  collateral_type: CollateralType;
  description: string;
  reported_value: number;
  verified_value?: number;
  currency?: string;
  valuation_date?: string;
  valuation_source?: string;
  ownership_status?: string;
  encumbrance_status?: EncumbranceStatus;
  encumbrance_amount?: number;
  lien_holder?: string;
  verification_status?: CollateralVerificationStatus;
  notes?: string;
};

export type CollateralUpdatePayload = Partial<CollateralCreatePayload>;

export type CollateralSummary = {
  record_count: number;
  total_reported_value: number;
  total_verified_value: number;
  total_encumbered_value: number;
  total_unencumbered_reported_value: number;
  verified_record_count: number;
  unverified_record_count: number;
  unknown_encumbrance_count: number;
};

export function listCollateral(token: string, studyId: number) {
  return authedRequest<CollateralItem[]>(`/studies/${studyId}/collateral/`, token);
}

export function getCollateralSummary(token: string, studyId: number) {
  return authedRequest<CollateralSummary>(`/studies/${studyId}/collateral/summary`, token);
}

export function createCollateral(token: string, studyId: number, payload: CollateralCreatePayload) {
  return authedRequest<CollateralItem>(`/studies/${studyId}/collateral/`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateCollateral(token: string, studyId: number, collateralId: number, payload: CollateralUpdatePayload) {
  return authedRequest<CollateralItem>(`/studies/${studyId}/collateral/${collateralId}`, token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteCollateral(token: string, studyId: number, collateralId: number) {
  return authedRequest<void>(`/studies/${studyId}/collateral/${collateralId}`, token, { method: "DELETE" });
}

// --- Funding Readiness (Wave 2) --------------------------------------------------

export const READINESS_STATUSES = ["READY", "PARTIALLY_READY", "NEEDS_INFORMATION", "NOT_READY"] as const;
export type ReadinessStatus = (typeof READINESS_STATUSES)[number];

export type ActionableStep = {
  key: string;
  title_en: string;
  title_ar: string;
  action_target: string;
};

export type FundingReadiness = {
  study_id: number;
  status: ReadinessStatus;
  summary_en: string;
  summary_ar: string;
  positive_factors: string[];
  positive_factors_ar: string[];
  blocking_factors: string[];
  blocking_factors_ar: string[];
  missing_information: string[];
  missing_information_ar: string[];
  warnings: string[];
  warnings_ar: string[];
  actionable_steps: ActionableStep[];
  financial_health_snapshot: Record<string, unknown> | null;
  funding_gap_snapshot: Record<string, unknown> | null;
  borrowing_capacity_snapshot: Record<string, unknown> | null;
  collateral_snapshot: Record<string, unknown> | null;
  documents_status: string;
  internal_screening_assumptions?: Record<string, unknown>;
  assumptions_used: Record<string, unknown>;
  calculation_version: string;
};

export function getFundingReadiness(token: string, studyId: number, period?: string) {
  const query = period ? `?period=${encodeURIComponent(period)}` : "";
  return authedRequest<FundingReadiness>(`/studies/${studyId}/funding-readiness/${query}`, token);
}

// --- Verified Funding Programs Registry (Phase 18) --------------------------

export type FundingProgramRule = {
  id: number;
  program_id: number;
  rule_key: string;
  rule_type: string;
  structured_value: Record<string, unknown>;
  description_ar?: string | null;
  description_en?: string | null;
  source_url: string;
  source_reference?: string | null;
  source_authority: string;
  verified_at: string;
  rule_version: string;
  is_active: boolean;
};

export type FundingProgram = {
  id: number;
  slug: string;
  provider: string;
  provider_ar: string;
  program_name_ar: string;
  program_name_en: string;
  description_ar?: string | null;
  description_en?: string | null;
  program_type: string;
  target_business_stage: string;
  target_sectors: string[];
  financing_min?: number | null;
  financing_max?: number | null;
  currency: string;
  term_months?: number | null;
  grace_period_months?: number | null;
  owner_contribution_rule?: Record<string, unknown> | null;
  collateral_rule?: Record<string, unknown> | null;
  guarantee_rule?: Record<string, unknown> | null;
  revenue_rule?: Record<string, unknown> | null;
  business_age_rule?: Record<string, unknown> | null;
  other_eligibility_rules?: unknown[] | null;
  official_source_url: string;
  source_type: string;
  source_owner: string;
  first_seen_at: string;
  last_checked_at: string;
  last_verified_at: string;
  effective_from?: string | null;
  effective_to?: string | null;
  verification_status: string;
  rule_version: string;
  rules: FundingProgramRule[];
};

export type RegistrySummary = {
  total_programs: number;
  verified_current_count: number;
  providers_breakdown: Record<string, number>;
  program_types_breakdown: Record<string, number>;
  all_providers: string[];
};

export function listFundingPrograms(
  token?: string,
  filters?: {
    provider?: string;
    program_type?: string;
    verification_status?: string;
    target_business_stage?: string;
    sector?: string;
  }
) {
  const params = new URLSearchParams();
  if (filters?.provider) params.append("provider", filters.provider);
  if (filters?.program_type) params.append("program_type", filters.program_type);
  if (filters?.verification_status) params.append("verification_status", filters.verification_status);
  if (filters?.target_business_stage) params.append("target_business_stage", filters.target_business_stage);
  if (filters?.sector) params.append("sector", filters.sector);
  const q = params.toString() ? `?${params.toString()}` : "";

  if (token) {
    return authedRequest<FundingProgram[]>(`/funding-programs/${q}`, token);
  }
  return request<FundingProgram[]>(`/funding-programs/${q}`);
}

export function getFundingProgram(programId: number, token?: string) {
  if (token) {
    return authedRequest<FundingProgram>(`/funding-programs/${programId}`, token);
  }
  return request<FundingProgram>(`/funding-programs/${programId}`);
}

export function getFundingProgramsSummary(token?: string) {
  if (token) {
    return authedRequest<RegistrySummary>("/funding-programs/summary", token);
  }
  return request<RegistrySummary>("/funding-programs/summary");
}

// --- Funding Matching (Phase 19) -------------------------------------------

export type FundingRuleEvaluation = {
  rule_key: string;
  rule_name_ar: string;
  rule_name_en: string;
  rule_type: string;
  required_value: unknown;
  actual_value: unknown;
  result: "PASS" | "FAIL" | "UNKNOWN";
  notes_ar: string;
  notes_en: string;
  source_url: string;
  source_authority: string;
  rule_version: string;
};

export type FundingProgramMatchResult = {
  program_id: number;
  program_slug: string;
  provider: string;
  provider_ar: string;
  program_name_ar: string;
  program_name_en: string;
  program_type: string;
  target_business_stage: string;
  financing_min?: number | null;
  financing_max?: number | null;
  term_months?: number | null;
  grace_period_months?: number | null;
  official_source_url: string;
  source_owner: string;
  rule_version: string;
  last_verified_at?: string | null;
  overall_match_status: "MATCH" | "POSSIBLE_MATCH" | "NEEDS_INFORMATION" | "NOT_MATCHED";
  status_reason_ar: string;
  status_reason_en: string;
  passed_rules: string[];
  failed_rules: string[];
  unknown_rules: string[];
  missing_information: string[];
  rule_evaluations: FundingRuleEvaluation[];
};

export type FundingMatchesSummary = {
  study_id: number;
  study_profile_snapshot: {
    project_name: string;
    sector: string;
    stage: string;
    total_project_requirement: number;
    owner_contribution: number;
    funding_gap: number;
    available_collateral: number;
    collateral_coverage_ratio: number;
    annual_revenue?: number | null;
    safe_debt_capacity: number;
    financial_health_score?: string | null;
  };
  total_programs_evaluated: number;
  matches_count: number;
  possible_matches_count: number;
  needs_information_count: number;
  not_matched_count: number;
  matches: FundingProgramMatchResult[];
  disclaimer_ar: string;
  disclaimer_en: string;
  calculation_version: string;
};

export function getFundingMatches(token: string, studyId: number, period?: string) {
  const query = period ? `?period=${encodeURIComponent(period)}` : "";
  return authedRequest<FundingMatchesSummary>(`/studies/${studyId}/funding-matches/${query}`, token);
}

export function getFundingProgramMatch(token: string, studyId: number, programId: number) {
  return authedRequest<FundingProgramMatchResult>(`/studies/${studyId}/funding-matches/${programId}`, token);
}

// --- Financing Structure (Phase 20: Capstone) -------------------------------

export type FinancingSourceItem = {
  source_key: string;
  name_ar: string;
  name_en: string;
  source_type: "EQUITY" | "EXISTING_DEBT" | "PROGRAM_DEBT" | "UNFUNDED";
  amount: number;
  percentage: number;
  is_secured: boolean;
  program_slug?: string | null;
  official_source_url?: string | null;
};

export type FinancingUseItem = {
  category_key: string;
  name_ar: string;
  name_en: string;
  amount: number;
  percentage: number;
};

export type FinancingProgramAllocation = {
  program_id: number;
  program_slug: string;
  provider: string;
  provider_ar: string;
  program_name_ar: string;
  program_name_en: string;
  program_type: string;
  match_status: string;
  allocated_amount?: number | null;
  allocation_status?: string | null;
  term_months?: number | null;
  grace_period_months?: number | null;
  official_source_url?: string | null;
};

export type CreditEnhancementItem = {
  program_id: number;
  program_slug: string;
  provider: string;
  provider_ar: string;
  program_name_ar: string;
  program_name_en: string;
  program_type: string;
  match_status: string;
  cash_contribution: number;
  role_ar: string;
  role_en: string;
  max_guarantee_amount?: number | null;
  coverage_ratio?: number | null;
  official_source_url?: string | null;
};

export type ConfirmedSourcesData = {
  owner_equity: number;
  existing_debt: number;
  total_confirmed: number;
  coverage_percentage: number;
};

export type FinancingWarning = {
  code: string;
  severity: "CRITICAL" | "WARNING" | "ADVISORY";
  title_ar: string;
  title_en: string;
  message_ar: string;
  message_en: string;
};

export type FinancingNextAction = {
  step_number: number;
  title_ar: string;
  title_en: string;
  status: "READY" | "ACTION_REQUIRED" | "PENDING_VALUATION" | "MATCHED_PROGRAM" | "POTENTIAL_SOURCE" | "NO_MATCH" | string;
  description_ar: string;
  description_en: string;
};

export type FinancingStructure = {
  study_id: number;
  project_name: string;
  sector: string;
  stage: string;
  total_project_requirement: number;
  owner_equity: number;
  existing_debt: number;
  total_confirmed_sources?: number;
  confirmed_sources?: ConfirmedSourcesData;
  initial_funding_gap?: number;
  confirmed_funding_gap?: number;
  potential_residual_gap?: number;
  potential_program_capacity?: number;
  allocated_program_debt: number;
  internal_screening_debt_capacity?: number;
  safe_debt_capacity: number;
  capacity_status: string;
  total_identified_sources: number;
  residual_gap: number;
  surplus: number;
  equity_percentage: number;
  debt_percentage: number;
  debt_to_equity_ratio?: number | null;
  collateral_coverage_ratio: number;
  sources: FinancingSourceItem[];
  uses: FinancingUseItem[];
  program_allocations: FinancingProgramAllocation[];
  credit_enhancements?: CreditEnhancementItem[];
  warnings: FinancingWarning[];
  next_actions: FinancingNextAction[];
  disclaimer_ar: string;
  disclaimer_en: string;
  version: string;
};

export function getFinancingStructure(token: string, studyId: number, period?: string) {
  const query = period ? `?period=${encodeURIComponent(period)}` : "";
  return authedRequest<FinancingStructure>(`/studies/${studyId}/financing-structure/${query}`, token);
}

// --- Evidence (study provenance layer) ---------------------------------------

export const SOURCE_TYPES = [
  "official_statistic",
  "regulation",
  "funding_program",
  "market_report",
  "news",
  "survey",
  "user_document",
  "ai_inference",
  "other",
] as const;
export type SourceType = (typeof SOURCE_TYPES)[number];

export const VERIFICATION_STATUSES = ["verified", "user_provided", "unverified"] as const;
export type VerificationStatus = (typeof VERIFICATION_STATUSES)[number];

export const CONFIDENCE_LEVELS = ["low", "medium", "high"] as const;
export type ConfidenceLevel = (typeof CONFIDENCE_LEVELS)[number];

export type AuthorityLevel =
  | "OFFICIAL_PRIMARY"
  | "OFFICIAL_SECONDARY"
  | "REGULATOR"
  | "REPUTABLE_INSTITUTION"
  | "COMMERCIAL_SOURCE"
  | "USER_DOCUMENT"
  | "AI_INFERENCE"
  | "UNVERIFIED";

export type EvidenceItem = {
  id: number;
  study_id: number;
  source_type: SourceType;
  source_name: string | null;
  source_url: string | null;
  publisher: string | null;
  title: string;
  claim: string;
  value_number: number | null;
  value_text: string | null;
  unit: string | null;
  geography: string | null;
  sector: string | null;
  published_at: string | null;
  retrieved_at: string;
  effective_from: string | null;
  effective_to: string | null;
  superseded_by_id: number | null;
  confidence: ConfidenceLevel;
  verification_status: VerificationStatus;
  authority_level: AuthorityLevel;
  snapshot_text: string | null;
  created_at: string;
  updated_at: string;
};

export type EvidenceCreatePayload = {
  source_type: SourceType;
  title: string;
  claim: string;
  source_name?: string;
  source_url?: string;
  publisher?: string;
  value_number?: number;
  value_text?: string;
  unit?: string;
  geography?: string;
  sector?: string;
  confidence?: ConfidenceLevel;
  verification_status?: VerificationStatus;
};

export function listEvidence(token: string, studyId: number) {
  return authedRequest<EvidenceItem[]>(`/studies/${studyId}/evidence`, token);
}

export function createEvidence(token: string, studyId: number, payload: EvidenceCreatePayload) {
  return authedRequest<EvidenceItem>(`/studies/${studyId}/evidence`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteEvidence(token: string, studyId: number, evidenceId: number) {
  return authedRequest<void>(`/studies/${studyId}/evidence/${evidenceId}`, token, { method: "DELETE" });
}

export type SourceRegistryEntry = {
  key: string;
  name_en: string;
  name_ar: string;
  domain: string;
  authority_level: AuthorityLevel;
};

export function getSourceRegistry(token: string) {
  return authedRequest<{ authority_levels: AuthorityLevel[]; sources: SourceRegistryEntry[] }>(
    "/sources/registry",
    token,
  );
}

// --- Study assumptions (versioned, provenance-tagged) -------------------------

export const ASSUMPTION_ORIGINS = ["USER", "EVIDENCE_DERIVED", "AI_SUGGESTED", "DEFAULT"] as const;
export type AssumptionOrigin = (typeof ASSUMPTION_ORIGINS)[number];

export type StudyAssumption = {
  id: number;
  study_id: number;
  key: string;
  label_en: string;
  label_ar: string;
  value_number: number | null;
  value_text: string | null;
  unit: string | null;
  origin: AssumptionOrigin;
  reason: string | null;
  confidence: ConfidenceLevel;
  evidence_id: number | null;
  version: number;
  is_active: boolean;
};

export type AssumptionCreatePayload = {
  key: string;
  label_en: string;
  label_ar: string;
  origin: AssumptionOrigin;
  value_number?: number;
  value_text?: string;
  unit?: string;
  reason?: string;
  confidence?: ConfidenceLevel;
  evidence_id?: number;
};

export function listAssumptions(token: string, studyId: number, includeInactive = false) {
  return authedRequest<StudyAssumption[]>(
    `/studies/${studyId}/assumptions/${includeInactive ? "?include_inactive=true" : ""}`,
    token,
  );
}

export function createAssumption(token: string, studyId: number, payload: AssumptionCreatePayload) {
  return authedRequest<StudyAssumption>(`/studies/${studyId}/assumptions/`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function retireAssumption(token: string, studyId: number, assumptionId: number) {
  return authedRequest<StudyAssumption>(`/studies/${studyId}/assumptions/${assumptionId}`, token, {
    method: "DELETE",
  });
}

// --- Financial & funding engines (public, unauthenticated) ------------------

export type FeasibilityEvalResponse = {
  roi_percent: number | null;
  payback_years: number | null;
  npv: number | null;
  irr_percent: number | null;
  verdict: string;
};

export type FinancialAnalysisRecord = {
  id: number;
  owner_id: number;
  project_id: number | null;
  feasibility_study_id: number | null;
  title: string;
  investment: number;
  annual_cash_flows: number[];
  discount_rate: number;
  result: FeasibilityEvalResponse;
  import_meta: Record<string, unknown>;
};

export type ImportPreview = {
  study_id: number;
  project_id: number;
  project_name?: string | null;
  investment?: number | null;
  annual_cash_flows: number[];
  discount_rate: number;
  imported_fields: string[];
  source_record: string;
  last_sync?: string | null;
  study_title?: string;
  industry?: string | null;
  verdict?: string | null;
};

export function evaluateFinancial(payload: {
  investment: number;
  annual_cash_flows: number[];
  discount_rate?: number;
}) {
  return request<FeasibilityEvalResponse>("/financial/evaluate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function evaluateSensitivity(payload: {
  investment: number;
  annual_cash_flows: number[];
  discount_rate?: number;
}) {
  return request<unknown>("/financial/sensitivity", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listFinancialAnalyses(token: string, projectId?: number) {
  const qs = projectId ? `?project_id=${projectId}` : "";
  return authedRequest<FinancialAnalysisRecord[]>(`/financial/analyses${qs}`, token);
}

export function createFinancialAnalysis(token: string, payload: {
  title?: string;
  investment: number;
  annual_cash_flows: number[];
  discount_rate?: number;
  project_id?: number;
  feasibility_study_id?: number;
  import_meta?: Record<string, unknown>;
}) {
  return authedRequest<FinancialAnalysisRecord>("/financial/analyses", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getFinancialImportPreview(token: string, studyId: number) {
  return authedRequest<ImportPreview>(`/financial/from-study/${studyId}`, token);
}

export function getProposalImportPreview(token: string, studyId: number) {
  return authedRequest<ImportPreview>(`/proposals/from-study/${studyId}`, token);
}

export async function downloadInvestorPackage(token: string, payload: {
  study_id?: number;
  proposal_id?: number;
  project_id?: number;
  locale: "ar" | "en";
}) {
  const res = await fetch(API_BASE + "/reports/investor-package", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(apiErrorMessage(data, res.statusText));
  }
  const url = URL.createObjectURL(await res.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `investor_package_${payload.locale}.pdf`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function listNotifications(token: string) {
  return authedRequest<AppNotification[]>("/notifications/", token);
}

export function markNotificationRead(token: string, id: number) {
  return authedRequest<AppNotification>(`/notifications/${id}/read`, token, { method: "POST" });
}

export function trackAnalytics(token: string, payload: {
  event_type: "tool_opened" | "workflow_started" | "workflow_completed" | "report_generated" | "service_linked";
  service_key?: string;
  entity?: string;
  entity_id?: number;
}) {
  return authedRequest<{ accepted: boolean }>("/analytics/events", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export type AppNotification = {
  id: number;
  kind: string;
  title_en: string;
  title_ar: string;
  body?: string | null;
  entity?: string | null;
  entity_id?: number | null;
  is_read: boolean;
};

export type FundingMatch = {
  program: string;
  name: string;
  score_percent: number;
  reasons: string[];
  missing: string[];
  name_ar: string;
  source_url: string;
  eligibility_sample_ar: string[];
  provider_role_ar: string;
  verified_at: string;
};

export function matchFunding(payload: {
  industry: string;
  stage?: string;
  has_mvp?: boolean;
  has_technical_team?: boolean;
}) {
  return request<FundingMatch[]>("/funding/match", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export type FundingDocument = { id: number; project_id: number | null; name: string; content_type?: string | null; size_bytes?: number | null; created_at: string };

export async function uploadFundingDocument(token: string, projectId: number, file: File) {
  const form = new FormData(); form.append("project_id", String(projectId)); form.append("file", file);
  const res = await fetch(API_BASE + "/documents/", { method: "POST", headers: { Authorization: "Bearer " + token }, body: form });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(apiErrorMessage(data, res.statusText || "Upload failed"));
  return data as FundingDocument;
}

export function listFundingDocuments(token: string, projectId: number) {
  return authedRequest<FundingDocument[]>(`/documents/?project_id=${projectId}`, token);
}

export async function downloadProtectedFile(path: string, token: string, filename: string) {
  const res = await fetch(API_BASE + path, { headers: { Authorization: "Bearer " + token } });
  if (!res.ok) throw new Error(apiErrorMessage(await res.json().catch(() => ({})), res.statusText));
  const url = URL.createObjectURL(await res.blob()); const link = document.createElement("a"); link.href = url; link.download = filename; link.click(); setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

export function exportProposal(token: string, proposalId: number, fmt: "pdf" | "docx", locale: "ar" | "en") {
  return downloadProtectedFile(`/proposals/${proposalId}/export?fmt=${fmt}&locale=${locale}`, token, `proposal_${proposalId}_${locale}.${fmt}`);
}

// --- Investment opportunities (public, unauthenticated) ---------------------

export type Opportunity = {
  id: number;
  title_en: string;
  title_ar: string;
  industry: string;
  summary_en?: string | null;
  summary_ar?: string | null;
  stage: string;
  risk_level: string;
  investment_min: number | null;
  investment_max: number | null;
  expected_return_percent: number | null;
  funding_goal: number | null;
  funding_committed: number;
  source_url?: string | null;
  verification_status: string;
  is_active: boolean;
};

export function listOpportunities(filters?: { industry?: string; risk_level?: string; max_amount?: number }) {
  const params = new URLSearchParams();
  if (filters?.industry) params.set("industry", filters.industry);
  if (filters?.risk_level) params.set("risk_level", filters.risk_level);
  if (filters?.max_amount !== undefined) params.set("max_amount", String(filters.max_amount));
  const qs = params.toString();
  return request<Opportunity[]>("/opportunities/" + (qs ? "?" + qs : ""));
}

// --- Sales lead capture (public, unauthenticated; not a payment endpoint) ---

export type LeadPayload = {
  full_name: string;
  email: string;
  company?: string;
  phone?: string;
  plan?: string;
  intent?: string;
  message?: string;
};

export function submitLead(payload: LeadPayload) {
  return request<{ received: boolean; persisted: boolean }>("/leads/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateProfile(token: string, payload: { full_name?: string | null; locale?: "ar" | "en" }) {
  return authedRequest<UserProfile>("/auth/me", token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function changePassword(token: string, currentPassword: string, newPassword: string) {
  return authedRequest<AccountAction>("/auth/password/change", token, {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}

export type AccountAction = {
  accepted: boolean;
  delivery_configured: boolean;
  dev_token?: string | null;
};

export function requestEmailVerification(email: string) {
  return request<AccountAction>("/auth/verification/request", {
    method: "POST", body: JSON.stringify({ email }),
  });
}

export function confirmEmailVerification(token: string) {
  return request<AccountAction>("/auth/verification/confirm", {
    method: "POST", body: JSON.stringify({ token }),
  });
}

export function requestPasswordReset(email: string) {
  return request<AccountAction>("/auth/password/forgot", {
    method: "POST", body: JSON.stringify({ email }),
  });
}

export function resetPassword(token: string, password: string) {
  return request<AccountAction>("/auth/password/reset", {
    method: "POST", body: JSON.stringify({ token, password }),
  });
}

// --- Proposals -----------------------------------------------------------

export type Proposal = {
  id: number;
  owner_id: number | null;
  project_id: number | null;
  title: string;
  proposal_type: string;
  status: string;
  locale: string;
  payload: Record<string, unknown>;
  version: string;
  feasibility_study_id: number | null;
};

export function listProposals(token: string) {
  return authedRequest<Proposal[]>("/proposals/", token);
}

export function createProposal(token: string, payload: {
  title: string;
  proposal_type?: string;
  locale?: string;
  project_id?: number;
  feasibility_study_id?: number;
  payload?: Record<string, unknown>;
}) {
  return authedRequest<Proposal>("/proposals/", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getProposal(token: string, proposalId: number) {
  return authedRequest<Proposal>(`/proposals/${proposalId}`, token);
}

export function updateProposal(token: string, proposalId: number, payload: {
  title?: string;
  status?: string;
  payload?: Record<string, unknown>;
  version?: string;
}) {
  return authedRequest<Proposal>(`/proposals/${proposalId}`, token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteProposal(token: string, proposalId: number) {
  return authedRequest<void>(`/proposals/${proposalId}`, token, { method: "DELETE" });
}

// --- Entitlements --------------------------------------------------------

export type Entitlement = {
  service_key: string;
  enabled: boolean;
  plan: string;
  quota: number | null;
  used: number;
  upgrade_required?: boolean;
};

export function listEntitlements(token: string) {
  return authedRequest<Entitlement[]>("/entitlements/", token);
}

// --- Franchises (public, unauthenticated) ---------------------------------

export type Franchise = {
  id: number;
  brand: string;
  description_en?: string | null;
  description_ar?: string | null;
  sector: string;
  investment_min?: number | null;
  investment_max?: number | null;
  franchise_fee?: number | null;
  regions: string[];
  verification_status: string;
  is_active: boolean;
};

export function listFranchises() {
  return request<Franchise[]>("/franchises/");
}

// --- Business qualification & readiness -----------------------------------

export type QualificationProfile = {
  id: number;
  owner_id: number | null;
  company_name_en?: string | null;
  company_name_ar?: string | null;
  cr_number?: string | null;
  sector?: string | null;
  company_size?: string | null;
  saudization_rate?: number | null;
  overall_score: number;
  category_scores: Record<string, number>;
  recommendations: Array<Record<string, unknown>>;
};

export type QualificationRequirement = {
  id: number;
  profile_id: number;
  category: string;
  title_en: string;
  title_ar: string;
  status: string;
  is_mandatory: boolean;
  authority?: string | null;
};

export function listQualificationProfiles(token: string) {
  return authedRequest<QualificationProfile[]>("/api/qualification/", token);
}

export function createQualificationProfile(token: string, payload: Record<string, unknown>) {
  return authedRequest<QualificationProfile>("/api/qualification/", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listQualificationRequirements(token: string, profileId: number) {
  return authedRequest<QualificationRequirement[]>(`/api/qualification/${profileId}/requirements`, token);
}

export function addQualificationRequirement(token: string, profileId: number, payload: Record<string, unknown>) {
  return authedRequest<QualificationRequirement>(`/api/qualification/${profileId}/requirements`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateQualificationRequirement(token: string, profileId: number, requirementId: number, status: string) {
  return authedRequest<QualificationRequirement>(`/api/qualification/${profileId}/requirements/${requirementId}`, token, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export type AdminStats = {
  db_enabled: boolean;
  db_backend: string;
  users: number;
  projects: number;
  studies: number;
  ideas: number;
  franchises: number;
  reports: number;
  recent_activity: Array<{ id: number; action: string; entity?: string | null; entity_id?: number | null }>;
};

export function getAdminStats(token: string) {
  return authedRequest<AdminStats>("/admin/stats", token);
}

export type AdminLead = LeadPayload & { id: number; status: string };

export function listAdminLeads(token: string) {
  return authedRequest<AdminLead[]>("/leads/", token);
}

export function listAdminUsers(token: string) {
  return authedRequest<UserProfile[]>("/admin/users", token);
}

export function createAdminUser(token: string, payload: {
  email: string;
  password: string;
  full_name?: string;
  role_key: string;
  locale: "ar" | "en";
}) {
  return authedRequest<UserProfile>("/admin/users", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// --- Wave 3: Verified Opportunity & Franchise Registry -----------------------

export type FactsBreakdown = {
  published_facts?: string[];
  platform_normalized_facts?: string[];
  unknowns?: string[];
  user_assumptions_needed?: string[];
};

export type OpportunityVersionHistoryItem = {
  id: number;
  data_version: string;
  snapshot: Record<string, unknown>;
  changed_by?: number | null;
  change_reason: string;
  created_at: string;
};

export type VerifiedOpportunity = {
  id: number;
  slug: string;
  title_ar: string;
  title_en: string;
  opportunity_type: "BUSINESS_OPPORTUNITY" | "FRANCHISE";
  sector: string;
  subsector?: string | null;
  business_model?: string | null;
  target_customer?: string | null;
  geography: string;
  city?: string | null;
  region?: string | null;
  investment_min: number | null;
  investment_max: number | null;
  franchise_fee?: number | null;
  royalty_model?: string | null;
  required_space?: string | null;
  business_stage?: string | null;
  description_ar?: string | null;
  description_en?: string | null;
  brand_name?: string | null;
  official_source_url: string;
  source_owner: string;
  source_type: string;
  source_evidence?: Record<string, unknown> | null;
  first_seen_at: string;
  last_checked_at: string;
  last_verified_at: string;
  effective_from?: string | null;
  effective_to?: string | null;
  source_last_modified?: string | null;
  verification_status: string;
  data_version: string;
  is_active: boolean;
  facts_breakdown?: FactsBreakdown | null;
  field_provenance?: Record<string, unknown> | null;
  version_history?: OpportunityVersionHistoryItem[];
};

export type OpportunityComparisonItem = {
  id: number;
  title_ar: string;
  title_en: string;
  opportunity_type: string;
  brand_name?: string | null;
  sector: string;
  subsector?: string | null;
  business_model?: string | null;
  geography: string;
  city?: string | null;
  region?: string | null;
  investment_min: number | null;
  investment_max: number | null;
  franchise_fee?: number | null;
  royalty_model?: string | null;
  required_space?: string | null;
  business_stage?: string | null;
  source_owner: string;
  source_type: string;
  official_source_url: string;
  verification_status: string;
  data_version: string;
  field_provenance?: Record<string, unknown> | null;
  last_verified_at?: string | null;
};

export type CreateStudyFromOpportunityResponse = {
  project_id: number;
  study_id: number;
  title: string;
  opportunity_id: number;
  lineage: {
    source_opportunity_id: number;
    source_opportunity_slug: string;
    source_opportunity_title_ar: string;
    source_opportunity_title_en: string;
    opportunity_type: string;
    brand_name?: string | null;
    sector: string;
    subsector?: string | null;
    source_owner: string;
    source_type: string;
    official_source_url: string;
    verification_status: string;
    data_version: string;
    transferred_at: string;
    budget_type: string;
    is_user_assumption: boolean;
    budget_amount: number;
    budget_notes?: string | null;
    transferred_facts: Record<string, unknown>;
  };
};

export function listVerifiedOpportunities(filters?: {
  type?: string;
  sector?: string;
  max_budget?: number;
  min_budget?: number;
  geography?: string;
  verification_status?: string;
  search?: string;
}) {
  const params = new URLSearchParams();
  if (filters?.type) params.set("type", filters.type);
  if (filters?.sector) params.set("sector", filters.sector);
  if (filters?.max_budget !== undefined && filters.max_budget > 0) params.set("max_budget", String(filters.max_budget));
  if (filters?.min_budget !== undefined && filters.min_budget > 0) params.set("min_budget", String(filters.min_budget));
  if (filters?.geography) params.set("geography", filters.geography);
  if (filters?.verification_status) params.set("verification_status", filters.verification_status);
  if (filters?.search) params.set("search", filters.search);
  const qs = params.toString();
  return request<VerifiedOpportunity[]>("/api/v1/opportunities/" + (qs ? "?" + qs : ""));
}

export function getVerifiedOpportunity(id: number) {
  return request<VerifiedOpportunity>(`/api/v1/opportunities/${id}`);
}

export function compareVerifiedOpportunities(ids: number[]) {
  return request<OpportunityComparisonItem[]>(`/api/v1/opportunities/compare?ids=${ids.join(",")}`);
}

export interface CreateStudyFromOpportunityPayload {
  custom_budget?: number;
  study_title?: string;
  match_result_id?: number;
}

export function createStudyFromOpportunity(
  token: string,
  opportunityId: number,
  payload?: CreateStudyFromOpportunityPayload
) {
  return authedRequest<CreateStudyFromOpportunityResponse>(
    `/api/v1/opportunities/${opportunityId}/create-study`,
    token,
    {
      method: "POST",
      body: JSON.stringify(payload ?? {}),
    }
  );
}

export interface FitProfile {
  id?: number;
  user_id?: number;
  available_capital?: number | null;
  capital_constraint_type?: "HARD" | "PREFERENCE";
  preferred_sectors?: string[];
  excluded_sectors?: string[];
  preferred_opportunity_types?: string[];
  opportunity_type_constraint?: "HARD" | "PREFERENCE";
  target_region?: string | null;
  target_city?: string | null;
  preferred_business_models?: string[];
  target_customer?: string | null;
  experience_sectors?: string[];
  notes?: string | null;
  version?: number;
}

export interface CriterionEvaluation {
  criterion: string;
  label_ar: string;
  constraint_strength: "HARD" | "PREFERENCE";
  user_value: any;
  opportunity_value: any;
  result: "PASS" | "FAIL" | "UNKNOWN" | "NOT_APPLICABLE";
  reason: string;
  source_type?: string;
  source_url?: string;
  source_version?: number;
  provenance?: any;
}

export interface OpportunityMatchItem {
  result_id: number;
  opportunity_id: number;
  slug: string;
  title_ar: string;
  title_en: string;
  brand_name?: string | null;
  sector: string;
  opportunity_type: string;
  investment_min?: number | null;
  investment_max?: number | null;
  franchise_fee?: number | null;
  geography?: string;
  official_source_url?: string;
  verification_status: string;
  verification_status_at_eval?: string;
  is_active: boolean;
  match_state: "MATCH" | "POSSIBLE_MATCH" | "NEEDS_INFORMATION" | "NOT_MATCHED" | "NOT_EVALUATED";
  original_match_state: string;
  is_version_stale: boolean;
  summary_reason: string;
  missing_information: string[];
  criteria_evaluations: Record<string, CriterionEvaluation>;
  opportunity_version_at_eval: number;
  current_data_version: number;
}

export interface MatchRunResponse {
  id: number;
  evaluated_at?: string | null;
  calculation_version: string;
  fit_profile_version: number;
  fit_profile_snapshot: FitProfile;
  results_count: number;
  results: OpportunityMatchItem[];
}

export function getOpportunityFitProfile(token: string) {
  return authedRequest<FitProfile | null>("/api/v1/opportunities/fit-profile", token);
}

export function saveOpportunityFitProfile(token: string, data: FitProfile) {
  return authedRequest<FitProfile>("/api/v1/opportunities/fit-profile", token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function evaluateOpportunityFit(token: string) {
  return authedRequest<MatchRunResponse>("/api/v1/opportunities/fit-evaluate", token, {
    method: "POST",
  });
}

export function getOpportunityFitResults(token: string) {
  return authedRequest<MatchRunResponse | null>("/api/v1/opportunities/fit-results", token);
}

export function getOpportunitySingleFitResult(token: string, oppId: number) {
  return authedRequest<any>(`/api/v1/opportunities/fit-results/${oppId}`, token);
}

// =============================================================================
// Wave 4: Validation OS Interfaces & Functions
// =============================================================================

export interface ValidationHypothesis {
  id: number;
  hypothesis_type: string;
  statement: string;
  importance: string;
  status: string;
  rationale?: string | null;
  created_at?: string | null;
  evidence_count?: number;
}

export interface ValidationExperiment {
  id: number;
  hypothesis_id?: number | null;
  experiment_type: string;
  title: string;
  objective: string;
  method: string;
  planned_sample_size?: number | null;
  success_criteria: string;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
  result_summary?: string | null;
  created_at?: string | null;
}

export interface ValidationEvidenceItem {
  id: number;
  hypothesis_id?: number | null;
  experiment_id?: number | null;
  evidence_type: string;
  title: string;
  notes?: string | null;
  source_type: string;
  source_url?: string | null;
  source_owner?: string | null;
  raw_value?: number | null;
  unit?: string | null;
  captured_at?: string | null;
  evidence_strength: string;
  evidence_direction?: "SUPPORTING" | "REFUTING" | "NEUTRAL";
  is_simulated: boolean;
  structured_payload: Record<string, any>;
}

export interface ValidationDecisionItem {
  id: number;
  decision: "GO" | "GO_WITH_CONDITIONS" | "PIVOT" | "STOP";
  decision_reason: string;
  conditions: string[];
  evidence_snapshot: Record<string, any>;
  decision_version: number;
  decided_at: string;
}

export interface ValidationWorkspaceData {
  id: number;
  project_id: number;
  study_id: number;
  status: string;
  cycle_number?: number;
  total_cycles?: number;
  is_current_cycle?: boolean;
  historical_cycle_ids?: number[];
  evaluation: {
    status?: string;
    overall_status?: string;
    total_hypotheses?: number;
    counts?: Record<string, number>;
    critical_total: number;
    critical_supported: number;
    critical_untested: number;
    critical_not_supported: number;
    summary_ar: string;
  };
  created_at?: string | null;
  updated_at?: string | null;
  hypotheses: ValidationHypothesis[];
  experiments: ValidationExperiment[];
  evidence: ValidationEvidenceItem[];
  latest_decision?: ValidationDecisionItem | null;
}

export function getValidationWorkspace(token: string, studyId: number) {
  return authedRequest<ValidationWorkspaceData>(`/api/v1/validation/study/${studyId}`, token);
}

export function getValidationWorkspaceById(token: string, workspaceId: number) {
  return authedRequest<ValidationWorkspaceData>(`/api/v1/validation/workspaces/${workspaceId}`, token);
}

export function getValidationCycles(token: string, studyId: number) {
  return authedRequest<{
    study_id: number;
    cycles: Array<{
      workspace_id: number;
      cycle_number: number;
      is_current: boolean;
      status: string;
      latest_decision: string | null;
      hypotheses_count: number;
      evidence_count: number;
      created_at: string | null;
    }>;
    total_cycles: number;
  }>(`/api/v1/validation/study/${studyId}/cycles`, token);
}

export function addValidationHypothesis(
  token: string,
  workspaceId: number,
  data: {
    hypothesis_type: string;
    statement: string;
    importance: string;
    rationale?: string;
  }
) {
  return authedRequest<ValidationHypothesis>(`/api/v1/validation/workspaces/${workspaceId}/hypotheses`, token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateValidationHypothesis(
  token: string,
  hypothesisId: number,
  data: {
    statement?: string;
    importance?: string;
    status?: string;
    rationale?: string;
  }
) {
  return authedRequest<ValidationHypothesis>(`/api/v1/validation/hypotheses/${hypothesisId}`, token, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function addValidationExperiment(
  token: string,
  workspaceId: number,
  data: {
    experiment_type: string;
    title: string;
    objective: string;
    method: string;
    success_criteria: string;
    hypothesis_id?: number | null;
    planned_sample_size?: number | null;
  }
) {
  return authedRequest<ValidationExperiment>(`/api/v1/validation/workspaces/${workspaceId}/experiments`, token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateValidationExperiment(
  token: string,
  experimentId: number,
  data: {
    status?: string;
    result_summary?: string;
  }
) {
  return authedRequest<ValidationExperiment>(`/api/v1/validation/experiments/${experimentId}`, token, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function recordValidationEvidence(
  token: string,
  workspaceId: number,
  data: {
    evidence_type: string;
    title: string;
    hypothesis_id?: number | null;
    experiment_id?: number | null;
    source_type?: string;
    source_url?: string | null;
    source_owner?: string | null;
    notes?: string | null;
    raw_value?: number | null;
    unit?: string | null;
    evidence_strength?: string;
    evidence_direction?: "SUPPORTING" | "REFUTING" | "NEUTRAL";
    is_simulated?: boolean;
    structured_payload?: Record<string, any>;
  }
) {
  return authedRequest<ValidationEvidenceItem>(`/api/v1/validation/workspaces/${workspaceId}/evidence`, token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function recordValidationDecision(
  token: string,
  workspaceId: number,
  data: {
    decision: string;
    decision_reason: string;
    conditions?: string[];
  }
) {
  return authedRequest<ValidationDecisionItem>(`/api/v1/validation/workspaces/${workspaceId}/decision`, token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getValidationDecisions(token: string, workspaceId: number) {
  return authedRequest<ValidationDecisionItem[]>(`/api/v1/validation/workspaces/${workspaceId}/decisions`, token);
}

// ---------------------------------------------------------
// WAVE 5: LAUNCH & ACTUALS OS TYPES AND CLIENT APIS
// ---------------------------------------------------------

export type LaunchMilestoneStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "BLOCKED" | "DELAYED";
export type LaunchTaskStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "BLOCKED" | "CANCELLED";
export type LaunchWorkspaceStatus = "PLANNED" | "IN_PROGRESS" | "BLOCKED" | "LAUNCHED" | "PAUSED" | "CANCELLED";

export type LaunchTask = {
  id: number;
  workspace_id: number;
  milestone_id?: number | null;
  title: string;
  description?: string | null;
  owner_name?: string | null;
  due_date?: string | null;
  completed_date?: string | null;
  status: LaunchTaskStatus;
  dependency_task_id?: number | null;
  is_critical: boolean;
};

export type LaunchMilestone = {
  id: number;
  category: string;
  title: string;
  description?: string | null;
  due_date?: string | null;
  completed_date?: string | null;
  budget_allocated: number | null;
  actual_cost: number | null;
  status: LaunchMilestoneStatus;
  owner_name?: string | null;
  dependency_milestone_id?: number | null;
  is_suggested?: boolean;
  tasks?: LaunchTask[];
};

export type LaunchBaselineSnapshot = {
  id: number;
  version: number;
  snapshot_version: number;
  is_frozen: boolean;
  total_investment: number | null;
  monthly_projections: Array<{
    month: number;
    period_label: string;
    projected_revenue: number | null;
    projected_capex: number | null;
    projected_opex: number | null;
    projected_net_cashflow: number | null;
  }>;
  frozen_at: string;
  source_study_revision?: number | null;
  validation_decision_id?: number | null;
  validation_decision_version?: number | null;
  source_opportunity_id?: number | null;
  source_opportunity_version?: number | null;
  funding_context?: string | null;
  calculation_version?: string | null;
  notes?: string | null;
};

export type LaunchActualPeriod = {
  id: number;
  period_number: number;
  period_label: string;
  period_order: number;
  actual_revenue: number | null;
  transactions_count?: number | null;
  average_ticket_size?: number | null;
  actual_capex: number | null;
  actual_opex: number | null;
  total_actual_opex?: number | null;
  opex_breakdown: {
    salaries?: number | null;
    rent?: number | null;
    utilities_gov?: number | null;
    marketing?: number | null;
    inventory?: number | null;
    other?: number | null;
  };
  net_cashflow: number | null;
  closing_cash_balance?: number | null;
  source_type?: string;
  source_reference?: string | null;
  notes?: string | null;
  recorded_at: string;
};

export type LaunchVarianceReport = {
  period_label: string;
  period_order: number;
  projected: {
    revenue: number | null;
    opex: number | null;
    capex: number | null;
    net_cashflow: number | null;
  };
  actual: {
    revenue: number | null;
    opex: number | null;
    capex: number | null;
    net_cashflow: number | null;
    transactions_count?: number | null;
    average_ticket_size?: number | null;
  };
  variance: {
    revenue_diff: number | null;
    revenue_pct: number | null;
    revenue_state: string;
    opex_diff: number | null;
    opex_pct: number | null;
    opex_state: string;
    net_diff: number | null;
  };
  alert: "NORMAL" | "WATCH" | "MATERIAL_VARIANCE" | "NOT_AVAILABLE";
  explanation_ar: string;
};

export type LaunchVarianceSummary = {
  overall_health: string;
  summary_ar: string;
  period_variances: LaunchVarianceReport[];
};

export type LaunchReforecast = {
  id: number;
  version: string;
  version_number: number;
  reforecast_title: string;
  adjustment_rationale: string;
  growth_rate_adjustment_pct: number;
  opex_adjustment_pct: number;
  monthly_burn_rate: number | null;
  runway_months: number | null;
  remaining_runway_months: number | null;
  cash_flow_positive_month: number | null;
  financial_break_even_month: number | null;
  reforecast_payload: any;
  created_at: string;
};

export type LaunchWorkspaceData = {
  workspace: {
    id: number;
    study_id: number;
    project_id: number;
    status: string;
    target_launch_date?: string | null;
    actual_launch_date?: string | null;
    created_at: string;
    updated_at: string;
  };
  id: number;
  study_id: number;
  project_id: number;
  status: string;
  decision_gate: {
    decision: string;
    is_allowed: boolean;
    reason: string;
  };
  baseline_snapshots: LaunchBaselineSnapshot[];
  active_baseline: LaunchBaselineSnapshot | null;
  target_launch_date?: string | null;
  actual_launch_date?: string | null;
  milestones: LaunchMilestone[];
  tasks: LaunchTask[];
  actual_periods: LaunchActualPeriod[];
  latest_reforecast: LaunchReforecast | null;
  reforecasts: LaunchReforecast[];
  variance_summary: LaunchVarianceSummary;
  variances_summary: LaunchVarianceSummary;
};

export function getLaunchWorkspace(token: string, studyId: number) {
  return authedRequest<LaunchWorkspaceData>(`/api/v1/launch/workspaces/study/${studyId}`, token);
}

export function updateLaunchWorkspaceStatus(
  token: string,
  workspaceId: number,
  data: {
    status: LaunchWorkspaceStatus;
    actual_launch_date?: string | null;
    target_launch_date?: string | null;
  }
) {
  return authedRequest<LaunchWorkspaceData>(`/api/v1/launch/workspaces/${workspaceId}/status`, token, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function addLaunchMilestone(
  token: string,
  workspaceId: number,
  data: {
    category: string;
    title: string;
    description?: string;
    due_date?: string;
    budget_allocated?: number | null;
    owner_name?: string;
    dependency_milestone_id?: number | null;
    is_suggested?: boolean;
    status?: LaunchMilestoneStatus;
  }
) {
  return authedRequest<LaunchMilestone>(`/api/v1/launch/workspaces/${workspaceId}/milestones`, token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateLaunchMilestone(
  token: string,
  milestoneId: number,
  data: {
    status?: LaunchMilestoneStatus;
    actual_cost?: number | null;
    budget_allocated?: number | null;
    completed_date?: string | null;
    owner_name?: string;
    due_date?: string;
  }
) {
  return authedRequest<LaunchMilestone>(`/api/v1/launch/milestones/${milestoneId}`, token, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function createLaunchTask(
  token: string,
  workspaceId: number,
  data: {
    title: string;
    milestone_id?: number | null;
    description?: string;
    owner_name?: string;
    due_date?: string;
    dependency_task_id?: number | null;
    is_critical?: boolean;
    status?: LaunchTaskStatus;
  }
) {
  return authedRequest<LaunchTask>(`/api/v1/launch/workspaces/${workspaceId}/tasks`, token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateLaunchTask(
  token: string,
  taskId: number,
  data: {
    status?: LaunchTaskStatus;
    owner_name?: string;
    due_date?: string;
    completed_date?: string;
  }
) {
  return authedRequest<LaunchTask>(`/api/v1/launch/tasks/${taskId}`, token, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function recordLaunchActuals(
  token: string,
  workspaceId: number,
  data: {
    period_order: number;
    period_label: string;
    actual_revenue?: number | null;
    transactions_count?: number | null;
    average_ticket_size?: number | null;
    actual_capex?: number | null;
    actual_opex_salaries?: number | null;
    actual_opex_rent?: number | null;
    actual_opex_utilities?: number | null;
    actual_opex_marketing?: number | null;
    actual_opex_cogs?: number | null;
    actual_opex_other?: number | null;
    total_actual_opex?: number | null;
    closing_cash_balance?: number | null;
    source_type?: string;
    source_reference?: string | null;
    notes?: string;
  }
) {
  return authedRequest<LaunchActualPeriod>(`/api/v1/launch/workspaces/${workspaceId}/actuals`, token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getLaunchVariances(token: string, workspaceId: number) {
  return authedRequest<LaunchVarianceSummary>(`/api/v1/launch/workspaces/${workspaceId}/variances`, token);
}

export function createLaunchReforecast(
  token: string,
  workspaceId: number,
  data: {
    reforecast_title: string;
    adjustment_rationale: string;
    growth_rate_adjustment_pct?: number;
    opex_adjustment_pct?: number;
    explicit_cash_balance?: number | null;
  }
) {
  return authedRequest<LaunchReforecast>(`/api/v1/launch/workspaces/${workspaceId}/reforecast`, token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ==============================================================================
// WAVE 6: GROWTH OS TYPES AND CLIENT APIS
// ==============================================================================

export type GrowthWorkspaceData = {
  workspace: {
    id: number;
    study_id: number;
    project_id: number;
    user_id: number;
    status: string;
    current_health_state: string;
    current_health_summary_ar: string;
    created_at: string;
    updated_at: string;
  };
  business_health: {
    health_state: "HEALTHY" | "WATCH" | "AT_RISK" | "INSUFFICIENT_DATA";
    health_name_ar: string;
    health_summary_ar: string;
    recommendation_ar: string;
    calculation_version: string;
    supporting_metrics: Record<string, any>;
    evaluated_at: string;
  };
  trends: {
    evaluation_status: string;
    evaluation_summary_ar: string;
    periods_analyzed: number;
    metrics: Record<
      string,
      {
        metric: string;
        metric_name_ar: string;
        direction: string;
        direction_ar: string;
        period_range: string;
        first_value: number | null;
        latest_value: number | null;
        absolute_change: number | null;
        percentage_change: number | null;
      }
    >;
  };
  unit_economics: {
    calculation_status: string;
    calculation_summary_ar: string;
    period_label: string;
    metrics: Record<
      string,
      {
        name_ar: string;
        value: number | null;
        unit: string;
        is_known: boolean;
        formula_ar: string;
        note_ar?: string;
      }
    >;
  };
  risks: Array<{
    risk_type: string;
    risk_title_ar: string;
    level: "LOW" | "WATCH" | "HIGH" | "UNKNOWN";
    level_ar: string;
    evidence_ar: string;
    remedy_ar: string;
  }>;
  expansion_readiness: {
    readiness_state: "READY" | "CONDITIONALLY_READY" | "NOT_READY" | "NEEDS_INFORMATION";
    readiness_name_ar: string;
    summary_ar: string;
    prerequisites: Array<{
      code: string;
      name_ar: string;
      status: "PASS" | "FAIL" | "UNKNOWN" | "NOT_APPLICABLE";
      reason_ar: string;
    }>;
    capacity_exhaustion_identified: boolean;
    operational_stability_confirmed: boolean;
    cash_runway_sufficient: boolean;
  };
  growth_funding: {
    context_type: string;
    summary_ar: string;
    feasibility_reference: {
      funding_needed: number | null;
      capital_structure: any;
      recommended_structure: any;
    };
    wave2_matched_programs_count: number;
    wave2_matched_programs: Array<{
      program_id: number;
      program_name_ar: string;
      sponsor_name_ar: string;
      funding_type: string;
      fit_status: string;
    }>;
    disclaimer_ar: string;
  };
  actual_periods_count: number;
  scenarios: Array<{
    id: number;
    workspace_id: number;
    name: string;
    scenario_type: string;
    description: string | null;
    target_horizon_months: number;
    capex_required: number | null;
    additional_monthly_opex: number | null;
    expected_monthly_revenue_uplift: number | null;
    target_capacity_increase_pct: number | null;
    user_assumptions: Record<string, any>;
    is_active: boolean;
    created_at: string;
  }>;
  what_if_models: Array<{
    id: number;
    workspace_id: number;
    scenario_id: number | null;
    scenario_name: string;
    assumptions_summary: Record<string, any>;
    baseline_snapshot: Record<string, any>;
    derived_monthly_projections: Array<Record<string, any>>;
    estimated_cash_payback_months: number | null;
    estimated_net_runway_impact_months: number | null;
    minimum_cash_required: number | null;
    provenance: Record<string, any>;
    created_at: string;
  }>;
  monthly_reviews: Array<{
    id: number;
    workspace_id: number;
    review_period: string;
    review_version: number;
    frozen_metrics: Record<string, any>;
    review_notes: string | null;
    target_next_month: string | null;
    created_at: string;
  }>;
  decisions: Array<{
    id: number;
    workspace_id: number;
    decision: "SCALE" | "FIX" | "PIVOT" | "HOLD" | "STOP" | "NEEDS_INFORMATION";
    decision_version: number;
    decision_reason: string;
    supporting_facts: string[];
    contradicting_facts: string[];
    unknowns: string[];
    user_assumptions: Record<string, any>;
    risks: string[];
    conditions: string[];
    recommended_next_actions: string[];
    pivot_validation_workspace_id: number | null;
    re_evaluation_date: string | null;
    decided_at: string;
  }>;
  actions: Array<{
    id: number;
    workspace_id: number;
    decision_id: number | null;
    title: string;
    action_type: string;
    category: string;
    priority: string;
    status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";
    owner_name: string | null;
    due_date: string | null;
    notes: string | null;
    created_at: string;
    completed_at: string | null;
  }>;
};

export type GrowthFundingContext = {
  context_type: string;
  summary_ar: string;
  disclaimer_ar: string;
  wave2_matched_programs_count: number;
  wave2_matched_programs: Array<{
    program_id: number;
    program_name_ar: string;
    sponsor_name_ar: string;
    funding_type: string;
    fit_status: string;
    status_reason_ar?: string;
  }>;
  known_confirmed_amounts?: Record<string, number>;
  unknown_components?: string[];
  known_total?: number;
  funding_gap_status?: string;
  feasibility_reference?: {
    funding_needed: number | null;
    capital_structure: any;
    recommended_structure: any;
  };
  current_available_cash?: {
    amount: number | null;
    status: string;
    source: string;
    label_ar: string;
  };
  growth_investment_need?: {
    amount: number | null;
    status: string;
    source: string;
    label_ar: string;
  };
  confirmed_funding?: {
    owner_equity: number | null;
    confirmed_credit_facilities: number | null;
    total_confirmed: number | null;
    status: string;
    label_ar: string;
  };
  potential_funding_capacity?: {
    status: string;
    note_ar: string;
    programs_link: string;
    readiness_link: string;
  };
  funding_gap?: {
    gap_amount: number | null;
    status: string;
    funding_gap_status: string;
    known_confirmed_amounts: Record<string, number>;
    unknown_components: string[];
    known_total: number;
    label_ar: string;
    rule_explanation_ar: string;
  };
  calculation_version?: string;
};

export function getGrowthFundingContext(token: string, studyId: number, scenarioId?: number) {
  const q = scenarioId ? `?scenario_id=${scenarioId}` : "";
  return authedRequest<{ funding_context: GrowthFundingContext }>(
    `/api/v1/growth/study/${studyId}/funding-context${q}`,
    token
  );
}

export function getGrowthWorkspace(token: string, studyId: number) {
  return authedRequest<GrowthWorkspaceData>(`/api/v1/growth/study/${studyId}`, token);
}

export function createGrowthScenario(
  token: string,
  workspaceId: number,
  data: {
    name: string;
    scenario_type: string;
    description?: string;
    target_horizon_months?: number;
    capex_required?: number | null;
    additional_monthly_opex?: number | null;
    expected_monthly_revenue_uplift?: number | null;
    target_capacity_increase_pct?: number | null;
    user_assumptions?: Record<string, any>;
  }
) {
  return authedRequest<{ message: string; scenario: any }>(
    `/api/v1/growth/workspaces/${workspaceId}/scenarios`,
    token,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export function runGrowthWhatIf(
  token: string,
  workspaceId: number,
  data: {
    scenario_id?: number | null;
    scenario_name: string;
    scenario_type: string;
    target_horizon_months?: number;
    capex_required?: number | null;
    additional_monthly_opex?: number | null;
    expected_monthly_revenue_uplift?: number | null;
    target_capacity_increase_pct?: number | null;
    user_assumptions?: Record<string, any>;
  }
) {
  return authedRequest<{ message: string; model: any }>(
    `/api/v1/growth/workspaces/${workspaceId}/what-if`,
    token,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export function createGrowthReview(
  token: string,
  workspaceId: number,
  data: {
    review_period: string;
    review_notes?: string;
    target_next_month?: string;
  }
) {
  return authedRequest<{ message: string; review: any }>(
    `/api/v1/growth/workspaces/${workspaceId}/reviews`,
    token,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export function recordGrowthDecision(
  token: string,
  workspaceId: number,
  data: {
    decision: string;
    decision_reason: string;
    growth_scenario_id?: number | null;
    user_assumptions?: Record<string, any>;
    conditions?: string[];
    re_evaluation_date?: string | null;
  }
) {
  return authedRequest<{ message: string; decision: any }>(
    `/api/v1/growth/workspaces/${workspaceId}/decisions`,
    token,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export function createGrowthAction(
  token: string,
  workspaceId: number,
  data: {
    title: string;
    action_type?: string;
    category?: string;
    priority?: string;
    owner_name?: string;
    due_date?: string;
    decision_id?: number | null;
  }
) {
  return authedRequest<{ message: string; action: any }>(
    `/api/v1/growth/workspaces/${workspaceId}/actions`,
    token,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export function updateGrowthAction(
  token: string,
  actionId: number,
  data: {
    status?: string;
    notes?: string;
    due_date?: string;
    owner_name?: string;
  }
) {
  return authedRequest<{ message: string; action: any }>(
    `/api/v1/growth/actions/${actionId}`,
    token,
    {
      method: "PATCH",
      body: JSON.stringify(data),
    }
  );
}



export type FinancialMetricState = {
  label?: string;
  available?: boolean;
  display?: string;
  reason?: string | null;
  missing_condition?: string | null;
};

export type FinancialResultsLike = Record<string, unknown> | null | undefined;

const IRR_UNAVAILABLE_EN =
  "IRR cannot be calculated for these cash flows.";
const IRR_UNAVAILABLE_AR =
  "لا يمكن حساب معدل العائد الداخلي لهذه التدفقات النقدية.";
const IRR_REASON_EN =
  "No valid internal rate of return was found in range — often because cash flows do not change sign, or the profile is too extreme for a stable IRR.";
const IRR_REASON_AR =
  "لم يتم العثور على معدل عائد داخلي صالح ضمن النطاق — غالباً لأن التدفقات النقدية لا تغيّر الإشارة، أو لأن الملف متطرف جداً لاستقرار الحساب.";
const IRR_MISSING_EN =
  "Requires an initial outflow followed by net inflows (a sign change) within the projection window.";
const IRR_MISSING_AR =
  "يتطلب تدفقاً أولياً سالباً يتبعه صافي تدفقات موجبة (تغير إشارة) ضمن نافذة الإسقاط.";

const PAYBACK_UNAVAILABLE_EN =
  "Payback period cannot be calculated for these cash flows.";
const PAYBACK_UNAVAILABLE_AR =
  "لا يمكن حساب فترة الاسترداد لهذه التدفقات النقدية.";
const PAYBACK_REASON_EN =
  "Cumulative cash flow never recovers the initial investment inside the projection window.";
const PAYBACK_REASON_AR =
  "التدفق النقدي التراكمي لا يسترد الاستثمار الأولي داخل نافذة الإسقاط.";
const PAYBACK_MISSING_EN =
  "Requires cumulative net cash flows to turn non-negative within the modeled years.";
const PAYBACK_MISSING_AR =
  "يتطلب أن يصبح صافي التدفق التراكمي غير سالب خلال السنوات المُنمذَجة.";

function asState(value: unknown): FinancialMetricState | null {
  if (!value || typeof value !== "object") return null;
  return value as FinancialMetricState;
}

function neverNullText(value: unknown, fallback: string): string {
  if (value === null || value === undefined) return fallback;
  const text = String(value).trim();
  if (!text || text.toLowerCase() === "null" || text.toLowerCase() === "undefined" || text === "—") {
    return fallback;
  }
  return text;
}

export function formatIrrMetric(
  financial: FinancialResultsLike,
  ar: boolean,
): FinancialMetricState {
  const fallbackDisplay = ar ? IRR_UNAVAILABLE_AR : IRR_UNAVAILABLE_EN;
  const state = asState(financial?.irr_state);
  if (state?.display) {
    return {
      label: state.label || (ar ? "معدل العائد الداخلي" : "IRR"),
      available: Boolean(state.available),
      display: neverNullText(state.display, fallbackDisplay),
      reason: state.available ? null : state.reason || (ar ? IRR_REASON_AR : IRR_REASON_EN),
      missing_condition: state.available
        ? null
        : state.missing_condition || (ar ? IRR_MISSING_AR : IRR_MISSING_EN),
    };
  }
  const display = neverNullText(financial?.irr_display, "");
  if (display) {
    const available = financial?.irr != null && financial?.irr_available !== false;
    return {
      label: ar ? "معدل العائد الداخلي" : "IRR",
      available,
      display,
      reason: available ? null : ar ? IRR_REASON_AR : IRR_REASON_EN,
      missing_condition: available ? null : ar ? IRR_MISSING_AR : IRR_MISSING_EN,
    };
  }
  if (typeof financial?.irr === "number") {
    return {
      label: ar ? "معدل العائد الداخلي" : "IRR",
      available: true,
      display: `${(financial.irr * 100).toFixed(1)}%`,
      reason: null,
      missing_condition: null,
    };
  }
  return {
    label: ar ? "معدل العائد الداخلي" : "IRR",
    available: false,
    display: fallbackDisplay,
    reason: ar ? IRR_REASON_AR : IRR_REASON_EN,
    missing_condition: ar ? IRR_MISSING_AR : IRR_MISSING_EN,
  };
}

export function formatPaybackMetric(
  financial: FinancialResultsLike,
  ar: boolean,
): FinancialMetricState {
  const fallbackDisplay = ar ? PAYBACK_UNAVAILABLE_AR : PAYBACK_UNAVAILABLE_EN;
  const state = asState(financial?.payback_state);
  if (state?.display) {
    return {
      label: state.label || (ar ? "فترة الاسترداد" : "Payback Period"),
      available: Boolean(state.available),
      display: neverNullText(state.display, fallbackDisplay),
      reason: state.available ? null : state.reason || (ar ? PAYBACK_REASON_AR : PAYBACK_REASON_EN),
      missing_condition: state.available
        ? null
        : state.missing_condition || (ar ? PAYBACK_MISSING_AR : PAYBACK_MISSING_EN),
    };
  }
  const display = neverNullText(financial?.payback_display, "");
  if (display) {
    const available =
      financial?.payback_months != null && financial?.payback_available !== false;
    return {
      label: ar ? "فترة الاسترداد" : "Payback Period",
      available,
      display,
      reason: available ? null : ar ? PAYBACK_REASON_AR : PAYBACK_REASON_EN,
      missing_condition: available ? null : ar ? PAYBACK_MISSING_AR : PAYBACK_MISSING_EN,
    };
  }
  if (typeof financial?.payback_months === "number") {
    return {
      label: ar ? "فترة الاسترداد" : "Payback Period",
      available: true,
      display: ar
        ? `${Number(financial.payback_months).toFixed(1)} شهراً`
        : `${Number(financial.payback_months).toFixed(1)} months`,
      reason: null,
      missing_condition: null,
    };
  }
  if (typeof financial?.payback_years === "number") {
    return {
      label: ar ? "فترة الاسترداد" : "Payback Period",
      available: true,
      display: ar
        ? `${Number(financial.payback_years).toFixed(2)} سنة`
        : `${Number(financial.payback_years).toFixed(2)} years`,
      reason: null,
      missing_condition: null,
    };
  }
  return {
    label: ar ? "فترة الاسترداد" : "Payback Period",
    available: false,
    display: fallbackDisplay,
    reason: ar ? PAYBACK_REASON_AR : PAYBACK_REASON_EN,
    missing_condition: ar ? PAYBACK_MISSING_AR : PAYBACK_MISSING_EN,
  };
}

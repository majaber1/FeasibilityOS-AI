"""Assumption agent: fills archetype schema only; AI estimates are labeled."""
from __future__ import annotations

import json
import re

from langchain_core.messages import AIMessage, SystemMessage

from ..config import get_llm
from ..models.study_state import StudyState, Assumption
from ..archetypes import (
    get_assumption_schema,
    schema_keys_for,
    assert_no_saas_leakage,
    assert_no_mobility_on_professional,
    detect_services_variant,
    normalize_archetype,
)

SYSTEM_PROMPT_AR = """
أنت محلل افتراضات لدراسات الجدوى في السوق السعودي.
املأ فقط مفاتيح الافتراضات المعطاة لنوع المشروع. لا تُضف مقاييس SaaS (CAC/Churn/ARR/MRR)
إلا إذا كان التصنيف saas_digital.

لكل افتراض:
- value / low / base / high كنصوص
- source: "user" أو "AI Estimated Assumption" إذا قدّرت القيمة
- confidence: confirmed|medium|low
- ai_estimated: true إذا كانت القيمة تقدير ذكاء اصطناعي

أخرج JSON:
```json
{{
  "assumptions": [ {{"key":"...", "value":"...", "source":"...", "confidence":"medium", "low":"...", "base":"...", "high":"...", "ai_estimated": false}} ],
  "assumptions_complete": true
}}
```
"""

SYSTEM_PROMPT_EN = """
You are an assumptions analyst for Saudi feasibility studies.
Fill ONLY the provided assumption keys for this project archetype.
Do NOT add SaaS metrics (CAC/Churn/ARR/MRR) unless archetype is saas_digital.

For each assumption:
- value / low / base / high as strings
- source: "user" or "AI Estimated Assumption" when you estimate
- confidence: confirmed|medium|low
- ai_estimated: true when AI estimated

Output JSON:
```json
{{
  "assumptions": [ {{"key":"...", "value":"...", "source":"...", "confidence":"medium", "low":"...", "base":"...", "high":"...", "ai_estimated": false}} ],
  "assumptions_complete": true
}}
```
"""


def run_assumptions(state: StudyState) -> StudyState:
    lang = state.language
    archetype = normalize_archetype(state.profile.archetype if state.profile else "other")
    services_variant = getattr(state.profile, "services_variant", None) if state.profile else None
    # Rebuild context from recent user messages for variant safety.
    context_bits = []
    for msg in reversed(list(state.messages or [])):
        role = getattr(msg, "type", None) or getattr(msg, "role", None)
        content = getattr(msg, "content", None)
        if isinstance(msg, dict):
            role = msg.get("type") or msg.get("role")
            content = msg.get("content")
        if role in {"human", "user"} and content:
            context_bits.append(str(content))
            if len(context_bits) >= 3:
                break
    context_text = "\n".join(reversed(context_bits))
    schema = get_assumption_schema(
        archetype, context_text=context_text, services_variant=services_variant
    )
    allowed = schema_keys_for(
        archetype, context_text=context_text, services_variant=services_variant
    )
    schema_by_key = {f["key"]: f for f in schema}

    system_prompt = SYSTEM_PROMPT_AR if lang == "ar" else SYSTEM_PROMPT_EN

    context_parts = [
        f"Archetype: {archetype}",
        "Allowed assumption keys ONLY:\n"
        + "\n".join(
            f"- {f['key']}: {f['label_en']} ({f['input_type']}, unit={f.get('unit')})" for f in schema
        ),
    ]
    if state.structured_answers:
        context_parts.append(
            "Structured answers already collected:\n"
            + json.dumps(state.structured_answers, ensure_ascii=False)
        )
    if state.claims:
        claims_text = "\n".join(
            f"- {c.statement} ({c.source_type}, conf={c.confidence})" for c in state.claims[:12]
        )
        context_parts.append(f"Evidence:\n{claims_text}")

    extra = "\n\nContext:\n" + "\n".join(context_parts)
    messages = [SystemMessage(content=system_prompt + extra)] + list(
        state.messages[-4:] if state.messages else []
    )

    assumption_data: dict | None = None
    response_text = ""
    llm_unavailable = False
    # get_llm must be inside try/except: client init failures previously aborted
    # the agent after evidence approve had already set phase=ASSUMPTIONS_REVIEW,
    # leaving assumptions=[] and disabling Approve in the UI.
    try:
        llm = get_llm("assumptions")
        response = llm.invoke(messages)
        response_text = response.content if hasattr(response, "content") else str(response)
        assumption_data = _extract_json(response_text)
        if assumption_data is None:
            llm_unavailable = True
            response_text = (
                response_text
                or "Assumption generation used Rule Fallback (LLM response not parseable)."
            )
    except Exception as e:
        llm_unavailable = True
        response_text = f"Rule Fallback: assumption generation LLM unavailable ({e})."
        assumption_data = None

    seeded: dict[str, Assumption] = {}
    for key, raw in (state.structured_answers or {}).items():
        if key not in allowed:
            continue
        meta = schema_by_key.get(key, {})
        val = _as_str(raw).strip()
        # Discovery question ids can collide with assumption keys. Ignore
        # non-numeric placeholders ("confirmed"/"ok") for numeric fields so
        # Rule Fallback / AI can supply values financial analysis can parse.
        if not _usable_user_assumption_value(meta, val):
            continue
        seeded[key] = Assumption(
            key=key,
            value=val,
            source="user",
            confidence="confirmed",
            low=val,
            base=val,
            high=val,
            origin="user",
            input_type=meta.get("input_type"),
            unit=meta.get("unit"),
            label_en=meta.get("label_en"),
            label_ar=meta.get("label_ar"),
            ai_estimated=False,
        )

    for a in (assumption_data or {}).get("assumptions") or []:
        key = str(a.get("key") or "").strip()
        if key not in allowed:
            continue
        meta = schema_by_key.get(key, {})
        ai_est = bool(a.get("ai_estimated")) or str(a.get("source") or "").lower().startswith("ai")
        if key in seeded and seeded[key].origin == "user":
            continue
        conf = str(a.get("confidence") or "low")
        if conf not in {"confirmed", "medium", "low"}:
            conf = "low"
        source = str(a.get("source") or ("AI Estimated Assumption" if ai_est else "model"))
        if ai_est and "AI Estimated" not in source:
            source = "AI Estimated Assumption"
        default_val = _default_value_for_field(meta or {"key": key}, archetype)
        value = _as_str(a.get("value")).strip() or default_val
        low = _as_str(a.get("low")).strip() or value
        base = _as_str(a.get("base")).strip() or value
        high = _as_str(a.get("high")).strip() or value
        seeded[key] = Assumption(
            key=key,
            value=value,
            source=source,
            confidence=conf,  # type: ignore[arg-type]
            low=low,
            base=base,
            high=high,
            origin="ai_estimated" if ai_est else "user",
            input_type=meta.get("input_type"),
            unit=meta.get("unit"),
            label_en=meta.get("label_en"),
            label_ar=meta.get("label_ar"),
            ai_estimated=ai_est,
        )

    for field in schema:
        key = field["key"]
        if key in seeded:
            continue
        if not field.get("required", True):
            continue
        default_val = _default_value_for_field(field, archetype)
        if llm_unavailable:
            seeded[key] = Assumption(
                key=key,
                value=default_val,
                source="Rule Fallback",
                confidence="low",
                low=default_val,
                base=default_val,
                high=default_val,
                origin="rule_fallback",
                input_type=field.get("input_type"),
                unit=field.get("unit"),
                label_en=field.get("label_en"),
                label_ar=field.get("label_ar"),
                ai_estimated=False,
            )
        else:
            seeded[key] = Assumption(
                key=key,
                value=default_val,
                source="AI Estimated Assumption",
                confidence="low",
                low=default_val,
                base=default_val,
                high=default_val,
                origin="ai_estimated",
                input_type=field.get("input_type"),
                unit=field.get("unit"),
                label_en=field.get("label_en"),
                label_ar=field.get("label_ar"),
                ai_estimated=True,
            )

    assumptions = list(seeded.values())
    leaked = assert_no_saas_leakage(archetype, [a.key for a in assumptions])
    if leaked:
        assumptions = [a for a in assumptions if a.key not in leaked]
    if archetype == "services" and (
        (services_variant or detect_services_variant(context_text)) == "professional"
    ):
        mob = assert_no_mobility_on_professional([a.key for a in assumptions])
        if mob:
            assumptions = [a for a in assumptions if a.key not in mob]

    prev_sig = [(a.key, a.value, a.base) for a in (state.assumptions or [])]
    new_sig = [(a.key, a.value, a.base) for a in assumptions]
    state.assumptions = assumptions
    if new_sig != prev_sig or state.assumptions_version == 0:
        state.assumptions_version = int(state.assumptions_version or 0) + 1

    state.phase = "ASSUMPTIONS_REVIEW"
    state.assumptions_approved = False
    state.next_action = "review_assumptions"
    state.error = None

    summary_lines = [
        f"Assumptions prepared for archetype `{archetype}` (version {state.assumptions_version}).",
        f"Count: {len(assumptions)}. AI-estimated: {sum(1 for a in assumptions if a.ai_estimated)}.",
        "Review, edit, regenerate, or approve before financial analysis.",
    ]
    if response_text:
        summary_lines.append(response_text[:1500])
    state.messages.append(AIMessage(content="\n".join(summary_lines)))
    return state


def _as_str(v) -> str:
    if v is None:
        return ""
    return v if isinstance(v, str) else str(v)


def _usable_user_assumption_value(field: dict, val: str) -> bool:
    """Return False for empty / placeholder answers that would break financial extract."""
    if not val:
        return False
    lowered = val.strip().lower()
    if lowered in {
        "confirmed", "ok", "yes", "y", "true", "n/a", "na", "none", "null",
        "unknown", "tbd", "مؤكد", "نعم", "موافق",
    }:
        return False
    input_type = (field.get("input_type") or "").lower()
    if input_type in {"number", "currency", "percent"}:
        cleaned = val.replace(",", "").replace("%", "").replace("SAR", "").replace("ر.س", "").strip()
        try:
            float(cleaned)
        except ValueError:
            return False
    return True


def _default_value_for_field(field: dict, archetype: str) -> str:
    """Deterministic placeholders so financial extract can run when LLM is down."""
    key = field.get("key") or ""
    input_type = (field.get("input_type") or "").lower()
    defaults = {
        "target_customers": "200",
        "pricing": "500",
        "arr": "1200000",
        "mrr": "100000",
        "cac": "800",
        "churn": "3",
        "ltv": "8000",
        "acquisition_channels": "Organic",
        "initial_investment": "1500000",
        "capex": "1500000",
        "opex_monthly": "80000",
        "revenue_y1": "1200000",
        "gross_margin": "70",
        "land_cost": "5000000",
        "construction_boq": "15000000",
        "units": "100",
        "selling_price": "1200000",
        "absorption_rate": "40",
        "mw_capacity": "5",
        "rack_count": "200",
        "pue": "1.4",
        "power_cost": "0.25",
        "active_contracts": "15",
        "consultants_headcount": "20",
        "utilization_rate": "70",
        "monthly_recurring_contracts": "80000",
        "delivery_cost_monthly": "35000",
        "take_rate": "20",
        "monthly_trips": "50000",
        "drivers": "2000",
        "driver_cac": "150",
        "occupancy": "60",
        "pricing_per_kw": "400",
        "capex_total": "80000000",
        "opex_annual": "12000000",
        "financing": "50",
    }
    if key in defaults:
        return defaults[key]
    if input_type in {"currency", "number"}:
        return "100000" if archetype in {"real_estate", "data_center"} else "10000"
    if input_type == "percent":
        return "10"
    return "10000"


def _extract_json(text: str) -> dict | None:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None

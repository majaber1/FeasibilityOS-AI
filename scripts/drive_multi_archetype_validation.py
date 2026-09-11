#!/usr/bin/env python3
"""Drive multi-archetype V2 study validation against production AI API."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = os.environ.get("API_BASE", "https://feasibilityos-ai.vercel.app").rstrip("/")
OUT = Path(os.environ.get("OUT_DIR", "/opt/cursor/artifacts/workflow-validation"))
OUT.mkdir(parents=True, exist_ok=True)

SAAS_MARKERS = (
    "cac",
    "ltv",
    "churn",
    "mrr",
    "arr",
    "subscription price",
    "monthly recurring",
    "customer acquisition cost",
)

UBER = {
    "email": os.environ.get("UBER_EMAIL", "uber_ai_fill_1788980900@example.com"),
    "password": os.environ.get("UBER_PASS", "Sup3rSecretUberAI1!"),
    "study_id": os.environ.get("UBER_STUDY", "study_7373f1139f96"),
}
VALIDATOR = {
    "email": os.environ.get("VAL_EMAIL", "wf_val_1789077891@example.com"),
    "password": os.environ.get("VAL_PASS", "Val1dateWorkflowAI9!"),
}
RESIDENTIAL = {
    "study_id": os.environ.get("RE_STUDY", "study_6c7b908df981"),
    "answers": (
        "Land: 180,000 sqm freehold owned in Al Narjis, acquisition cost SAR 420M. "
        "Permits: preliminary municipal approval in progress; Wafi registration planned before off-plan sales. "
        "BOQ/construction: SAR 2.1M per villa × 420 = SAR 882M hard costs; soft costs SAR 95M; contingency 8%. "
        "Units: 420 villas (240×4BR, 140×5BR, 40×6BR). Completion today 0% (greenfield). "
        "ASP: SAR 4.2M average. Absorption 70 units/year. "
        "Financing: 35% equity / 65% construction + mortgage facilitation; target IRR 18%+. "
        "Pure real-estate development — not SaaS. No CAC/LTV/churn."
    ),
}
DATACENTER = {
    "study_id": os.environ.get("DC_STUDY", "study_11bc143d2d39"),
    "answers": (
        "IT load 40 MW Tier III; PUE target 1.30; ~4,000 racks phased. "
        "Year-1 occupancy 25%, year-3 55%, year-5 80%. Power tariff SAR 0.18/kWh. "
        "Wholesale colo pricing SAR 550/kW/month. "
        "Capex SAR 900M. Annual opex staffing+maintenance+security SAR 48M ex-power. "
        "Debt/equity 60/40, 12-year tenor, 7.5% interest. COD 36 months. "
        "Physical digital infrastructure — not a SaaS product. No subscription CAC/churn."
    ),
}


def api(method: str, path: str, token: str | None = None, body: dict | None = None, timeout: int = 300):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw[:4000]}
        return exc.code, payload


def login(email: str, password: str) -> str:
    code, body = api("POST", "/auth/login", body={"email": email, "password": password})
    if code != 200 or "access_token" not in body:
        raise RuntimeError(f"login failed {email}: {code} {body}")
    return body["access_token"]


def saas_hits(texts: list[str]) -> list[str]:
    hits = []
    for text in texts:
        low = (text or "").lower()
        for marker in SAAS_MARKERS:
            if marker in low:
                hits.append(f"{marker} :: {text[:160]}")
    return hits


def extract_questions(study: dict) -> list[str]:
    questions: list[str] = []
    missing = (study.get("profile") or {}).get("missing_information") or []
    questions.extend(str(item) for item in missing)
    for message in study.get("messages") or []:
        if not isinstance(message, dict):
            continue
        role = (message.get("type") or message.get("role") or "").lower()
        if role not in {"ai", "assistant"}:
            continue
        content = message.get("content") or ""
        for block in re.finditer(r"```json\s*(\{.*?\})\s*```", content, re.S):
            try:
                parsed = json.loads(block.group(1))
                questions.extend(str(item) for item in (parsed.get("next_questions") or []))
            except Exception:
                pass
        for line in content.splitlines():
            if "?" in line and len(line) < 280:
                questions.append(line.strip(" -*0123456789."))
    deduped: list[str] = []
    seen: set[str] = set()
    for question in questions:
        question = (question or "").strip()
        if question and question not in seen:
            seen.add(question)
            deduped.append(question)
    return deduped


def assumption_keys(study: dict) -> list[str]:
    keys = []
    for assumption in study.get("assumptions") or []:
        if isinstance(assumption, dict) and assumption.get("key"):
            keys.append(str(assumption["key"]))
    return keys


def snapshot(label: str, study: dict) -> dict:
    financial = study.get("financial_results") or {}
    questions = extract_questions(study)
    keys = assumption_keys(study)
    return {
        "label": label,
        "ts": datetime.now(timezone.utc).isoformat(),
        "study_id": study.get("study_id"),
        "phase": study.get("phase"),
        "profile": study.get("profile"),
        "questions": questions[:40],
        "assumption_keys": keys,
        "assumptions_sample": (study.get("assumptions") or [])[:15],
        "financial": {
            "analysis_complete": financial.get("analysis_complete"),
            "capex": financial.get("capex"),
            "npv": financial.get("npv"),
            "irr": financial.get("irr"),
            "payback_months": financial.get("payback_months"),
            "revenue_projections": financial.get("revenue_projections"),
            "cost_projections": financial.get("cost_projections"),
            "warnings": (financial.get("warnings") or [])[:3],
        },
        "decision_risks": study.get("decision_risks") or [],
        "verdict": study.get("verdict"),
        "decision_rationale": (study.get("decision_rationale") or "")[:1000],
        "decision_conditions": study.get("decision_conditions") or [],
        "error": study.get("error"),
        "saas_hits": saas_hits(
            questions
            + keys
            + [json.dumps(item, default=str) for item in (study.get("assumptions") or [])[:20]]
        ),
    }


def rate_limited(error) -> bool:
    text = str(error or "").lower()
    return "429" in text or "rate_limit" in text or "tokens per day" in text or "tpd" in text


def advance(token: str, study_id: str, answers: dict[str, str], max_steps: int = 18) -> dict:
    last: dict = {}
    for step in range(1, max_steps + 1):
        code, current = api("GET", f"/api/v2/studies/{study_id}", token=token)
        if code != 200:
            return {"error": f"GET {code}", "body": current}
        last = current
        phase = current.get("phase") or ""
        next_action = current.get("next_action") or ""
        error = current.get("error")
        print(
            f"  [{study_id}] step={step} phase={phase} next={next_action} "
            f"verdict={current.get('verdict')} risks={len(current.get('decision_risks') or [])}"
        )
        (OUT / f"trace_{study_id}_{step:02d}.json").write_text(
            json.dumps(snapshot(f"step_{step}", current), indent=2, default=str)
        )

        if rate_limited(error):
            return {"error": "rate_limited", "study": current, "detail": error}

        risks = current.get("decision_risks") or []
        if current.get("verdict") and risks and phase in {"DECISION_READY", "FUNDING_READY"}:
            break
        if phase == "FUNDING_READY" and current.get("verdict"):
            break

        if phase == "NEEDS_INFORMATION":
            missing = (current.get("profile") or {}).get("missing_information") or []
            if missing and step <= 5:
                message = answers.get("NEEDS_INFORMATION") or answers.get("default", "Details provided.")
                _, current = api(
                    "POST",
                    f"/api/v2/studies/{study_id}/message",
                    token=token,
                    body={"message": message, "language": "en"},
                )
                last = current
                if rate_limited(current.get("error")):
                    return {"error": "rate_limited", "study": current, "detail": current.get("error")}
                continue
            _, current = api(
                "POST",
                f"/api/v2/studies/{study_id}/approve/profile",
                token=token,
                body={"approved": True},
            )
            last = current
            continue

        if phase == "EVIDENCE_REVIEW":
            if (current.get("claims_count") or 0) == 0:
                message = answers.get("EVIDENCE_REVIEW") or answers.get("default", "Evidence provided.")
                _, current = api(
                    "POST",
                    f"/api/v2/studies/{study_id}/message",
                    token=token,
                    body={"message": message, "language": "en"},
                )
                last = current
                if rate_limited(current.get("error")):
                    return {"error": "rate_limited", "study": current, "detail": current.get("error")}
                continue
            _, current = api(
                "POST",
                f"/api/v2/studies/{study_id}/approve/evidence",
                token=token,
                body={"approved": True},
            )
            last = current
            continue

        if phase == "ASSUMPTIONS_REVIEW":
            if (current.get("assumptions_count") or 0) == 0:
                message = answers.get("ASSUMPTIONS_REVIEW") or answers.get("default", "Assumptions provided.")
                _, current = api(
                    "POST",
                    f"/api/v2/studies/{study_id}/message",
                    token=token,
                    body={"message": message, "language": "en"},
                )
                last = current
                if rate_limited(current.get("error")):
                    return {"error": "rate_limited", "study": current, "detail": current.get("error")}
                continue
            _, current = api(
                "POST",
                f"/api/v2/studies/{study_id}/approve/assumptions",
                token=token,
                body={"approved": True},
            )
            last = current
            continue

        message = (
            answers.get(phase)
            or answers.get("default")
            or "Please continue the feasibility workflow through financials, risks, and verdict."
        )
        _, current = api(
            "POST",
            f"/api/v2/studies/{study_id}/message",
            token=token,
            body={"message": message, "language": "en"},
        )
        last = current
        if rate_limited(current.get("error")):
            return {"error": "rate_limited", "study": current, "detail": current.get("error")}
    return {"study": last}


def verify_persistence(token: str, study_id: str) -> dict:
    _, first = api("GET", f"/api/v2/studies/{study_id}", token=token)
    time.sleep(1.2)
    _, second = api("GET", f"/api/v2/studies/{study_id}", token=token)
    financial_a = first.get("financial_results") or {}
    financial_b = second.get("financial_results") or {}
    return {
        "ok": True,
        "phase_stable": first.get("phase") == second.get("phase"),
        "verdict_stable": first.get("verdict") == second.get("verdict"),
        "financial_stable": financial_a.get("npv") == financial_b.get("npv")
        and financial_a.get("analysis_complete") == financial_b.get("analysis_complete"),
        "risks_stable": (first.get("decision_risks") or []) == (second.get("decision_risks") or []),
        "phase": second.get("phase"),
        "verdict": second.get("verdict"),
        "npv": financial_b.get("npv"),
        "n_risks": len(second.get("decision_risks") or []),
    }


def grade(name: str, snap: dict, persistence: dict, forbid_saas: bool) -> dict:
    financial_ok = bool((snap.get("financial") or {}).get("analysis_complete"))
    risk_ok = len(snap.get("decision_risks") or []) > 0
    verdict_ok = bool(snap.get("verdict"))
    persistence_ok = bool(
        persistence.get("ok")
        and persistence.get("phase_stable")
        and persistence.get("financial_stable")
    )
    if verdict_ok:
        persistence_ok = persistence_ok and persistence.get("verdict_stable")
    saas_ok = not (snap.get("saas_hits") or []) if forbid_saas else True
    passed = financial_ok and risk_ok and verdict_ok and persistence_ok and saas_ok
    return {
        "scenario": name,
        "result": "PASS" if passed else "FAIL",
        "gates": {
            "financial": financial_ok,
            "risk": risk_ok,
            "verdict": verdict_ok,
            "persistence": persistence_ok,
            "no_saas_bleed": saas_ok,
        },
        "classification": (snap.get("profile") or {}).get("archetype"),
        "recommended_model": (snap.get("profile") or {}).get("recommended_model"),
        "questions": snap.get("questions"),
        "assumptions": snap.get("assumption_keys"),
        "assumptions_sample": snap.get("assumptions_sample"),
        "financial": snap.get("financial"),
        "risks": snap.get("decision_risks"),
        "verdict": snap.get("verdict"),
        "decision_rationale": snap.get("decision_rationale"),
        "persistence": persistence,
        "saas_hits": snap.get("saas_hits"),
        "error": snap.get("error"),
    }


def main() -> None:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base": BASE,
        "scenarios": {},
    }

    print("=== UBER ===")
    uber_token = login(UBER["email"], UBER["password"])
    uber_advance = advance(
        uber_token,
        UBER["study_id"],
        {
            "ANALYZED": (
                "Run full risk assessment (TGA licensing, driver supply, subsidy wars, "
                "safety, unit economics, cash runway) then issue investment verdict."
            ),
            "DECISION_READY": "Confirm final investment verdict with conditions.",
            "default": "Continue to risk analysis and investment decision.",
        },
        max_steps=8,
    )
    _, uber = api("GET", f"/api/v2/studies/{UBER['study_id']}", token=uber_token)
    uber_snap = snapshot("uber_final", uber)
    (OUT / "uber_final.json").write_text(json.dumps(uber_snap, indent=2, default=str))
    uber_persist = verify_persistence(uber_token, UBER["study_id"])
    report["scenarios"]["uber"] = grade("1) Uber Ride-Hailing", uber_snap, uber_persist, forbid_saas=False)
    report["scenarios"]["uber"]["advance_error"] = uber_advance.get("error")

    print("=== RESIDENTIAL ===")
    validator_token = login(VALIDATOR["email"], VALIDATOR["password"])
    residential_advance = advance(
        validator_token,
        RESIDENTIAL["study_id"],
        {
            "NEEDS_INFORMATION": RESIDENTIAL["answers"],
            "EVIDENCE_REVIEW": RESIDENTIAL["answers"] + " Sources: founder inputs + North Riyadh villa ASP comps.",
            "ASSUMPTIONS_REVIEW": (
                "Assumptions: land_cost=420000000 SAR; construction_boq=882000000; soft_costs=95000000; "
                "unit_count=420; asp_per_unit=4200000; annual_absorption_units=70; contingency_pct=8; "
                "target_irr=0.18; equity_pct=0.35. Real-estate only — no SaaS metrics."
            ),
            "READY_FOR_ANALYSIS": "Compute real-estate financial model (sell-through, BOQ, financing gap) then risks and verdict.",
            "ANALYZED": "Produce real-estate risks (absorption, cost inflation, Wafi, mortgage rates) and investment verdict.",
            "default": RESIDENTIAL["answers"],
        },
        max_steps=18,
    )
    _, residential = api("GET", f"/api/v2/studies/{RESIDENTIAL['study_id']}", token=validator_token)
    residential_snap = snapshot("residential_final", residential)
    (OUT / "residential_final.json").write_text(json.dumps(residential_snap, indent=2, default=str))
    residential_persist = verify_persistence(validator_token, RESIDENTIAL["study_id"])
    report["scenarios"]["residential"] = grade(
        "2) Residential Real Estate",
        residential_snap,
        residential_persist,
        forbid_saas=True,
    )
    report["scenarios"]["residential"]["advance_error"] = residential_advance.get("error")

    print("=== DATA CENTER ===")
    datacenter_advance = advance(
        validator_token,
        DATACENTER["study_id"],
        {
            "NEEDS_INFORMATION": DATACENTER["answers"],
            "EVIDENCE_REVIEW": DATACENTER["answers"] + " Sources: founder engineering basis + Jeddah colo indications.",
            "ASSUMPTIONS_REVIEW": (
                "Assumptions: it_load_mw=40; price_per_kw_month=550; year1_occupancy=0.25; "
                "year3_occupancy=0.55; pue=1.30; power_tariff_per_kwh=0.18; "
                "initial_investment=900000000; annual_opex_ex_power=48000000; rack_count=4000. "
                "Infrastructure only — no SaaS."
            ),
            "READY_FOR_ANALYSIS": "Compute data-center financial model (MW, kW pricing, PUE, utilization) then risks and verdict.",
            "ANALYZED": "Produce DC risks (interconnection, tariff, hyperscaler competition, cooling/ESG) and investment verdict.",
            "default": DATACENTER["answers"],
        },
        max_steps=18,
    )
    _, datacenter = api("GET", f"/api/v2/studies/{DATACENTER['study_id']}", token=validator_token)
    datacenter_snap = snapshot("datacenter_final", datacenter)
    (OUT / "datacenter_final.json").write_text(json.dumps(datacenter_snap, indent=2, default=str))
    datacenter_persist = verify_persistence(validator_token, DATACENTER["study_id"])
    report["scenarios"]["datacenter"] = grade(
        "3) Data Center",
        datacenter_snap,
        datacenter_persist,
        forbid_saas=True,
    )
    report["scenarios"]["datacenter"]["advance_error"] = datacenter_advance.get("error")

    report["overall"] = (
        "PASS" if all(scenario["result"] == "PASS" for scenario in report["scenarios"].values()) else "FAIL"
    )
    (OUT / "scenario_report.json").write_text(json.dumps(report, indent=2, default=str))
    summary = {
        key: {
            "result": value["result"],
            "gates": value["gates"],
            "classification": value.get("classification"),
            "verdict": value.get("verdict"),
            "advance_error": value.get("advance_error"),
        }
        for key, value in report["scenarios"].items()
    }
    print(json.dumps(summary, indent=2, default=str))
    print("OVERALL", report["overall"])


if __name__ == "__main__":
    main()

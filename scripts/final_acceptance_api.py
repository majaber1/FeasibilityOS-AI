#!/usr/bin/env python3
"""Final acceptance: challenge loop + Decision→Readiness→Funding→Report per archetype."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CREDS = json.loads(Path("/opt/cursor/artifacts/workflow-validation/creds.json").read_text())
BASE = CREDS.get("api", "https://feasibilityos-ai.vercel.app")
WEB = "https://saudi-business-web.vercel.app"
OUT = Path("/opt/cursor/artifacts/final-acceptance")
OUT.mkdir(parents=True, exist_ok=True)

STUDIES = {
    "uber": {
        "email": CREDS["uber"]["email"],
        "password": CREDS["uber"]["password"],
        "study_id": CREDS["uber"]["study_id"],
        "archetype": "services",
        "challenge_key_hints": ("take_rate", "average_trip", "monthly_rides", "promo", "commission"),
        "expected_funding": ("venture", "angel", "seed", "marketplace", "mobility"),
        "forbidden_funding": ("wafi", "construction facility", "mortgage take-out"),
    },
    "residential": {
        "email": CREDS["validator"]["email"],
        "password": CREDS["validator"]["password"],
        "study_id": CREDS["validator"]["residential_study_id"],
        "archetype": "real_estate",
        "challenge_key_hints": ("asp", "absorption", "land_cost", "construction", "price", "sale"),
        "expected_funding": ("construction", "wafi", "off-plan", "mezzanine", "mortgage", "development"),
        "forbidden_funding": ("saas venture", "angel / venture seed"),
    },
    "datacenter": {
        "email": CREDS["validator"]["email"],
        "password": CREDS["validator"]["password"],
        "study_id": CREDS["validator"]["datacenter_study_id"],
        "archetype": "data_center",
        "challenge_key_hints": ("price_per_kw", "occupancy", "it_load", "pue", "mw", "kw"),
        "expected_funding": ("project finance", "infrastructure", "hyperscaler", "pue", "colo"),
        "forbidden_funding": ("consumer mortgage", "saas seed", "wafi"),
    },
}


def api(method, path, token=None, body=None, timeout=360):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw[:4000]}
        return e.code, payload


def login(email, password):
    code, body = api("POST", "/auth/login", body={"email": email, "password": password})
    if code != 200:
        raise RuntimeError(f"login failed {email}: {code} {body}")
    return body["access_token"]


def pick_assumption(assumptions, hints):
    for a in assumptions or []:
        key = (a.get("key") or "").lower()
        if any(h in key for h in hints):
            return a
    return (assumptions or [None])[0]


def post_msg(token, study_id, message):
    return api(
        "POST",
        f"/api/v2/studies/{study_id}/message",
        token=token,
        body={"message": message, "language": "en"},
        timeout=360,
    )


def challenge_loop(token, study_id, meta):
    """Change one major assumption, then drive financial→risk→decision."""
    _, before = api("GET", f"/api/v2/studies/{study_id}", token=token)
    target = pick_assumption(before.get("assumptions") or [], meta["challenge_key_hints"])
    if not target:
        return {"ok": False, "error": "no assumption to challenge"}

    key = target.get("key")
    old_val = target.get("value") or target.get("base")
    new_val = "0.35"
    kl = (key or "").lower()
    if "asp" in kl or ("price" in kl and "kw" not in kl) or "sale" in kl:
        new_val = "5500000"
    elif "occupancy" in kl or "year1" in kl:
        new_val = "0.55"
    elif "take" in kl or "commission" in kl:
        new_val = "0.35"
    elif "absorption" in kl:
        new_val = "120"
    elif "trip" in kl:
        new_val = "65"
    elif "pue" in kl:
        new_val = "1.15"
    elif "kw" in kl or "mw" in kl:
        new_val = "950"

    before_fin = before.get("financial_results") or {}
    before_npv = before_fin.get("npv")
    before_verdict = before.get("verdict")
    before_av = int(before.get("assumptions_version") or 0)
    before_dv = int(before.get("decision_version") or 0)
    before_updated = before.get("updated_at")

    steps = {}
    code, step1 = post_msg(
        token,
        study_id,
        (
            f"CHALLENGE LOOP: Change assumption '{key}' from {old_val} to {new_val}. "
            f"Update the structured assumptions JSON so '{key}' equals {new_val}. "
            f"Set assumptions_complete true."
        ),
    )
    steps["challenge_assumptions"] = {
        "http": code,
        "phase": step1.get("phase"),
        "assumptions_version": step1.get("assumptions_version"),
        "error": step1.get("error"),
        "response_excerpt": (step1.get("response") or "")[:400],
    }
    time.sleep(0.5)

    for label, text in [
        ("financial", "Recompute financial analysis with the updated assumptions. Produce NPV/IRR."),
        ("risk", "Re-run risk analysis for the updated financial model."),
        ("decision", "Issue an updated investment decision/verdict based on the new financials and risks."),
    ]:
        code, body = post_msg(token, study_id, text)
        steps[label] = {
            "http": code,
            "phase": body.get("phase"),
            "verdict": body.get("verdict"),
            "npv": (body.get("financial_results") or {}).get("npv"),
            "assumptions_version": body.get("assumptions_version"),
            "decision_version": body.get("decision_version"),
            "error": body.get("error"),
        }
        time.sleep(0.5)

    _, after = api("GET", f"/api/v2/studies/{study_id}", token=token)
    after_fin = after.get("financial_results") or {}
    after_assumptions = after.get("assumptions") or []
    changed = None
    for a in after_assumptions:
        if (a.get("key") or "").lower() == (key or "").lower():
            changed = a
            break

    after_av = int(after.get("assumptions_version") or 0)
    after_dv = int(after.get("decision_version") or 0)
    result = {
        "assumption_key": key,
        "old_value": old_val,
        "requested_new_value": new_val,
        "observed_new_value": (changed or {}).get("value") or (changed or {}).get("base"),
        "before": {
            "npv": before_npv,
            "verdict": before_verdict,
            "assumptions_version": before_av,
            "decision_version": before_dv,
            "updated_at": before_updated,
            "phase": before.get("phase"),
        },
        "after": {
            "npv": after_fin.get("npv"),
            "verdict": after.get("verdict"),
            "assumptions_version": after_av,
            "decision_version": after_dv,
            "updated_at": after.get("updated_at"),
            "phase": after.get("phase"),
            "error": after.get("error"),
            "analysis_complete": after_fin.get("analysis_complete"),
        },
        "steps": steps,
        "assumptions_version_changed": after_av > before_av,
        "financial_recalculated": bool(
            after_fin.get("analysis_complete") is True
            and (before_npv != after_fin.get("npv") or before_updated != after.get("updated_at"))
        ),
        "decision_updated": after_dv > before_dv or before_verdict != after.get("verdict"),
    }
    result["ok"] = bool(
        result["assumptions_version_changed"]
        and result["financial_recalculated"]
        and result["decision_updated"]
        and not result["after"].get("error")
        and not any((steps.get(k) or {}).get("error") for k in steps)
    )
    return result


def funding_pipeline(token, study_id, meta):
    """Decision → readiness → intelligent funding → report."""
    archetype = meta["archetype"]
    out = {"archetype": archetype, "study_id": study_id, "steps": {}}

    _, st = api("GET", f"/api/v2/studies/{study_id}", token=token)
    out["steps"]["decision_state"] = {
        "phase": st.get("phase"),
        "verdict": st.get("verdict"),
        "decision_version": st.get("decision_version"),
        "risks": st.get("decision_risks"),
        "rationale": (st.get("decision_rationale") or "")[:500],
    }

    for _ in range(4):
        phase = st.get("phase")
        pkg = st.get("funding_package") or (st.get("financial_results") or {}).get("funding_package")
        if phase in ("FUNDING_READY", "REPORT_READY") and pkg:
            break
        code, st = post_msg(
            token,
            study_id,
            (
                "Advance Decision → Funding Readiness → Intelligent Funding → Report. "
                f"This is a {archetype} project — recommend funding sources appropriate to this archetype only."
            ),
        )
        out["steps"].setdefault("advance", []).append(
            {
                "http": code,
                "phase": st.get("phase"),
                "error": st.get("error"),
                "has_funding": bool(
                    st.get("funding_package")
                    or (st.get("financial_results") or {}).get("funding_package")
                ),
                "response_excerpt": (st.get("response") or "")[:600],
            }
        )
        time.sleep(0.5)

    _, st = api("GET", f"/api/v2/studies/{study_id}", token=token)
    pkg = st.get("funding_package") or (st.get("financial_results") or {}).get("funding_package")
    report = st.get("report_outline") or (st.get("financial_results") or {}).get("report_outline")
    out["steps"]["final_state"] = {
        "phase": st.get("phase"),
        "verdict": st.get("verdict"),
        "funding_package": pkg,
        "report_outline": report,
    }

    blob = json.dumps(
        {"pkg": pkg, "report": report, "advance": out["steps"].get("advance")},
        default=str,
    ).lower()
    expected_hit = any(m in blob for m in meta["expected_funding"])
    forbidden_hit = any(m in blob for m in meta["forbidden_funding"])
    instruments = []
    if isinstance(pkg, dict):
        for i in pkg.get("recommended_instruments") or []:
            instruments.append(i.get("name") if isinstance(i, dict) else str(i))
    out["differentiation"] = {
        "expected_markers": list(meta["expected_funding"]),
        "expected_hit": expected_hit,
        "forbidden_markers": list(meta["forbidden_funding"]),
        "forbidden_hit": forbidden_hit,
        "readiness_status": (pkg or {}).get("readiness_status") if isinstance(pkg, dict) else None,
        "instruments": instruments,
        "has_report_outline": bool(report),
        "archetype_in_package": (pkg or {}).get("archetype") if isinstance(pkg, dict) else None,
    }
    out["ok"] = bool(
        pkg
        and expected_hit
        and not forbidden_hit
        and out["differentiation"]["has_report_outline"]
        and st.get("phase") in ("FUNDING_READY", "REPORT_READY")
    )
    out["phase_final"] = st.get("phase")
    return out


def main():
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "domain_check": {},
        "challenge": {},
        "funding": {},
    }

    import urllib.request as u

    for url in [WEB, f"{WEB}/login", BASE + "/health"]:
        try:
            with u.urlopen(url, timeout=30) as resp:
                report["domain_check"][url] = {"http": resp.status, "ok": 200 <= resp.status < 400}
        except Exception as e:
            report["domain_check"][url] = {"ok": False, "error": str(e)[:200]}

    for name, meta in STUDIES.items():
        print(f"=== {name} challenge + funding ===")
        tok = login(meta["email"], meta["password"])
        ch = challenge_loop(tok, meta["study_id"], meta)
        (OUT / f"challenge_{name}.json").write_text(json.dumps(ch, indent=2, default=str))
        report["challenge"][name] = {
            "ok": ch.get("ok"),
            "assumptions_version_changed": ch.get("assumptions_version_changed"),
            "financial_recalculated": ch.get("financial_recalculated"),
            "decision_updated": ch.get("decision_updated"),
            "before": ch.get("before"),
            "after": ch.get("after"),
            "assumption_key": ch.get("assumption_key"),
            "steps_phases": {k: v.get("phase") for k, v in (ch.get("steps") or {}).items()},
            "errors": {
                k: v.get("error") for k, v in (ch.get("steps") or {}).items() if v.get("error")
            },
        }
        print(
            " challenge ok",
            ch.get("ok"),
            "ver",
            ch.get("assumptions_version_changed"),
            "fin",
            ch.get("financial_recalculated"),
            "dec",
            ch.get("decision_updated"),
        )

        fund = funding_pipeline(tok, meta["study_id"], meta)
        (OUT / f"funding_{name}.json").write_text(json.dumps(fund, indent=2, default=str))
        report["funding"][name] = {
            "ok": fund.get("ok"),
            "phase_final": fund.get("phase_final"),
            "decision": fund["steps"].get("decision_state"),
            "differentiation": fund.get("differentiation"),
            "instruments": (fund.get("differentiation") or {}).get("instruments"),
            "readiness": (fund.get("differentiation") or {}).get("readiness_status"),
        }
        print(" funding ok", fund.get("ok"), "phase", fund.get("phase_final"), fund.get("differentiation"))

    report["funding_differentiation_pass"] = all(v.get("ok") for v in report["funding"].values())
    report["challenge_pass"] = all(v.get("ok") for v in report["challenge"].values())
    report["domain_pass"] = all(v.get("ok") for v in report["domain_check"].values())

    (OUT / "api_acceptance.json").write_text(json.dumps(report, indent=2, default=str))
    print(
        json.dumps(
            {
                "domain_pass": report["domain_pass"],
                "challenge_pass": report["challenge_pass"],
                "funding_diff_pass": report["funding_differentiation_pass"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

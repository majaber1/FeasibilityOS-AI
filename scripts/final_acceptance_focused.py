#!/usr/bin/env python3
"""Focused final acceptance: Uber challenge + funding stages for all archetypes."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CREDS_PATH = Path("/opt/cursor/artifacts/workflow-validation/creds.json")
CREDS = json.loads(CREDS_PATH.read_text())
BASE = CREDS["api"]
OUT = Path("/opt/cursor/artifacts/final-acceptance")
OUT.mkdir(parents=True, exist_ok=True)

STUDIES = {
    "uber": {
        "email": CREDS["uber"]["email"],
        "password": CREDS["uber"]["password"],
        "study_id": CREDS["uber"]["study_id"],
        "archetype": "services",
        "challenge_key": "take_rate",
        "challenge_value": "0.30",
        "expected_funding": ("venture", "angel", "seed", "mobility", "marketplace"),
        "forbidden_in_package": ("wafi", "construction facility", "mortgage take-out", "off-plan escrow"),
    },
    "residential": {
        "email": CREDS["validator"]["email"],
        "password": CREDS["validator"]["password"],
        "study_id": CREDS["validator"]["residential_study_id"],
        "archetype": "real_estate",
        "challenge_key": "land_cost",
        "challenge_value": "450000000",
        "expected_funding": ("construction", "wafi", "off-plan", "mezzanine", "mortgage", "development"),
        "forbidden_in_package": ("saas venture", "angel / venture seed", "hyperscaler colo"),
    },
    "datacenter": {
        "email": CREDS["validator"]["email"],
        "password": CREDS["validator"]["password"],
        "study_id": CREDS["validator"]["datacenter_study_id"],
        "archetype": "data_center",
        "challenge_key": "pue",
        "challenge_value": "1.20",
        "expected_funding": ("project finance", "infrastructure", "hyperscaler", "colo", "energy"),
        "forbidden_in_package": ("consumer mortgage", "wafi", "angel / venture seed"),
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
            return resp.status, (json.loads(raw) if raw else {})
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
        raise RuntimeError(f"login failed: {code} {body}")
    return body["access_token"]


def get_study(token, study_id):
    return api("GET", f"/api/v2/studies/{study_id}", token=token)[1]


def post_msg(token, study_id, message):
    return api(
        "POST",
        f"/api/v2/studies/{study_id}/message",
        token=token,
        body={"message": message, "language": "en"},
        timeout=360,
    )


def find_assumption(assumptions, key_hint):
    for a in assumptions or []:
        if key_hint.lower() in (a.get("key") or "").lower():
            return a
    return None


def run_challenge(token, meta, name):
    study_id = meta["study_id"]
    before = get_study(token, study_id)
    target = find_assumption(before.get("assumptions"), meta["challenge_key"])
    if not target:
        return {"ok": False, "error": f"assumption {meta['challenge_key']} not found"}

    key = target["key"]
    old_val = target.get("value") or target.get("base")
    new_val = meta["challenge_value"]
    before_npv = (before.get("financial_results") or {}).get("npv")
    before_verdict = before.get("verdict")
    before_av = int(before.get("assumptions_version") or 0)
    before_dv = int(before.get("decision_version") or 0)

    steps = {}
    code, body = post_msg(
        token,
        study_id,
        (
            f"CHALLENGE LOOP: Change assumption '{key}' from {old_val} to {new_val}. "
            f"Update structured assumptions so '{key}' value/base equals {new_val}. "
            f"Set assumptions_complete true."
        ),
    )
    steps["challenge"] = {
        "http": code,
        "phase": body.get("phase"),
        "assumptions_version": body.get("assumptions_version"),
        "error": body.get("error"),
        "excerpt": (body.get("response") or "")[:500],
    }
    time.sleep(0.5)

    for label, msg in [
        ("financial", "Recompute financial analysis with updated assumptions. Produce NPV/IRR."),
        ("risk", "Re-run risk analysis for the updated financial model."),
        ("decision", "Issue an updated investment decision/verdict from the new financials and risks."),
    ]:
        code, body = post_msg(token, study_id, msg)
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

    after = get_study(token, study_id)
    after_fin = after.get("financial_results") or {}
    changed = find_assumption(after.get("assumptions"), key)
    after_av = int(after.get("assumptions_version") or 0)
    after_dv = int(after.get("decision_version") or 0)
    result = {
        "name": name,
        "assumption_key": key,
        "old_value": old_val,
        "requested_new_value": new_val,
        "observed_new_value": (changed or {}).get("value") or (changed or {}).get("base"),
        "before": {
            "npv": before_npv,
            "verdict": before_verdict,
            "assumptions_version": before_av,
            "decision_version": before_dv,
            "phase": before.get("phase"),
        },
        "after": {
            "npv": after_fin.get("npv"),
            "verdict": after.get("verdict"),
            "assumptions_version": after_av,
            "decision_version": after_dv,
            "phase": after.get("phase"),
            "error": after.get("error"),
            "analysis_complete": after_fin.get("analysis_complete"),
        },
        "steps": steps,
        "assumptions_version_changed": after_av > before_av,
        "financial_recalculated": bool(
            after_fin.get("analysis_complete") and before_npv != after_fin.get("npv")
        ),
        "decision_updated": after_dv > before_dv or before_verdict != after.get("verdict"),
    }
    result["ok"] = bool(
        result["assumptions_version_changed"]
        and result["financial_recalculated"]
        and result["decision_updated"]
        and not result["after"].get("error")
    )
    (OUT / f"challenge_{name}.json").write_text(json.dumps(result, indent=2, default=str))
    return result


def run_funding(token, meta, name):
    study_id = meta["study_id"]
    out = {"name": name, "archetype": meta["archetype"], "study_id": study_id, "steps": {}}
    st = get_study(token, study_id)
    out["steps"]["before"] = {
        "phase": st.get("phase"),
        "verdict": st.get("verdict"),
        "decision_version": st.get("decision_version"),
        "has_funding": bool(st.get("funding_package")),
    }

    if not st.get("verdict"):
        for msg in [
            "Complete risk analysis if missing.",
            "Issue the investment decision/verdict now.",
        ]:
            code, st = post_msg(token, study_id, msg)
            out["steps"].setdefault("to_decision", []).append(
                {
                    "http": code,
                    "phase": st.get("phase"),
                    "verdict": st.get("verdict"),
                    "error": st.get("error"),
                }
            )
            if st.get("verdict"):
                break
            time.sleep(0.5)

    for _ in range(3):
        st = get_study(token, study_id)
        pkg = st.get("funding_package") or (st.get("financial_results") or {}).get("funding_package")
        report = st.get("report_outline") or (st.get("financial_results") or {}).get("report_outline")
        if st.get("phase") in ("FUNDING_READY", "REPORT_READY") and pkg and report:
            break
        code, st = post_msg(
            token,
            study_id,
            (
                "Advance Decision → Funding Readiness → Intelligent Funding → Report. "
                f"Archetype={meta['archetype']}. Recommend only archetype-appropriate funding."
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
                "excerpt": (st.get("response") or "")[:500],
            }
        )
        time.sleep(0.5)

    st = get_study(token, study_id)
    pkg = st.get("funding_package") or (st.get("financial_results") or {}).get("funding_package") or {}
    report = st.get("report_outline") or (st.get("financial_results") or {}).get("report_outline")
    pkg_blob = json.dumps(pkg, default=str).lower()
    expected_hit = any(m in pkg_blob for m in meta["expected_funding"])
    forbidden_hit = any(m in pkg_blob for m in meta["forbidden_in_package"])
    instruments = [
        (i.get("name") if isinstance(i, dict) else str(i))
        for i in (pkg.get("recommended_instruments") or [])
    ]
    out["steps"]["final"] = {
        "phase": st.get("phase"),
        "verdict": st.get("verdict"),
        "funding_package": pkg,
        "report_outline": report,
    }
    out["differentiation"] = {
        "expected_hit": expected_hit,
        "forbidden_hit": forbidden_hit,
        "readiness_status": pkg.get("readiness_status"),
        "instruments": instruments,
        "avoid": pkg.get("avoid_instruments"),
        "has_report_outline": bool(report),
        "archetype": pkg.get("archetype"),
    }
    out["ok"] = bool(
        pkg
        and expected_hit
        and not forbidden_hit
        and report
        and st.get("phase") in ("FUNDING_READY", "REPORT_READY")
        and pkg.get("archetype") == meta["archetype"]
    )
    out["phase_final"] = st.get("phase")
    (OUT / f"funding_{name}.json").write_text(json.dumps(out, indent=2, default=str))
    return out


def main():
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "challenge": {},
        "funding": {},
    }

    print("=== uber challenge ===", flush=True)
    tok = login(STUDIES["uber"]["email"], STUDIES["uber"]["password"])
    ch = run_challenge(tok, STUDIES["uber"], "uber")
    report["challenge"]["uber"] = {
        "ok": ch.get("ok"),
        "assumptions_version_changed": ch.get("assumptions_version_changed"),
        "financial_recalculated": ch.get("financial_recalculated"),
        "decision_updated": ch.get("decision_updated"),
        "before": ch.get("before"),
        "after": ch.get("after"),
        "assumption_key": ch.get("assumption_key"),
        "observed_new_value": ch.get("observed_new_value"),
        "steps_phases": {k: v.get("phase") for k, v in (ch.get("steps") or {}).items()},
        "errors": {k: v.get("error") for k, v in (ch.get("steps") or {}).items() if v.get("error")},
    }
    print("challenge", json.dumps(report["challenge"]["uber"], indent=2), flush=True)

    for name, meta in STUDIES.items():
        print(f"=== {name} funding ===", flush=True)
        tok = login(meta["email"], meta["password"])
        if name == "residential":
            st = get_study(tok, meta["study_id"])
            land = find_assumption(st.get("assumptions"), "land_cost")
            if land and str(land.get("value")) in {"0.35", "0.30", "0.40"}:
                print("repairing residential land_cost", flush=True)
                run_challenge(tok, meta, "residential_repair")
        fund = run_funding(tok, meta, name)
        report["funding"][name] = {
            "ok": fund.get("ok"),
            "phase_final": fund.get("phase_final"),
            "differentiation": fund.get("differentiation"),
        }
        print("funding", name, fund.get("ok"), fund.get("phase_final"), fund.get("differentiation"), flush=True)

    report["challenge_pass"] = bool(report["challenge"].get("uber", {}).get("ok"))
    report["funding_pass"] = all(v.get("ok") for v in report["funding"].values())
    report["funding_diff_pass"] = all(
        (v.get("differentiation") or {}).get("expected_hit")
        and not (v.get("differentiation") or {}).get("forbidden_hit")
        for v in report["funding"].values()
    )
    (OUT / "api_acceptance.json").write_text(json.dumps(report, indent=2, default=str))
    print(
        json.dumps(
            {
                "challenge_pass": report["challenge_pass"],
                "funding_pass": report["funding_pass"],
                "funding_diff_pass": report["funding_diff_pass"],
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()

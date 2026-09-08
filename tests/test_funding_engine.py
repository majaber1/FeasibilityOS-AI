import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "funding-engine"))
from matcher import match


def test_match_returns_all_programs_ranked():
    results = match("technology", stage="mvp", has_mvp=True, has_technical_team=True)
    assert len(results) == 5
    assert results[0]["score_percent"] >= results[-1]["score_percent"]
    assert all(result["source_url"].startswith("https://") for result in results)
    assert all(result["eligibility_sample_ar"] for result in results)


def test_unrelated_industry_scores_lower():
    tech_results = match("technology", stage="mvp")
    tourism_results = match("tourism", stage="mvp")
    ntdp_tech = next(r for r in tech_results if r["program"] == "NTDP")
    ntdp_tourism = next(r for r in tourism_results if r["program"] == "NTDP")
    assert ntdp_tech["score_percent"] > ntdp_tourism["score_percent"]

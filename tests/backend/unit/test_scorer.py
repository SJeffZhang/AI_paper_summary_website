import pytest

from app.services.scorer import Scorer


def test_score_paper_accumulates_expected_signals(sample_paper_payload):
    scored = Scorer().score_paper(sample_paper_payload.copy())

    assert scored["score"] == 193
    assert scored["score_reasons"] == {
        "top_org": 20,
        "hf_recommend": 30,
        "community_popularity": 40,
        "top_conf": 25,
        "has_code": 20,
        "practitioner_relevance": 15,
        "academic_influence": 18,
        "os_trending": 25,
    }
    assert scored["direction"] == "RAG"
    assert scored["threshold_category"] == "focus"


def test_practitioner_keyword_matching_uses_boundaries(sample_paper_payload):
    paper = sample_paper_payload.copy()
    paper["title_original"] = "Ragged tensors for vision"
    paper["abstract"] = "We study predeployment checks without production rollout terms."
    paper["venue"] = "Workshop"
    paper["authors"] = [{"name": "Test", "affiliation": "Independent Lab"}]
    paper["upvotes"] = 0
    paper["citations"] = 0
    paper["is_hf_daily"] = False
    paper["is_trending"] = False

    scored = Scorer().score_paper(paper)

    assert "practitioner_relevance" not in scored["score_reasons"]
    assert scored["threshold_category"] == "candidate"


def test_top_org_signal_can_use_paper_level_affiliations(sample_paper_payload):
    paper = sample_paper_payload.copy()
    paper["authors"] = [{"name": "Test", "affiliation": ""}]
    paper["affiliations"] = ["Stanford University"]

    scored = Scorer().score_paper(paper)

    assert scored["score_reasons"]["top_org"] == 20


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (49, "candidate"),
        (50, "watching"),
        (79, "watching"),
        (80, "focus"),
    ],
)
def test_threshold_category_boundaries(score, expected):
    assert Scorer._determine_threshold_category(score) == expected


def test_direction_detection_respects_taxonomy_order(sample_paper_payload):
    paper = sample_paper_payload.copy()
    paper["title_original"] = "Agent planning for retrieval-augmented reasoning"
    paper["abstract"] = "This combines agent execution with RAG."

    scored = Scorer().score_paper(paper)

    assert scored["direction"] == "Agent"

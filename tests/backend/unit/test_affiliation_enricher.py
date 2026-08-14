import json

import pytest

from app.services.affiliation_enricher import AffiliationEnricher


class FakeAIProcessor:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def _call_llm(self, **kwargs):
        self.calls.append(kwargs)
        if not self.outputs:
            raise AssertionError("unexpected LLM call")
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output


def _paper():
    return {
        "arxiv_id": "2604.00001",
        "title_original": "A Paper With Institutions",
        "authors": [
            {"name": "Alice Doe", "affiliation": ""},
            {"name": "Bob Smith", "affiliation": ""},
        ],
        "pdf_url": "https://arxiv.org/pdf/2604.00001.pdf",
    }


def _page_text():
    return (
        "A Paper With Institutions Alice Doe OpenAI, San Francisco, CA. "
        "Bob Smith Stanford University, Stanford, CA. "
        "Mila - Quebec AI Institute. Correspondence to alice@example.com. "
        "This first page contains enough text for a reliable extraction. "
    ) * 3


def _enricher(fake_ai):
    return AffiliationEnricher(
        ai_processor=fake_ai,
        downloader=lambda _url: b"%PDF fake",
        page_text_extractor=lambda _path: _page_text(),
    )


def _reviewed_affiliations(*items):
    return json.dumps({"affiliations": list(items)})


def test_enrich_paper_writes_paper_level_affiliations(monkeypatch):
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_PAGE_TEXT_MIN_CHARS", 20)
    fake_ai = FakeAIProcessor(
        [_reviewed_affiliations(
            {"name": "OpenAI", "is_institution": True, "reason": ""},
            {"name": "Stanford University", "is_institution": True, "reason": ""},
        )]
    )

    result = _enricher(fake_ai).enrich_paper(_paper())

    assert result.status == "overwrite_applied"
    assert result.attempts == 1
    assert result.affiliation_count == 2
    assert result.affiliations == ["OpenAI", "Stanford University"]
    assert "JSON output contract" in fake_ai.calls[0]["user_content"]
    assert fake_ai.calls[0]["response_format"] == {"type": "json_object"}
    assert len(fake_ai.calls) == 1


def test_enrich_paper_accepts_json_organization_list(monkeypatch):
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_PAGE_TEXT_MIN_CHARS", 20)
    fake_ai = FakeAIProcessor(
        [
            json.dumps(
                {
                    "affiliations": [
                        {"name": "OpenAI", "is_institution": True, "reason": ""},
                        {"name": "Stanford University", "is_institution": True, "reason": ""},
                    ]
                }
            )
        ]
    )

    result = _enricher(fake_ai).enrich_paper(_paper())

    assert result.status == "overwrite_applied"
    assert result.affiliations == ["OpenAI", "Stanford University"]


def test_enrich_paper_retries_with_validator_feedback(monkeypatch):
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_PAGE_TEXT_MIN_CHARS", 20)
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_MAX_RETRIES", 2)
    fake_ai = FakeAIProcessor(
        [
            _reviewed_affiliations(
                {"name": "OpenAI", "is_institution": True, "reason": ""},
                {"name": "alice@example.com", "is_institution": False, "reason": "email"},
            ),
            _reviewed_affiliations(
                {"name": "OpenAI", "is_institution": True, "reason": ""},
                {"name": "Stanford University", "is_institution": True, "reason": ""},
            ),
        ]
    )

    result = _enricher(fake_ai).enrich_paper(_paper())

    assert result.status == "overwrite_applied"
    assert result.attempts == 2
    assert result.affiliations == ["OpenAI", "Stanford University"]
    second_prompt = fake_ai.calls[1]["user_content"]
    assert "Rejected candidate lines:" in second_prompt
    assert "alice@example.com" in second_prompt


def test_enrich_paper_stops_after_configured_attempts(monkeypatch):
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_PAGE_TEXT_MIN_CHARS", 20)
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_MAX_RETRIES", 2)
    fake_ai = FakeAIProcessor(
        [
            _reviewed_affiliations(
                {"name": "OpenAI", "is_institution": True, "reason": ""},
                {"name": "alice@example.com", "is_institution": False, "reason": "email"},
            ),
            _reviewed_affiliations(
                {"name": "OpenAI", "is_institution": True, "reason": ""},
                {"name": "alice@example.com", "is_institution": False, "reason": "email"},
            ),
        ]
    )

    result = _enricher(fake_ai).enrich_paper(_paper())

    assert result.status == "skipped_not_institution"
    assert result.attempts == 2
    assert result.affiliations == []
    assert len(fake_ai.calls) == 2


def test_enrich_paper_reports_empty_extraction_as_low_confidence(monkeypatch):
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_PAGE_TEXT_MIN_CHARS", 20)
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_MAX_RETRIES", 1)
    fake_ai = FakeAIProcessor([_reviewed_affiliations()])

    result = _enricher(fake_ai).enrich_paper(_paper())

    assert result.status == "skipped_low_confidence"
    assert result.reasons == ["empty_or_low_quality_output: no valid affiliations extracted"]


def test_enrich_paper_rejects_missing_text_evidence(monkeypatch):
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_PAGE_TEXT_MIN_CHARS", 20)
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_MAX_RETRIES", 1)
    fake_ai = FakeAIProcessor([_reviewed_affiliations(
        {"name": "OpenAI", "is_institution": True, "reason": ""},
        {"name": "Google DeepMind", "is_institution": True, "reason": ""},
    )])

    result = _enricher(fake_ai).enrich_paper(_paper())

    assert result.status == "skipped_no_text_evidence"
    assert "Google DeepMind" in result.reasons[0]
    assert len(fake_ai.calls) == 1


def test_enrich_paper_does_not_require_author_records(monkeypatch):
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_PAGE_TEXT_MIN_CHARS", 20)
    fake_ai = FakeAIProcessor([_reviewed_affiliations(
        {"name": "Mila", "is_institution": True, "reason": ""},
    )])
    paper = {**_paper(), "authors": []}

    result = _enricher(fake_ai).enrich_paper(paper)

    assert result.status == "overwrite_applied"
    assert result.affiliations == ["Mila"]


def test_enrich_paper_reports_short_first_page_text(monkeypatch):
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_PAGE_TEXT_MIN_CHARS", 1000)
    fake_ai = FakeAIProcessor(["OpenAI"])
    enricher = AffiliationEnricher(
        ai_processor=fake_ai,
        downloader=lambda _url: b"%PDF fake",
        page_text_extractor=lambda _path: "OpenAI",
    )

    result = enricher.enrich_paper(_paper())

    assert result.status == "text_extract_failed"
    assert fake_ai.calls == []


def test_enrich_paper_reports_invalid_review_structure(monkeypatch):
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_PAGE_TEXT_MIN_CHARS", 20)
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_MAX_RETRIES", 1)
    fake_ai = FakeAIProcessor([json.dumps({"organizations": [{"name": "OpenAI"}]})])

    result = _enricher(fake_ai).enrich_paper(_paper())

    assert result.status == "skipped_structure_invalid"
    assert "affiliation_output_must_contain" in result.reasons[0]


def test_enrich_paper_accepts_reviewed_json_affiliations(monkeypatch):
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_PAGE_TEXT_MIN_CHARS", 20)
    fake_ai = FakeAIProcessor([_reviewed_affiliations(
        {"name": "OpenAI", "is_institution": True, "reason": ""},
        {"name": "Stanford University", "is_institution": True, "reason": ""},
    )])

    result = _enricher(fake_ai).enrich_paper(_paper())

    assert result.status == "overwrite_applied"
    assert result.affiliations == ["OpenAI", "Stanford University"]


def test_enrich_paper_rejects_title_fragment_candidates(monkeypatch):
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_PAGE_TEXT_MIN_CHARS", 20)
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_MAX_RETRIES", 1)
    fake_ai = FakeAIProcessor([_reviewed_affiliations(
        {"name": "SpatialEvo", "is_institution": True, "reason": ""},
        {"name": "StepFun", "is_institution": True, "reason": ""},
    )])
    paper = {
        **_paper(),
        "title_original": "SpatialEvo: Self-Evolving Spatial Intelligence via Deterministic Geometric Environments",
    }

    result = _enricher(fake_ai).enrich_paper(paper)

    assert result.status == "skipped_not_institution"
    assert "looks_like_title_fragment" in result.reasons[0]


def test_strip_title_from_front_matter_removes_exact_title_and_prefix():
    page_text = (
        "SpatialEvo: Self-Evolving Spatial Intelligence via Deterministic Geometric Environments "
        "Alice 1 ZhejiangUniversity 2 StepFun"
    )

    stripped = AffiliationEnricher._strip_title_from_front_matter(
        page_text,
        "SpatialEvo: Self-Evolving Spatial Intelligence via Deterministic Geometric Environments",
    )

    assert stripped == "Alice 1 ZhejiangUniversity 2 StepFun"


def test_enrich_paper_handles_numbered_affiliation_block_in_one_request(monkeypatch):
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_PAGE_TEXT_MIN_CHARS", 20)
    fake_ai = FakeAIProcessor([_reviewed_affiliations(
        {"name": "ZhejiangUniversity", "is_institution": True, "reason": ""},
        {"name": "StepFun", "is_institution": True, "reason": ""},
    )])
    page_text = (
        "SpatialEvo: Self-Evolving Spatial Intelligence via Deterministic Geometric Environments "
        "DingmingLi1,YingxiuZhao2 1 ZhejiangUniversity 2 StepFun GitHub HuggingFace Abstract"
    )
    enricher = AffiliationEnricher(
        ai_processor=fake_ai,
        downloader=lambda _url: b"%PDF fake",
        page_text_extractor=lambda _path: page_text,
    )

    result = enricher.enrich_paper(
        {
            "arxiv_id": "2604.14144",
            "title_original": "SpatialEvo: Self-Evolving Spatial Intelligence via Deterministic Geometric Environments",
            "pdf_url": "https://arxiv.org/pdf/2604.14144.pdf",
        }
    )

    assert result.status == "overwrite_applied"
    assert result.affiliations == ["ZhejiangUniversity", "StepFun"]
    assert len(fake_ai.calls) == 1
    assert fake_ai.calls[0]["response_format"] == {"type": "json_object"}


def test_enrich_paper_retries_after_review_rejection(monkeypatch):
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_PAGE_TEXT_MIN_CHARS", 20)
    monkeypatch.setattr("app.services.affiliation_enricher.settings.AFFILIATION_ENRICH_MAX_RETRIES", 3)
    fake_ai = FakeAIProcessor(
        [
            _reviewed_affiliations(
                {"name": "ZhejiangUniversity", "is_institution": False, "reason": "invalid label"},
            ),
            _reviewed_affiliations(
                {"name": "ZhejiangUniversity", "is_institution": True, "reason": ""},
                {"name": "StepFun", "is_institution": True, "reason": ""},
            ),
        ]
    )
    page_text = (
        "SpatialEvo: Self-Evolving Spatial Intelligence via Deterministic Geometric Environments "
        "DingmingLi1,YingxiuZhao2 1 ZhejiangUniversity 2 StepFun GitHub HuggingFace Abstract"
    )
    enricher = AffiliationEnricher(
        ai_processor=fake_ai,
        downloader=lambda _url: b"%PDF fake",
        page_text_extractor=lambda _path: page_text,
    )

    result = enricher.enrich_paper(
        {
            "arxiv_id": "2604.14144",
            "title_original": "SpatialEvo: Self-Evolving Spatial Intelligence via Deterministic Geometric Environments",
            "pdf_url": "https://arxiv.org/pdf/2604.14144.pdf",
        }
    )

    assert result.status == "overwrite_applied"
    assert result.attempts == 2
    assert result.affiliations == ["ZhejiangUniversity", "StepFun"]
    assert len(fake_ai.calls) == 2
    assert all(call["response_format"] == {"type": "json_object"} for call in fake_ai.calls)


def test_parse_single_review_output_rejects_prompt_echo_without_verdict():
    with pytest.raises(ValueError, match="review_invalid_verdict"):
        AffiliationEnricher(ai_processor=FakeAIProcessor([]))._parse_single_review_output(
            "Valid replies: YES | NO: email | NO: generic phrase",
            "At the",
        )


def test_parse_single_review_output_accepts_verbose_institution_description():
    approved, reason = AffiliationEnricher(ai_processor=FakeAIProcessor([]))._parse_single_review_output(
        (
            'The user wants me to classify whether "ZhejiangUniversity" is the name of an institution or organization.\n\n'
            "Zhejiang University is a major public research university in Hangzhou, China."
        ),
        "ZhejiangUniversity",
    )

    assert approved is True
    assert reason == ""


def test_parse_single_review_output_accepts_verbose_negative_description():
    approved, reason = AffiliationEnricher(ai_processor=FakeAIProcessor([]))._parse_single_review_output(
        '"At the" is not the name of an institution or organization. It is a generic phrase.',
        "At the",
    )

    assert approved is False
    assert reason

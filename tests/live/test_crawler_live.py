"""Live tests for crawler-side external data sources only.

These tests intentionally do not claim end-to-end coverage for the LLM, MySQL
bootstrap, run_pipeline_once.py, API reads, or frontend integration.
"""

import re

import pytest

from app.services.crawler import Crawler
from tests.live.helpers import probe_live_dates


pytestmark = pytest.mark.live

REPO_PATTERN = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")


@pytest.fixture(scope="session")
def live_probe():
    return probe_live_dates(days=14)


def test_fetch_hf_papers_live(live_probe):
    assert live_probe["hf_date"], "No Hugging Face Daily Papers data was found in the last 14 days."

    papers = Crawler()._fetch_hf_papers(live_probe["hf_date"])

    assert isinstance(papers, list)
    assert papers, "Hugging Face Daily Papers returned an empty list."
    sample = papers[0]
    for field in ("arxiv_id", "title_original", "abstract", "pdf_url", "upvotes", "arxiv_publish_date"):
        assert sample.get(field) not in (None, ""), f"Hugging Face paper missing field: {field}"


def test_fetch_arxiv_papers_live(live_probe):
    assert live_probe["arxiv_date"], "No arXiv data was found in the last 14 days."

    papers = Crawler()._fetch_arxiv_papers(live_probe["arxiv_date"])

    assert isinstance(papers, list)
    assert papers, "arXiv returned an empty list."
    sample = papers[0]
    for field in ("arxiv_id", "title_original", "authors", "abstract", "pdf_url", "arxiv_publish_date"):
        assert sample.get(field) not in (None, ""), f"arXiv paper missing field: {field}"
    assert isinstance(sample["authors"], list) and sample["authors"], "arXiv authors must be a non-empty list."


def test_fetch_github_trending_live():
    repos = Crawler()._fetch_github_trending()

    assert isinstance(repos, list)
    assert repos, "GitHub Trending returned an empty list."
    assert any(REPO_PATTERN.match(repo) for repo in repos), "GitHub Trending did not return owner/repo strings."


def test_fetch_semantic_scholar_citation_count_live(live_probe):
    sample = live_probe["hf_sample"] or live_probe["arxiv_sample"]
    assert sample, "No live paper sample was found for Semantic Scholar citation lookup."

    citations = Crawler()._fetch_citation_count(sample["arxiv_id"])

    assert isinstance(citations, int)
    assert citations >= 0


def test_fetch_papers_end_to_end_live(live_probe):
    assert live_probe["combined_date"], "No date in the last 14 days had both HF and arXiv data available."

    papers = Crawler().fetch_papers(fetch_date=live_probe["combined_date"])

    assert isinstance(papers, list)
    assert papers, "Merged crawler output was empty."
    assert any(paper.get("is_hf_daily") for paper in papers), "Merged results did not contain any HF daily paper."
    sample = papers[0]
    for field in ("title_original", "authors", "abstract", "pdf_url", "citations"):
        assert field in sample, f"Merged paper missing field: {field}"
    assert "is_trending" in sample

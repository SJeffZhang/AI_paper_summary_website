import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

from app.core.config import settings


class Crawler:
    """
    Fetch daily papers from Hugging Face Daily Papers and arXiv, then normalize them
    into the PRD v2.25 metadata structure.
    """

    ARXIV_CATEGORIES = ["cs.AI", "cs.CL", "cs.LG", "cs.CV", "cs.MA", "cs.IR"]
    ARXIV_API_URL = "http://export.arxiv.org/api/query"
    ARXIV_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    GITHUB_REPO_PATTERN = re.compile(r"github\.com/([a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+)", re.IGNORECASE)

    def __init__(self, hf_api_url: str = settings.HUGGINGFACE_API_URL):
        self.hf_api_url = hf_api_url

    def fetch_papers(self, fetch_date: Optional[str] = None) -> List[Dict[str, Any]]:
        if fetch_date is None:
            target_date = datetime.now(timezone(timedelta(hours=8))) - timedelta(days=3)
            fetch_date = target_date.strftime("%Y-%m-%d")

        hf_papers = self._fetch_hf_papers(fetch_date)
        arxiv_papers = self._fetch_arxiv_papers(fetch_date)

        merged = {paper["arxiv_id"]: paper for paper in arxiv_papers}
        for paper in hf_papers:
            existing = merged.get(paper["arxiv_id"])
            if existing:
                merged[paper["arxiv_id"]] = self._merge_normalized_paper(existing, paper)
            else:
                paper["is_hf_daily"] = True
                merged[paper["arxiv_id"]] = paper

        return self.enrich_metadata(list(merged.values()))

    def enrich_metadata(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        trending_repos = {repo.lower() for repo in self._fetch_github_trending()}

        for paper in papers:
            paper["citations"] = self._fetch_citation_count(paper["arxiv_id"])
            paper["is_trending"] = any(
                repo.lower() in trending_repos for repo in self._extract_github_repos(paper)
            )

        return papers

    def _fetch_citation_count(self, arxiv_id: str) -> int:
        try:
            response = requests.get(
                f"https://api.semanticscholar.org/graph/v1/paper/ARXIV:{arxiv_id}",
                params={"fields": "citationCount"},
                timeout=5,
            )
            response.raise_for_status()
            return int(response.json().get("citationCount", 0) or 0)
        except Exception:
            return 0

    def _fetch_github_trending(self) -> List[str]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        }

        try:
            response = requests.get("https://github.com/trending", headers=headers, timeout=15)
            response.raise_for_status()
        except Exception:
            return []

        repos = re.findall(
            r'href="/([a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+)"\s+data-view-component="true"\s+class="Link"',
            response.text,
        )
        return [repo for repo in repos if "/" in repo and not repo.startswith("trending/")]

    def _fetch_hf_papers(self, fetch_date: str) -> List[Dict[str, Any]]:
        try:
            response = requests.get(self.hf_api_url, params={"date": fetch_date}, timeout=30)
            response.raise_for_status()
            return self._normalize_hf_data(response.json(), fallback_date=fetch_date)
        except Exception:
            return []

    def _fetch_arxiv_papers(self, fetch_date: str) -> List[Dict[str, Any]]:
        papers: List[Dict[str, Any]] = []
        for category in self.ARXIV_CATEGORIES:
            params = {
                "search_query": f"cat:{category}",
                "start": 0,
                "max_results": 300,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            try:
                response = requests.get(self.ARXIV_API_URL, params=params, timeout=30)
                response.raise_for_status()
                papers.extend(self._parse_arxiv_xml(response.text, fetch_date))
            except Exception:
                continue
        return papers

    def _parse_arxiv_xml(self, xml_text: str, target_date: str) -> List[Dict[str, Any]]:
        root = ET.fromstring(xml_text)
        papers: List[Dict[str, Any]] = []

        for entry in root.findall("atom:entry", self.ARXIV_ATOM_NS):
            published = entry.findtext("atom:published", default="", namespaces=self.ARXIV_ATOM_NS)
            pub_date = published.split("T")[0]
            if pub_date != target_date:
                continue

            arxiv_id = entry.findtext("atom:id", default="", namespaces=self.ARXIV_ATOM_NS).split("/")[-1]
            title = self._normalize_text(entry.findtext("atom:title", default="", namespaces=self.ARXIV_ATOM_NS))
            abstract = self._normalize_text(entry.findtext("atom:summary", default="", namespaces=self.ARXIV_ATOM_NS))
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            venue = self._normalize_text(
                entry.findtext("arxiv:journal_ref", default="", namespaces=self.ARXIV_ATOM_NS)
            ) or None

            authors = []
            for author in entry.findall("atom:author", self.ARXIV_ATOM_NS):
                authors.append(
                    {
                        "name": self._normalize_text(
                            author.findtext("atom:name", default="", namespaces=self.ARXIV_ATOM_NS)
                        ),
                        "affiliation": self._normalize_text(
                            author.findtext("arxiv:affiliation", default="", namespaces=self.ARXIV_ATOM_NS)
                        ),
                    }
                )

            papers.append(
                {
                    "arxiv_id": arxiv_id,
                    "title_zh": None,
                    "title_original": title,
                    "authors": authors,
                    "venue": venue,
                    "abstract": abstract,
                    "pdf_url": pdf_url,
                    "upvotes": 0,
                    "arxiv_publish_date": pub_date,
                    "is_hf_daily": False,
                }
            )

        return papers

    def _normalize_hf_data(self, raw_data: List[Dict[str, Any]], fallback_date: str) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []

        for item in raw_data:
            paper_info = item.get("paper", {})
            arxiv_id = paper_info.get("id")
            if not arxiv_id:
                continue

            title_original = self._normalize_text(paper_info.get("title", ""))
            published_at = item.get("publishedAt", "") or paper_info.get("publishedAt", "")
            arxiv_publish_date = published_at.split("T")[0] if "T" in published_at else fallback_date
            authors = [
                {
                    "name": self._normalize_text(author.get("name", "")),
                    "affiliation": self._normalize_text(author.get("affiliation", "")),
                }
                for author in paper_info.get("authors", [])
                if author.get("name")
            ]

            normalized.append(
                {
                    "arxiv_id": arxiv_id,
                    "title_zh": None,
                    "title_original": title_original,
                    "authors": authors,
                    "venue": self._normalize_text(
                        paper_info.get("venue") or paper_info.get("conference") or item.get("venue", "")
                    )
                    or None,
                    "abstract": self._normalize_text(paper_info.get("summary", "")),
                    "pdf_url": paper_info.get("pdfUrl") or f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                    "upvotes": int(paper_info.get("upvotes", 0) or 0),
                    "arxiv_publish_date": arxiv_publish_date,
                    "is_hf_daily": True,
                }
            )

        return normalized

    def _extract_github_repos(self, paper: Dict[str, Any]) -> List[str]:
        text = " ".join(
            filter(
                None,
                [
                    paper.get("title_original", ""),
                    paper.get("abstract", ""),
                ],
            )
        )
        return [repo.strip("/").split(")")[0] for repo in self.GITHUB_REPO_PATTERN.findall(text)]

    @staticmethod
    def _normalize_text(value: Any) -> str:
        return " ".join(str(value or "").replace("\n", " ").split())

    def _merge_normalized_paper(self, arxiv_paper: Dict[str, Any], hf_paper: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(arxiv_paper)
        merged["title_zh"] = arxiv_paper.get("title_zh") or hf_paper.get("title_zh")
        merged["title_original"] = self._prefer_richer_text(
            arxiv_paper.get("title_original"),
            hf_paper.get("title_original"),
        )
        merged["authors"] = self._prefer_richer_authors(
            arxiv_paper.get("authors"),
            hf_paper.get("authors"),
        )
        merged["venue"] = self._prefer_richer_text(arxiv_paper.get("venue"), hf_paper.get("venue")) or None
        merged["abstract"] = self._prefer_richer_text(arxiv_paper.get("abstract"), hf_paper.get("abstract"))
        merged["pdf_url"] = self._prefer_pdf_url(arxiv_paper.get("pdf_url"), hf_paper.get("pdf_url"))
        merged["upvotes"] = max(int(arxiv_paper.get("upvotes", 0) or 0), int(hf_paper.get("upvotes", 0) or 0))
        merged["arxiv_publish_date"] = arxiv_paper.get("arxiv_publish_date") or hf_paper.get("arxiv_publish_date")
        merged["is_hf_daily"] = bool(arxiv_paper.get("is_hf_daily") or hf_paper.get("is_hf_daily"))
        return merged

    @staticmethod
    def _prefer_richer_text(primary: Optional[str], secondary: Optional[str]) -> str:
        primary_text = str(primary or "").strip()
        secondary_text = str(secondary or "").strip()
        if not primary_text:
            return secondary_text
        if not secondary_text:
            return primary_text
        return primary_text if len(primary_text) >= len(secondary_text) else secondary_text

    @staticmethod
    def _prefer_richer_authors(primary: Optional[List[Dict[str, Any]]], secondary: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        primary_authors = list(primary or [])
        secondary_authors = list(secondary or [])
        if not primary_authors:
            return secondary_authors
        if not secondary_authors:
            return primary_authors

        def score(authors: List[Dict[str, Any]]) -> tuple[int, int, int]:
            non_empty_affiliations = sum(1 for author in authors if str(author.get("affiliation", "")).strip())
            non_empty_names = sum(1 for author in authors if str(author.get("name", "")).strip())
            total_chars = sum(len(str(author.get("name", "")).strip()) + len(str(author.get("affiliation", "")).strip()) for author in authors)
            return (non_empty_affiliations, non_empty_names, total_chars)

        return primary_authors if score(primary_authors) >= score(secondary_authors) else secondary_authors

    @staticmethod
    def _prefer_pdf_url(primary: Optional[str], secondary: Optional[str]) -> str:
        primary_url = str(primary or "").strip()
        secondary_url = str(secondary or "").strip()
        if primary_url.startswith("https://arxiv.org/pdf/"):
            return primary_url
        if secondary_url.startswith("https://arxiv.org/pdf/"):
            return secondary_url
        if not primary_url:
            return secondary_url
        if not secondary_url:
            return primary_url
        return primary_url if len(primary_url) >= len(secondary_url) else secondary_url

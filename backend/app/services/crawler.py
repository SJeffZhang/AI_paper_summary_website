import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from app.core.config import settings

class Crawler:
    """
    Crawler Module to fetch daily papers from Hugging Face API.
    """
    def __init__(self, api_url: str = settings.HUGGINGFACE_API_URL):
        self.api_url = api_url

    def fetch_papers(self, fetch_date: str = None) -> List[Dict[str, Any]]:
        """
        Fetch papers for a specific date (YYYY-MM-DD). 
        If fetch_date is None, it defaults to yesterday (UTC+8).
        """
        if fetch_date is None:
            # Default to yesterday in UTC+8
            yesterday = datetime.now(timezone(timedelta(hours=8))) - timedelta(days=1)
            fetch_date = yesterday.strftime("%Y-%m-%d")

        params = {"date": fetch_date}
        try:
            response = requests.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return self._normalize_data(data, fallback_date=fetch_date)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching from HF API: {e}")
            raise e

    def _normalize_data(self, raw_data: List[Dict[str, Any]], fallback_date: str) -> List[Dict[str, Any]]:
        """
        Normalize HF API data into internal schema fields.
        Mapping:
        - arxiv_id: item["paper"]["id"]
        - title: item["paper"]["title"]
        - abstract: item["paper"]["summary"]
        - pdf_url: https://arxiv.org/pdf/{arxiv_id}.pdf
        - authors: list of names from item["paper"]["authors"]
        - upvotes: item["paper"]["upvotes"]
        - arxiv_publish_date: item["publishedAt"] -> YYYY-MM-DD
        """
        normalized = []
        for item in raw_data:
            paper_info = item.get("paper", {})
            arxiv_id = paper_info.get("id")
            if not arxiv_id:
                continue

            # Authors normalization
            authors = [a.get("name") for a in paper_info.get("authors", []) if a.get("name")]

            # Date normalization
            published_at = item.get("publishedAt", "")
            arxiv_publish_date = published_at.split("T")[0] if "T" in published_at else fallback_date

            normalized.append({
                "arxiv_id": arxiv_id,
                "title": paper_info.get("title", ""),
                "authors": authors,
                "abstract": paper_info.get("summary", ""),
                "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                "upvotes": paper_info.get("upvotes", 0),
                "arxiv_publish_date": arxiv_publish_date
            })
        return normalized

if __name__ == "__main__":
    # Quick standalone test
    crawler = Crawler()
    try:
        papers = crawler.fetch_papers()
        print(f"Successfully fetched {len(papers)} papers.")
        if papers:
            print(f"Top paper: {papers[0]['title']} (Upvotes: {papers[0]['upvotes']})")
    except Exception as e:
        print(f"Test failed: {e}")

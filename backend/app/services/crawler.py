import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from app.core.config import settings

class Crawler:
    """
    Crawler Module to fetch daily papers from Hugging Face API and arXiv.
    """
    ARXIV_CATEGORIES = ["cs.AI", "cs.CL", "cs.LG", "cs.CV", "cs.MA", "cs.IR"]
    ARXIV_API_URL = "http://export.arxiv.org/api/query"

    def __init__(self, hf_api_url: str = settings.HUGGINGFACE_API_URL):
        self.hf_api_url = hf_api_url

    def fetch_papers(self, fetch_date: str = None) -> List[Dict[str, Any]]:
        """
        Fetch papers from both HF and arXiv for a specific date.
        """
        if fetch_date is None:
            yesterday = datetime.now(timezone(timedelta(hours=8))) - timedelta(days=1)
            fetch_date = yesterday.strftime("%Y-%m-%d")

        print(f"Fetching papers for {fetch_date}...")
        hf_papers = self._fetch_hf_papers(fetch_date)
        arxiv_papers = self._fetch_arxiv_papers(fetch_date)
        
        # Merge by arxiv_id (HF papers take priority for metadata like upvotes)
        merged = {p["arxiv_id"]: p for p in arxiv_papers}
        for hp in hf_papers:
            if hp["arxiv_id"] in merged:
                merged[hp["arxiv_id"]].update(hp)
                merged[hp["arxiv_id"]]["is_hf_daily"] = True
            else:
                hp["is_hf_daily"] = True
                merged[hp["arxiv_id"]] = hp
                
        # Optional: Enrich top papers with citations and trending heuristics
        results = list(merged.values())
        return self.enrich_metadata(results)

    def enrich_metadata(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich papers with real citation data and REAL GitHub Trending status.
        """
        # 1. Fetch real-time GitHub Trending list (Daily)
        trending_repos = self._fetch_github_trending()
        print(f"Fetched {len(trending_repos)} trending repos from GitHub.")

        # 2. Enrich top papers (Directional mix or Global top)
        # To reduce bias, we ensure top papers from HF and those with code links are checked
        sorted_papers = sorted(papers, key=lambda x: x.get("upvotes", 0), reverse=True)
        top_candidates = sorted_papers[:150]
        
        print(f"Enriching metadata for top {len(top_candidates)} papers...")
        for p in top_candidates:
            # 2.1 Academic Influence (Semantic Scholar)
            try:
                ss_url = f"https://api.semanticscholar.org/graph/v1/paper/ARXIV:{p['arxiv_id']}"
                resp = requests.get(ss_url, params={"fields": "citationCount"}, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    p["citations"] = data.get("citationCount", 0)
                else:
                    p["citations"] = 0
            except:
                p["citations"] = 0

            # 2.2 REAL OS Trending Signal
            # Extract github repo from abstract and check if it's in the trending list
            p["is_trending"] = False
            abstract = p.get("abstract", "")
            import re
            github_links = re.findall(r"github\.com/([a-zA-Z0-9\-\._]+/[a-zA-Z0-9\-\._]+)", abstract)
            for link in github_links:
                # Clean link (remove trailing chars like . or ) )
                clean_link = link.split(' ')[0].split(')')[0].split('.')[0].strip('/')
                if clean_link.lower() in [r.lower() for r in trending_repos]:
                    p["is_trending"] = True
                    break
                
        # Initialize others
        for p in papers:
            if "citations" not in p:
                p["citations"] = 0
            if "is_trending" not in p:
                p["is_trending"] = False
        
        return papers

    def _fetch_github_trending(self) -> List[str]:
        """
        Scrape GitHub Trending page (Daily) to get trending repository names.
        """
        trending_repos = []
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            # Fetch daily trending
            resp = requests.get("https://github.com/trending", headers=headers, timeout=15)
            if resp.status_code == 200:
                # Simple regex parsing to avoid heavy bs4 dependency if possible, 
                # but standard practice would use an HTML parser.
                # GitHub Trending structure: <h2 class="h3 lh-condensed"><a href="/owner/repo">
                import re
                matches = re.findall(r'href="/([a-zA-Z0-9\-\._]+/[a-zA-Z0-9\-\._]+)"\s+data-view-component="true"\s+class="Link"', resp.text)
                # Filter out non-repo links like /trending/python
                for m in matches:
                    if "/" in m and not m.startswith("trending/"):
                        trending_repos.append(m)
        except Exception as e:
            print(f"Error fetching GitHub Trending: {e}")
        return trending_repos

    def _fetch_hf_papers(self, fetch_date: str) -> List[Dict[str, Any]]:
        params = {"date": fetch_date}
        try:
            response = requests.get(self.hf_api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return self._normalize_hf_data(data, fallback_date=fetch_date)
        except Exception as e:
            print(f"Error fetching from HF: {e}")
            return []

    def _fetch_arxiv_papers(self, fetch_date: str) -> List[Dict[str, Any]]:
        """
        Fetch papers from arXiv API for the 6 categories.
        """
        all_arxiv = []
        for cat in self.ARXIV_CATEGORIES:
            params = {
                "search_query": f"cat:{cat}",
                "start": 0,
                "max_results": 300,
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            }
            try:
                response = requests.get(self.ARXIV_API_URL, params=params, timeout=30)
                response.raise_for_status()
                papers = self._parse_arxiv_xml(response.text, fetch_date)
                all_arxiv.extend(papers)
            except Exception as e:
                print(f"Error fetching from arXiv {cat}: {e}")
        return all_arxiv

    def _parse_arxiv_xml(self, xml_text: str, target_date: str) -> List[Dict[str, Any]]:
        import xml.etree.ElementTree as ET
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}
        root = ET.fromstring(xml_text)
        papers = []
        for entry in root.findall('atom:entry', namespace):
            published = entry.find('atom:published', namespace).text
            pub_date = published.split("T")[0]
            
            if pub_date != target_date:
                continue
                
            arxiv_id = entry.find('atom:id', namespace).text.split('/')[-1]
            title = entry.find('atom:title', namespace).text.strip().replace('\n', ' ')
            summary = entry.find('atom:summary', namespace).text.strip().replace('\n', ' ')
            authors = [a.find('atom:name', namespace).text for a in entry.findall('atom:author', namespace)]
            
            papers.append({
                "arxiv_id": arxiv_id,
                "title": title,
                "title_en": title,
                "authors": authors,
                "abstract": summary,
                "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                "upvotes": 0,
                "arxiv_publish_date": pub_date,
                "is_hf_daily": False
            })
        return papers

    def _normalize_hf_data(self, raw_data: List[Dict[str, Any]], fallback_date: str) -> List[Dict[str, Any]]:
        """
        Normalize HF API data into internal schema fields.
        """
        normalized = []
        for item in raw_data:
            paper_info = item.get("paper", {})
            arxiv_id = paper_info.get("id")
            if not arxiv_id:
                continue

            authors = [a.get("name") for a in paper_info.get("authors", []) if a.get("name")]
            published_at = item.get("publishedAt", "")
            arxiv_publish_date = published_at.split("T")[0] if "T" in published_at else fallback_date
            title = paper_info.get("title", "")

            normalized.append({
                "arxiv_id": arxiv_id,
                "title": title,
                "title_en": title,
                "authors": authors,
                "abstract": paper_info.get("summary", ""),
                "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                "upvotes": paper_info.get("upvotes", 0),
                "arxiv_publish_date": arxiv_publish_date,
                "is_hf_daily": True
            })
        return normalized

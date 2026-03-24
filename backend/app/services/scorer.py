from typing import Any, Dict, Iterable, List

from app.core.specs import (
    FOCUS_THRESHOLD,
    PRACTITIONER_KEYWORDS,
    TAXONOMY_RULES,
    TOP_CONFERENCES,
    TOP_INSTITUTIONS,
    WATCHING_THRESHOLD,
    build_literal_boundary_pattern,
)


class Scorer:
    """
    Scoring Engine implementing the PRD v2.25 8-signal contract.
    """

    TOP_INSTITUTION_PATTERNS = [(name, build_literal_boundary_pattern(name)) for name in TOP_INSTITUTIONS]
    TOP_CONFERENCE_PATTERNS = [(name, build_literal_boundary_pattern(name)) for name in TOP_CONFERENCES]
    PRACTITIONER_PATTERNS = [(name, build_literal_boundary_pattern(name)) for name in PRACTITIONER_KEYWORDS]
    TAXONOMY_PATTERNS = [
        (direction, [(keyword, build_literal_boundary_pattern(keyword)) for keyword in keywords])
        for direction, keywords in TAXONOMY_RULES
    ]

    CODE_SIGNAL_PATTERNS = [
        build_literal_boundary_pattern("official code"),
        build_literal_boundary_pattern("code available"),
    ]

    def score_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        score = 0
        reasons: Dict[str, int] = {}

        if self._matches_top_institution(paper):
            score += 20
            reasons["top_org"] = 20

        if paper.get("is_hf_daily"):
            score += 30
            reasons["hf_recommend"] = 30

        upvotes = int(paper.get("upvotes", 0) or 0)
        upvote_score = 0
        if upvotes >= 100:
            upvote_score = 40
        elif upvotes >= 50:
            upvote_score = 20
        elif upvotes >= 10:
            upvote_score = 10
        if upvote_score:
            score += upvote_score
            reasons["community_popularity"] = upvote_score

        if self._matches_top_conference(paper):
            score += 25
            reasons["top_conf"] = 25

        if self._has_code_signal(paper):
            score += 20
            reasons["has_code"] = 20

        if self._matches_practitioner_keywords(paper):
            score += 15
            reasons["practitioner_relevance"] = 15

        citation_score = min(30, int(paper.get("citations", 0) or 0) * 2)
        if citation_score:
            score += citation_score
            reasons["academic_influence"] = citation_score

        if paper.get("is_trending"):
            score += 25
            reasons["os_trending"] = 25

        paper["score"] = score
        paper["score_reasons"] = reasons
        paper["direction"] = self._detect_direction(paper)
        paper["threshold_category"] = self._determine_threshold_category(score)
        return paper

    def _matches_top_institution(self, paper: Dict[str, Any]) -> bool:
        affiliations = " ".join(self._iter_affiliations(paper))
        if not affiliations:
            return False
        return any(pattern.search(affiliations) for _, pattern in self.TOP_INSTITUTION_PATTERNS)

    def _matches_top_conference(self, paper: Dict[str, Any]) -> bool:
        venue = paper.get("venue") or ""
        return any(pattern.search(venue) for _, pattern in self.TOP_CONFERENCE_PATTERNS)

    def _has_code_signal(self, paper: Dict[str, Any]) -> bool:
        text = self._title_abstract_text(paper)
        return "github.com" in text.lower() or any(pattern.search(text) for pattern in self.CODE_SIGNAL_PATTERNS)

    def _matches_practitioner_keywords(self, paper: Dict[str, Any]) -> bool:
        text = self._title_abstract_text(paper)
        return any(pattern.search(text) for _, pattern in self.PRACTITIONER_PATTERNS)

    def _detect_direction(self, paper: Dict[str, Any]) -> str:
        text = self._title_abstract_text(paper)
        for direction, patterns in self.TAXONOMY_PATTERNS:
            if any(pattern.search(text) for _, pattern in patterns):
                return direction
        return "Industry_Trends"

    @staticmethod
    def _determine_threshold_category(score: int) -> str:
        if score >= FOCUS_THRESHOLD:
            return "focus"
        if score >= WATCHING_THRESHOLD:
            return "watching"
        return "candidate"

    @staticmethod
    def _title_abstract_text(paper: Dict[str, Any]) -> str:
        return f"{paper.get('title_original', '')} {paper.get('abstract', '')}".strip()

    @staticmethod
    def _iter_affiliations(paper: Dict[str, Any]) -> Iterable[str]:
        for author in paper.get("authors", []) or []:
            if isinstance(author, dict):
                affiliation = author.get("affiliation") or ""
                if affiliation:
                    yield affiliation


if __name__ == "__main__":
    scorer = Scorer()
    sample_paper = {
        "title_original": "Agentic RAG with Quantization",
        "abstract": "Official code: github.com/example/repo. Designed for production inference.",
        "authors": [{"name": "Jane Doe", "affiliation": "OpenAI"}],
        "venue": "ICLR 2026",
        "upvotes": 120,
        "citations": 8,
        "is_hf_daily": True,
        "is_trending": True,
    }
    result = scorer.score_paper(sample_paper)
    print(result["score"])
    print(result["score_reasons"])
    print(result["direction"])
    print(result["threshold_category"])

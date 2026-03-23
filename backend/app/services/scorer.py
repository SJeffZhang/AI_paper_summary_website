from typing import List, Dict, Any
import re

class Scorer:
    """
    Scoring Engine for AI papers based on 8 signals as per PRD v2.0.
    """
    TOP_INSTITUTIONS = [
        "Google", "OpenAI", "Meta", "DeepMind", "Stanford", "MIT", "Berkeley", "CMU", 
        "Microsoft", "Tsinghua", "Peking", "DeepSeek", "Anthropic", "Mistral", "NVIDIA",
        "Harvard", "Oxford", "Cambridge", "ETH Zurich", "Toronto", "Washington",
        "Salesforce", "Amazon", "IBM", "Baidu", "Tencent", "Alibaba", "Huawei",
        "HKUST", "SJTU", "Fudan", "ZJU", "USTC", "UIUC", "Cornell", "Princeton", 
        "Caltech", "UCLA", "UCSD", "UT Austin"
    ]

    TOP_CONFERENCES = ["ICLR", "NeurIPS", "CVPR", "ICML", "AAAI", "IJCAI", "EMNLP", "ACL", "SIGGRAPH", "KDD"]

    PRACTITIONER_KEYWORDS = [
        "Deploy", "Inference", "Optimization", "Agent", "RAG", "Production", 
        "Efficiency", "Quantization", "Fine-tuning", "Scaling", "Serving", 
        "Framework", "Toolkit", "System", "Real-time", "Low-latency"
    ]

    TECH_DIRECTIONS = [
        "Agent", "推理", "训练优化", "检索与RAG", "多模态", "代码智能", 
        "视觉与图像生成", "视频生成", "安全与对齐", "语音与音频", 
        "机器人", "可解释性", "基准与评测", "数据工程", "行业动态"
    ]

    def score_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate scores based on 8 signals.
        """
        score = 0
        reasons = {}

        # 1. Institutional Background (+20)
        # We check in authors' affiliation if available, or just search in abstract/title metadata if possible.
        # Since standard arXiv data lacks clean affiliation, we might search in common patterns or just use a simplified check.
        # For now, searching in abstract for mention of top orgs.
        org_found = [org for org in self.TOP_INSTITUTIONS if org.lower() in paper.get("abstract", "").lower() or org.lower() in paper.get("title", "").lower()]
        if org_found:
            score += 20
            reasons["top_org"] = 20

        # 2. Community Recommendation (+30)
        # Assumed if it came from HF Daily Papers (this will be set by the crawler/orchestrator)
        if paper.get("is_hf_daily", False):
            score += 30
            reasons["hf_recommend"] = 30

        # 3. Community Popularity (0-40)
        upvotes = paper.get("upvotes", 0)
        upvote_score = 0
        if upvotes >= 100: upvote_score = 40
        elif upvotes >= 50: upvote_score = 20
        elif upvotes >= 10: upvote_score = 10
        
        if upvote_score > 0:
            score += upvote_score
            reasons["community_popularity"] = upvote_score

        # 4. Top Conference (+25)
        conf_found = [conf for conf in self.TOP_CONFERENCES if conf.lower() in paper.get("abstract", "").lower()]
        if conf_found:
            score += 25
            reasons["top_conf"] = 25

        # 5. Code Availability (+20)
        # Search for github links or common "code available" phrases
        abstract_lower = paper.get("abstract", "").lower()
        has_code_signal = (
            "github.com" in abstract_lower or 
            "code is available" in abstract_lower or
            "official implementation" in abstract_lower or
            paper.get("has_code", False)
        )
        if has_code_signal:
            score += 20
            reasons["has_code"] = 20

        # 6. Practitioner Relevance (+15)
        # Search for practitioner-oriented keywords indicating real-world utility
        practitioner_found = [kw for kw in self.PRACTITIONER_KEYWORDS if kw.lower() in abstract_lower or kw.lower() in paper.get("title", "").lower()]
        if practitioner_found:
            score += 15
            reasons["practitioner_relevance"] = 15

        # 7. Academic Influence (0-30) 
        # Best-effort: currently requires external enrichment (e.g. Semantic Scholar)
        # Placeholder logic based on citations field if present.
        citations = paper.get("citations", 0)
        citation_score = min(30, citations * 2) 
        if citation_score > 0:
            score += citation_score
            reasons["academic_influence"] = citation_score

        # 8. Open Source Popularity (+25)
        # Best-effort: currently requires external enrichment (e.g. GitHub Trending)
        if paper.get("is_trending", False):
            score += 25
            reasons["os_trending"] = 25

        paper["score"] = score
        paper["score_reasons"] = reasons
        
        # Determine category based on score thresholds (example)
        if score >= 80:
            paper["category"] = "focus"
        elif score >= 40:
            paper["category"] = "watching"
        else:
            paper["category"] = "candidate"
            
        # Determine Tech Direction (Naive keyword match for now)
        # This should ideally be handled by a Classifier Agent or strict keyword mapping
        paper["direction"] = self._detect_direction(paper)
        
        return paper

    def _detect_direction(self, paper: Dict[str, Any]) -> str:
        """
        Keyword-based direction detection for the 15 categories.
        """
        text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
        
        mapping = {
            "agent": "Agent",
            "reasoning": "推理",
            "thinking": "推理",
            "inference": "推理",
            "optimization": "训练优化",
            "training": "训练优化",
            "quantization": "训练优化",
            "distillation": "训练优化",
            "rag": "检索与RAG",
            "retrieval": "检索与RAG",
            "multimodal": "多模态",
            "vision": "视觉与图像生成",
            "image": "视觉与图像生成",
            "diffusion": "视觉与图像生成",
            "video": "视频生成",
            "safety": "安全与对齐",
            "alignment": "安全与对齐",
            "jailbreak": "安全与对齐",
            "speech": "语音与音频",
            "audio": "语音与音频",
            "robot": "机器人",
            "manipulation": "机器人",
            "interpretability": "可解释性",
            "benchmark": "基准与评测",
            "evaluation": "基准与评测",
            "dataset": "数据工程",
            "annotation": "数据工程",
            "code": "代码智能",
            "programming": "代码智能",
        }
        
        for kw, dir_name in mapping.items():
            if kw in text:
                return dir_name
                
        return "行业动态" # Default

if __name__ == "__main__":
    scorer = Scorer()
    test_paper = {
        "title": "Agentic RAG with Quantization",
        "abstract": "We present a framework for efficient Agent deployment. Available at github.com/test/repo. Presented at ICLR.",
        "upvotes": 60,
        "is_hf_daily": True
    }
    result = scorer.score_paper(test_paper)
    print(f"Score: {result['score']}")
    print(f"Reasons: {result['score_reasons']}")
    print(f"Category: {result['category']}")
    print(f"Direction: {result['direction']}")

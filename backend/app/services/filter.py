from typing import List, Dict, Any

class Filter:
    """
    Filter Module to select high-quality papers based on upvotes.
    """
    def __init__(self, top_n: int = 15):
        self.top_n = top_n

    def process(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort papers by upvotes descending and pick top_n.
        """
        if not papers:
            return []
            
        # Sort by upvotes (highest first)
        sorted_papers = sorted(papers, key=lambda x: x.get("upvotes", 0), reverse=True)
        
        # Take the top_n papers
        top_papers = sorted_papers[:self.top_n]
        
        return top_papers

if __name__ == "__main__":
    # Test sample data
    test_data = [
        {"arxiv_id": "1", "upvotes": 10},
        {"arxiv_id": "2", "upvotes": 50},
        {"arxiv_id": "3", "upvotes": 30},
    ]
    f = Filter(top_n=2)
    result = f.process(test_data)
    print(f"Filter result length: {len(result)}")
    print(f"Top paper ID: {result[0]['arxiv_id']}")

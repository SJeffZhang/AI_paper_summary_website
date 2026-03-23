import re
import requests
import os
from typing import List, Dict, Any, Optional
from app.core.config import settings

class AIProcessor:
    """
    AI Processor Module implementing the multi-agent workflow:
    Editor -> Writer -> Reviewer using Markdown-based contracts.
    """
    def __init__(self, api_key: str = settings.KIMI_API_KEY):
        self.api_key = api_key
        self.api_url = "https://api.moonshot.cn/v1/chat/completions" # Kimi API (Moonshot)
        
        # Determine paths relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompts_dir = os.path.join(current_dir, "..", "..", "prompts")
        
        # Load prompts
        with open(os.path.join(prompts_dir, "editor_prompt.md"), "r") as f:
            self.editor_prompt = f.read()
        with open(os.path.join(prompts_dir, "writer_prompt.md"), "r") as f:
            self.writer_prompt = f.read()
        with open(os.path.join(prompts_dir, "reviewer_prompt.md"), "r") as f:
            self.reviewer_prompt = f.read()

    def _call_llm(self, system_prompt: str, user_content: str, history: List[Dict[str, str]] = None) -> str:
        """
        Helper to call Kimi API.
        """
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": "moonshot-v1-8k",
            "messages": messages,
            "temperature": 0.3
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"LLM call failed: {e}")
            raise e

    def run_editor(self, candidate_papers: List[Dict[str, Any]], min_count: int = 3, max_count: int = 5) -> str:
        """
        Step 1: Editor Agent selects a specified range of papers and creates editorial briefs.
        """
        # Format papers into a readable Markdown list for the LLM
        input_text = f"# Candidate Papers (Please select between {min_count} and {max_count} papers)\n\n"
        for p in candidate_papers:
            input_text += f"## [{p['arxiv_id']}] {p['title']}\n"
            input_text += f"- **Upvotes**: {p['upvotes']}\n"
            input_text += f"- **Abstract**: {p['abstract']}\n\n"

        output = self._call_llm(self.editor_prompt, input_text)
        
        # Validation: Extract IDs and check against candidates
        selected_ids = re.findall(r"## 论文: \[(.*?)\]", output)
        
        # 1. Uniqueness check
        if len(selected_ids) != len(set(selected_ids)):
            raise ValueError(f"Editor produced duplicate IDs: {selected_ids}")

        candidate_ids = {p["arxiv_id"] for p in candidate_papers}
        
        # 2. Source & Count check
        valid_ids = [id_ for id_ in selected_ids if id_ in candidate_ids]
        if not (min_count <= len(valid_ids) <= max_count):
            raise ValueError(f"Editor selected {len(valid_ids)} papers, expected {min_count}-{max_count}. Output: {output[:200]}...")
            
        if len(valid_ids) != len(selected_ids):
            # Detect hallucinated IDs
            invalid_ids = set(selected_ids) - candidate_ids
            raise ValueError(f"Editor produced hallucinated IDs: {invalid_ids}")

        return output

    def run_writer(self, editor_brief: str, papers_metadata: List[Dict[str, Any]], history: List[Dict[str, str]] = None) -> str:
        """
        Step 2: Writer Agent writes the actual summaries.
        `history` can be used to pass previous attempts and reviewer feedback for retries.
        """
        # Extract metadata for selected papers only to reduce prompt size
        selected_ids = re.findall(r"## 论文: \[(.*?)\]", editor_brief)
        metadata_map = {p["arxiv_id"]: p for p in papers_metadata}
        
        context = "# Selected Papers Metadata\n\n"
        for sid in selected_ids:
            if sid in metadata_map:
                p = metadata_map[sid]
                context += f"## [{p['arxiv_id']}] {p['title']}\n"
                context += f"- **Abstract**: {p['abstract']}\n\n"

        user_input = f"{editor_brief}\n\n---\n\n{context}"
        output = self._call_llm(self.writer_prompt, user_input, history=history)
        
        # Validation: Consistency check (ID set must match & no duplicates)
        writer_ids = re.findall(r"## \[(.*?)\]", output)
        
        # 1. Uniqueness check for sections
        if len(writer_ids) != len(set(writer_ids)):
            raise ValueError(f"Writer output contains duplicate paper sections: {writer_ids}")
            
        # 2. Set equality for members
        if set(writer_ids) != set(selected_ids):
            raise ValueError(f"Writer output IDs {writer_ids} do not match Editor IDs {selected_ids}")
            
        return output

    def run_reviewer(self, writer_output: str) -> Dict[str, Any]:
        """
        Step 3: Reviewer Agent checks the summaries.
        Returns: {"status": "PASSED"|"REJECTED", "rejected_ids": [...]}
        """
        output = self._call_llm(self.reviewer_prompt, writer_output)
        
        # Parse result using regex
        conclusion_match = re.search(r"- \*\*整体结论\*\*: (PASSED|REJECTED)", output)
        rejected_ids_match = re.search(r"- \*\*拒绝名单\*\*: \[(.*?)\]", output)
        
        status = conclusion_match.group(1) if conclusion_match else "FAILED_TO_PARSE"
        rejected_ids = []
        if rejected_ids_match:
            ids_str = rejected_ids_match.group(1)
            rejected_ids = [i.strip() for i in ids_str.split(",") if i.strip()]
            
        # Semantic Validation for REJECTED as per PRD
        if status == "REJECTED":
            writer_ids = set(re.findall(r"## \[(.*?)\]", writer_output))
            rejected_set = set(rejected_ids)
            
            if not rejected_ids:
                raise ValueError("Reviewer returned REJECTED but the rejection list is empty.")
            
            if not rejected_set.issubset(writer_ids):
                invalid_ids = rejected_set - writer_ids
                raise ValueError(f"Reviewer returned rejection IDs that were not in the Writer's output: {invalid_ids}")

        return {
            "status": status,
            "rejected_ids": rejected_ids,
            "raw_output": output
        }

    def parse_final_summaries(self, writer_output: str, rejected_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Final step: Parse the Markdown from Writer and extract bilingual (CN/EN) structured data.
        Strict validation: All CN and EN fields must be present and non-empty.
        """
        # Split by ## [arxiv_id]
        segments = re.split(r"## \[(.*?)\]", writer_output)
        
        results = []
        rejected_set = set(rejected_ids)
        
        for i in range(1, len(segments), 2):
            arxiv_id = segments[i].strip()
            content = segments[i+1]
            
            if arxiv_id in rejected_set:
                continue
                
            # --- Extract CN Fields ---
            one_line_cn_match = re.search(r"- \*\*一句话总结\*\*: (.*)", content)
            highlights_cn_block = re.search(r"- \*\*核心亮点\*\*:([\s\S]*?)(?=- \*\*|$)", content)
            scenarios_cn_match = re.search(r"- \*\*应用场景\*\*: (.*)", content)
            
            # --- Extract EN Fields ---
            one_line_en_match = re.search(r"- \*\*One-line Summary\*\*: (.*)", content)
            highlights_en_block = re.search(r"- \*\*Core Highlights\*\*:([\s\S]*?)(?=- \*\*|$)", content)
            scenarios_en_match = re.search(r"- \*\*Application Scenarios\*\*: (.*)", content)
            
            # Strict Validation: Check all matches exist
            if not all([one_line_cn_match, highlights_cn_block, scenarios_cn_match, 
                       one_line_en_match, highlights_en_block, scenarios_en_match]):
                raise ValueError(f"Paper {arxiv_id} summary structure is incomplete (missing CN or EN sections).")

            # Extract and validate non-empty content
            one_line_cn = one_line_cn_match.group(1).strip()
            one_line_en = one_line_en_match.group(1).strip()
            scenarios_cn = scenarios_cn_match.group(1).strip()
            scenarios_en = scenarios_en_match.group(1).strip()
            
            highlights_cn = [h.strip() for h in re.findall(r"  - (.*)", highlights_cn_block.group(1)) if h.strip()]
            highlights_en = [h.strip() for h in re.findall(r"  - (.*)", highlights_en_block.group(1)) if h.strip()]

            if not all([one_line_cn, one_line_en, scenarios_cn, scenarios_en, highlights_cn, highlights_en]):
                raise ValueError(f"Paper {arxiv_id} has empty required CN or EN fields.")

            results.append({
                "arxiv_id": arxiv_id,
                "one_line_summary": one_line_cn,
                "one_line_summary_en": one_line_en,
                "core_highlights": highlights_cn,
                "core_highlights_en": highlights_en,
                "application_scenarios": scenarios_cn,
                "application_scenarios_en": scenarios_en
            })
            
        return results

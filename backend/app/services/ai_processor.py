import json
import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from openai import APIConnectionError, APIError, APITimeoutError, AuthenticationError, OpenAI, PermissionDeniedError, RateLimitError

from app.core.config import settings


class AIProcessor:
    """
    Multi-agent workflow:
    Editor -> Writer -> Reviewer
    """

    CJK_PATTERN = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF]")
    EDITOR_BLOCK_PATTERN = r"## 论文:\s*\[?(.*?)\]?\s*\n"
    WRITER_BLOCK_PATTERN = r"## \[(.*?)\]\s*\n"
    REVIEWER_ANCHOR_PATTERN = r"- \*\*整体结论\*\*:"

    def __init__(self, api_key: str = settings.KIMI_API_KEY):
        self.api_key = api_key
        self._clients: Dict[int, OpenAI] = {}

        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompts_dir = os.path.join(current_dir, "..", "..", "prompts")

        with open(os.path.join(prompts_dir, "editor_prompt.md"), "r", encoding="utf-8") as file:
            self.editor_prompt = file.read()
        with open(os.path.join(prompts_dir, "writer_prompt.md"), "r", encoding="utf-8") as file:
            self.writer_prompt = file.read()
        with open(os.path.join(prompts_dir, "reviewer_prompt.md"), "r", encoding="utf-8") as file:
            self.reviewer_prompt = file.read()

    def _call_llm(
        self,
        system_prompt: str,
        user_content: str,
        history: Optional[List[Dict[str, str]]] = None,
        *,
        response_format: Optional[Dict[str, str]] = None,
        longform: bool = False,
        temperature: float = 0.3,
    ) -> str:
        if not self.api_key.strip():
            raise RuntimeError("KIMI_API_KEY is not configured.")

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_content})

        request_timeout = (
            settings.KIMI_LONGFORM_TIMEOUT_SECONDS if longform else settings.KIMI_TIMEOUT_SECONDS
        )
        client = self._get_client(request_timeout)
        payload: Dict[str, Any] = {
            "model": settings.KIMI_MODEL,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        last_error: Optional[Exception] = None
        for attempt in range(max(1, int(settings.KIMI_MAX_RETRIES or 1))):
            try:
                completion = client.chat.completions.create(**payload)
                content = (completion.choices[0].message.content or "").strip()
                if not content:
                    raise ValueError("Kimi returned empty content.")
                return content
            except (AuthenticationError, PermissionDeniedError) as exc:
                raise RuntimeError("Kimi authentication failed. Check KIMI_API_KEY permissions and validity.") from exc
            except RateLimitError as exc:
                last_error = exc
                if attempt >= settings.KIMI_MAX_RETRIES - 1:
                    raise RuntimeError("Kimi rate limit exceeded after retries.") from exc
            except (APIConnectionError, APITimeoutError) as exc:
                last_error = exc
                if attempt >= settings.KIMI_MAX_RETRIES - 1:
                    timeout_label = "longform" if longform else "standard"
                    raise RuntimeError(f"Kimi {timeout_label} request timed out after retries.") from exc
            except APIError as exc:
                last_error = exc
                if attempt >= settings.KIMI_MAX_RETRIES - 1:
                    raise RuntimeError(f"Kimi request failed after retries: {exc}") from exc

        raise RuntimeError("Kimi request failed without a recoverable response.") from last_error

    def _get_client(self, timeout_seconds: int) -> OpenAI:
        client = self._clients.get(timeout_seconds)
        if client is None:
            client = OpenAI(
                api_key=self.api_key,
                base_url=settings.KIMI_BASE_URL,
                timeout=timeout_seconds,
                max_retries=0,
            )
            self._clients[timeout_seconds] = client
        return client

    def run_editor(self, locked_papers: Sequence[Dict[str, Any]], category: str) -> str:
        input_text = [f"# Locked {category.title()} Batch", "", "系统已锁定以下论文，请逐篇生成定调：", ""]
        for paper in locked_papers:
            input_text.extend(
                [
                    f"## [{paper['arxiv_id']}] {paper['title_original']}",
                    f"- 中文标题: {paper['title_zh']}",
                    f"- 分数: {paper['score']}",
                    f"- 方向: {paper['direction']}",
                    f"- 摘要: {paper['abstract']}",
                    "",
                ]
            )

        output = self._call_llm(self.editor_prompt, "\n".join(input_text), longform=True)
        records = self._split_markdown_blocks(output, self.EDITOR_BLOCK_PATTERN, "Editor")
        self._validate_exact_id_set(records, locked_papers, "Editor")

        for arxiv_id, block in records:
            angle = re.search(r"- \*\*写作角度\*\*: (.*?)\n", block)
            problem = re.search(r"- \*\*核心痛点\*\*: (.*?)\n", block)
            solution = re.search(r"- \*\*具体解法\*\*: (.*?)(?:\n|$)", block)
            if not all([angle, problem, solution]):
                raise ValueError(f"Editor block for {arxiv_id} is incomplete.")
            if not all(match.group(1).strip() for match in (angle, problem, solution)):
                raise ValueError(f"Editor block for {arxiv_id} contains empty required fields.")

        return output

    def localize_titles(self, papers: Sequence[Dict[str, Any]], batch_size: Optional[int] = None) -> Dict[str, str]:
        localized_titles: Dict[str, str] = {}
        batch_size = batch_size or max(1, int(settings.KIMI_TITLE_BATCH_SIZE or 1))

        for start in range(0, len(papers), batch_size):
            batch = papers[start : start + batch_size]
            prompt_lines = [
                "请把以下英文论文标题翻译成简洁、自然、面向中文技术读者的中文标题。",
                "保留模型名、数据集名、框架名、缩写和关键专有名词，不要添加编号或解释。",
                "每个中文标题都必须至少包含一个中文汉字，不能直接返回英文原题。",
                "只返回 JSON 对象，key 是 arxiv_id，value 是中文标题。",
                "",
            ]
            for paper in batch:
                prompt_lines.append(f"- {paper['arxiv_id']}: {paper['title_original']}")

            batch_titles = None
            retry_note = ""
            for attempt in range(3):
                try:
                    raw_output = self._call_llm(
                        system_prompt=(
                            "You translate AI paper titles into concise Chinese titles. "
                            "Each localized title must contain Chinese characters and must not be the original English title. "
                            "Return JSON only, without markdown fences or extra commentary."
                        ),
                        user_content="\n".join(prompt_lines + ([retry_note] if retry_note else [])),
                        response_format={"type": "json_object"},
                    )
                    batch_titles = self._parse_title_localization_output(raw_output, batch)
                    break
                except Exception as exc:
                    if attempt >= 2:
                        raise
                    retry_note = (
                        "上一次输出没有通过校验。"
                        f"错误原因：{exc}。"
                        "请重新返回 JSON，并确保每个标题都是真正的中文本地化标题。"
                    )

            if batch_titles is None:
                raise ValueError("Title localization failed after retries.")
            localized_titles.update(batch_titles)

        return localized_titles

    def run_writer(
        self,
        editor_brief: str,
        papers_metadata: Sequence[Dict[str, Any]],
        category: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        selected_ids = [arxiv_id for arxiv_id, _ in self._split_markdown_blocks(editor_brief, r"## 论文: \[(.*?)\]", "Editor")]
        metadata_map = {paper["arxiv_id"]: paper for paper in papers_metadata}

        context = [f"# Batch Type: {category}", "", "# Paper Metadata", ""]
        for arxiv_id in selected_ids:
            paper = metadata_map[arxiv_id]
            context.extend(
                [
                    f"## [{paper['arxiv_id']}] {paper['title_original']}",
                    f"- 中文标题: {paper['title_zh']}",
                    f"- 方向: {paper['direction']}",
                    f"- Venue: {paper.get('venue') or 'N/A'}",
                    f"- Abstract: {paper['abstract']}",
                    "",
                ]
            )

        output = self._call_llm(
            self.writer_prompt,
            f"{editor_brief}\n\n---\n\n" + "\n".join(context),
            history=history,
            longform=True,
        )
        records = self._split_markdown_blocks(output, self.WRITER_BLOCK_PATTERN, "Writer")
        self._validate_exact_id_set(records, papers_metadata, "Writer")
        return output

    def run_reviewer(self, writer_output: str) -> Dict[str, Any]:
        output = self._call_llm(self.reviewer_prompt, writer_output, longform=True).strip()
        normalized_output = self._strip_structured_output_wrappers(
            output,
            self.REVIEWER_ANCHOR_PATTERN,
            allow_preface=True,
        )

        full_match = re.fullmatch(
            r"- \*\*整体结论\*\*: (PASSED|REJECTED)\n- \*\*拒绝名单\*\*: \[(.*?)\]\s*",
            normalized_output,
        )
        if not full_match:
            raise ValueError("Reviewer output does not match the strict two-line contract.")

        status = full_match.group(1)
        rejected_ids = [item.strip() for item in full_match.group(2).split(",") if item.strip()]
        writer_ids = {arxiv_id for arxiv_id, _ in self._split_markdown_blocks(writer_output, self.WRITER_BLOCK_PATTERN, "Writer")}

        if status == "PASSED" and rejected_ids:
            raise ValueError("Reviewer returned PASSED with a non-empty rejection list.")
        if status == "REJECTED":
            if not rejected_ids:
                raise ValueError("Reviewer returned REJECTED with an empty rejection list.")
            invalid_ids = set(rejected_ids) - writer_ids
            if invalid_ids:
                raise ValueError(f"Reviewer returned invalid rejection IDs: {sorted(invalid_ids)}")

        return {"status": status, "rejected_ids": rejected_ids, "raw_output": normalized_output}

    def parse_final_summaries(
        self,
        writer_output: str,
        rejected_ids: Sequence[str],
        category: str,
    ) -> List[Dict[str, Any]]:
        records = self._split_markdown_blocks(writer_output, self.WRITER_BLOCK_PATTERN, "Writer")
        rejected_set = set(rejected_ids)
        results: List[Dict[str, Any]] = []

        for arxiv_id, block in records:
            if arxiv_id in rejected_set:
                continue

            one_line_cn_match = re.search(r"- \*\*一句话总结\*\*: (.*?)\n", block)
            one_line_en_match = re.search(r"- \*\*One-line Summary\*\*: (.*?)\n", block)
            highlights_cn_match = re.search(r"- \*\*核心亮点\*\*:\n(.*?)\n- \*\*Core Highlights\*\*:", block, re.S)
            highlights_en_match = re.search(r"- \*\*Core Highlights\*\*:\n(.*?)\n- \*\*应用场景\*\*:", block, re.S)
            scenarios_cn_match = re.search(r"- \*\*应用场景\*\*: (.*?)\n", block)
            scenarios_en_match = re.search(r"- \*\*Application Scenarios\*\*: (.*?)(?:\n|$)", block, re.S)

            if not all(
                [
                    one_line_cn_match,
                    one_line_en_match,
                    highlights_cn_match,
                    highlights_en_match,
                    scenarios_cn_match,
                    scenarios_en_match,
                ]
            ):
                raise ValueError(f"Writer block for {arxiv_id} is incomplete.")

            one_line_cn = one_line_cn_match.group(1).strip()
            one_line_en = one_line_en_match.group(1).strip()
            scenarios_cn = scenarios_cn_match.group(1).strip()
            scenarios_en = scenarios_en_match.group(1).strip()
            highlights_cn = self._extract_markdown_bullets(highlights_cn_match.group(1))
            highlights_en = self._extract_markdown_bullets(highlights_en_match.group(1))

            if not all([one_line_cn, one_line_en, scenarios_cn, scenarios_en, highlights_cn, highlights_en]):
                raise ValueError(f"Writer block for {arxiv_id} contains empty required content.")
            if len(highlights_cn) != len(highlights_en):
                raise ValueError(f"Writer block for {arxiv_id} has asymmetric CN/EN highlight counts.")

            min_highlights, max_highlights = (3, 5) if category == "focus" else (1, 2)
            if not (min_highlights <= len(highlights_cn) <= max_highlights):
                raise ValueError(
                    f"Writer block for {arxiv_id} has {len(highlights_cn)} highlights, expected {min_highlights}-{max_highlights}."
                )

            results.append(
                {
                    "arxiv_id": arxiv_id,
                    "one_line_summary": one_line_cn,
                    "one_line_summary_en": one_line_en,
                    "core_highlights": highlights_cn,
                    "core_highlights_en": highlights_en,
                    "application_scenarios": scenarios_cn,
                    "application_scenarios_en": scenarios_en,
                }
            )

        return results

    @staticmethod
    def _split_markdown_blocks(output: str, pattern: str, stage_name: str) -> List[Tuple[str, str]]:
        normalized = AIProcessor._strip_structured_output_wrappers(output, pattern)
        blocks = re.split(pattern, normalized)

        if not blocks or blocks[0].strip():
            raise ValueError(f"{stage_name} output failed zero-prefix validation.")
        if (len(blocks) - 1) % 2 != 0:
            raise ValueError(f"{stage_name} output produced malformed block pairs.")

        return [(blocks[index].strip(), blocks[index + 1]) for index in range(1, len(blocks), 2)]

    @staticmethod
    def _strip_structured_output_wrappers(raw_output: str, anchor_pattern: str, allow_preface: bool = False) -> str:
        normalized = raw_output.replace("\r\n", "\n").strip()
        stripped_fence = False

        if normalized.startswith("```"):
            normalized = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", normalized, count=1).strip()
            normalized = re.sub(r"\s*```$", "", normalized, count=1).strip()
            stripped_fence = True

        anchor_match = re.search(anchor_pattern, normalized, re.M)
        if anchor_match and (stripped_fence or allow_preface):
            normalized = normalized[anchor_match.start() :].strip()

        return normalized

    @staticmethod
    def _validate_exact_id_set(
        records: Sequence[Tuple[str, str]],
        papers: Sequence[Dict[str, Any]],
        stage_name: str,
    ) -> None:
        extracted_ids = [arxiv_id for arxiv_id, _ in records]
        expected_ids = [paper["arxiv_id"] for paper in papers]

        if len(records) != len(expected_ids):
            raise ValueError(f"{stage_name} output count mismatch: expected {len(expected_ids)}, got {len(records)}.")
        if len(extracted_ids) != len(set(extracted_ids)):
            raise ValueError(f"{stage_name} output contains duplicate IDs: {extracted_ids}")
        if set(extracted_ids) != set(expected_ids):
            raise ValueError(
                f"{stage_name} output IDs do not match input IDs. expected={sorted(expected_ids)} actual={sorted(extracted_ids)}"
            )

    @staticmethod
    def _extract_markdown_bullets(block: str) -> List[str]:
        return [item.strip() for item in re.findall(r"^\s*-\s+(.*?)\s*$", block, re.M) if item.strip()]

    @staticmethod
    def _parse_title_localization_output(raw_output: str, papers: Sequence[Dict[str, Any]]) -> Dict[str, str]:
        normalized = raw_output.strip()
        if normalized.startswith("```"):
            normalized = re.sub(r"^```(?:json)?\s*|\s*```$", "", normalized, flags=re.S).strip()

        try:
            parsed = json.loads(normalized)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Title localization output is not valid JSON: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ValueError("Title localization output must be a JSON object.")

        expected_ids = {paper["arxiv_id"] for paper in papers}
        actual_ids = set(parsed.keys())
        if actual_ids != expected_ids:
            raise ValueError(
                f"Title localization IDs mismatch. expected={sorted(expected_ids)} actual={sorted(actual_ids)}"
            )

        localized: Dict[str, str] = {}
        for paper in papers:
            title_zh = str(parsed[paper["arxiv_id"]]).strip()
            title_original = str(paper["title_original"]).strip()
            if not title_zh:
                raise ValueError(f"Localized title for {paper['arxiv_id']} is empty.")
            if not AIProcessor.CJK_PATTERN.search(title_zh):
                raise ValueError(f"Localized title for {paper['arxiv_id']} does not contain Chinese characters.")
            if title_zh.casefold() == title_original.casefold():
                raise ValueError(f"Localized title for {paper['arxiv_id']} is identical to the English original.")
            localized[paper["arxiv_id"]] = title_zh

        return localized

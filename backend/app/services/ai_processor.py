import json
import os
import re
import time
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from openai import APIConnectionError, APIError, APITimeoutError, AuthenticationError, OpenAI, PermissionDeniedError, RateLimitError

from app.core.config import settings


class StructuredOutputError(ValueError):
    def __init__(self, message: str, raw_output: str):
        super().__init__(message)
        self.raw_output = raw_output


class AIProcessor:
    """
    Multi-agent workflow:
    Editor -> Writer -> Reviewer
    """

    CJK_PATTERN = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF]")
    EDITOR_BLOCK_PATTERN = r"## 论文:\s*\[?(.*?)\]?\s*\n"
    WRITER_BLOCK_PATTERN = r"## \[(.*?)\]\s*\n"
    REVIEWER_ANCHOR_PATTERN = r"- \*\*整体结论\*\*:"

    def __init__(self, api_key: str | None = None):
        self.api_key = (api_key or settings.LLM_API_KEY).strip()
        self._clients: Dict[int, OpenAI] = {}
        self._next_request_at = 0.0

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
        temperature: Optional[float] = 1.0,
        max_tokens: Optional[int] = None,
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
        }
        normalized_temperature = self._normalize_temperature_for_model(settings.KIMI_MODEL, temperature)
        if normalized_temperature is not None:
            payload["temperature"] = normalized_temperature
        if response_format is not None:
            payload["response_format"] = response_format
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        max_attempts = self._max_retry_attempts(longform)
        last_error: Optional[Exception] = None
        for attempt in range(max_attempts):
            try:
                self._respect_request_interval(longform)
                if self._should_stream(longform=longform, response_format=response_format):
                    content = self._collect_streamed_content(client.chat.completions.create(stream=True, **payload))
                else:
                    completion = client.chat.completions.create(**payload)
                    content = self._extract_message_content(completion.choices[0].message)
                if not content:
                    last_error = ValueError("Kimi returned empty content.")
                    if attempt >= max_attempts - 1:
                        raise RuntimeError("Kimi returned empty content after retries.") from last_error
                    time.sleep(self._retry_backoff_seconds(attempt, longform, reason="empty"))
                    continue
                return content
            except (AuthenticationError, PermissionDeniedError) as exc:
                raise RuntimeError("Kimi authentication failed. Check KIMI_API_KEY permissions and validity.") from exc
            except RateLimitError as exc:
                last_error = exc
                if attempt >= max_attempts - 1:
                    raise RuntimeError("Kimi rate limit exceeded after retries.") from exc
                time.sleep(self._retry_backoff_seconds(attempt, longform, reason="rate_limit"))
            except (APIConnectionError, APITimeoutError) as exc:
                last_error = exc
                if attempt >= max_attempts - 1:
                    timeout_label = "longform" if longform else "standard"
                    raise RuntimeError(f"Kimi {timeout_label} request timed out after retries.") from exc
                time.sleep(self._retry_backoff_seconds(attempt, longform, reason="timeout"))
            except APIError as exc:
                last_error = exc
                if attempt >= max_attempts - 1:
                    raise RuntimeError(f"Kimi request failed after retries: {exc}") from exc
                time.sleep(self._retry_backoff_seconds(attempt, longform, reason="api_error"))

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

    @staticmethod
    def _should_stream(longform: bool, response_format: Optional[Dict[str, str]]) -> bool:
        # Kimi longform streaming can hang in production network conditions.
        # Keep non-streaming as the default stable path.
        return False

    @staticmethod
    def _retry_backoff_seconds(attempt: int, longform: bool, reason: str = "generic") -> int:
        if reason == "rate_limit":
            base_seconds = 20 if longform else 8
            max_seconds = 90 if longform else 30
            return min(base_seconds * (attempt + 1), max_seconds)

        base_seconds = 45 if longform else 12
        max_seconds = 120 if longform else 45
        return min(base_seconds * (attempt + 1), max_seconds)

    def _respect_request_interval(self, longform: bool) -> None:
        interval_seconds = self._minimum_request_interval_seconds(longform)
        now = time.monotonic()
        if self._next_request_at > now:
            time.sleep(self._next_request_at - now)
        self._next_request_at = time.monotonic() + interval_seconds

    @staticmethod
    def _minimum_request_interval_seconds(longform: bool) -> float:
        if longform:
            configured = settings.KIMI_LONGFORM_MIN_REQUEST_INTERVAL_SECONDS
        else:
            configured = settings.KIMI_MIN_REQUEST_INTERVAL_SECONDS
        return max(0.0, float(configured))

    @staticmethod
    def _normalize_temperature_for_model(model_name: str, temperature: Optional[float]) -> Optional[float]:
        if temperature is None:
            return None
        if str(model_name or "").strip().lower() == "kimi-k2.5":
            return 1.0
        return temperature

    @staticmethod
    def _max_retry_attempts(longform: bool) -> int:
        configured = max(1, int(settings.KIMI_MAX_RETRIES or 1))
        if not longform:
            return configured
        configured_longform = max(1, int(settings.KIMI_LONGFORM_MAX_RETRIES or configured))
        return min(configured, configured_longform)

    def run_editor(
        self,
        locked_papers: Sequence[Dict[str, Any]],
        category: str,
        retry_feedback: Optional[str] = None,
    ) -> str:
        input_text = [f"# Locked {category.title()} Batch", "", "系统已锁定以下论文，请逐篇生成定调：", ""]
        for paper in locked_papers:
            input_text.extend(
                [
                    f"## [{paper['arxiv_id']}] {paper['title_original']}",
                    f"- 中文标题: {paper['title_zh']}",
                    f"- 分数: {paper['score']}",
                    f"- 方向: {paper['direction']}",
                    f"- 摘要: {self._truncate_abstract(paper['abstract'])}",
                    "",
                ]
            )

        if retry_feedback:
            input_text.extend(
                [
                    "# 上一轮 Reviewer 反馈",
                    "",
                    retry_feedback.strip(),
                    "",
                    "请重新生成完整定调，重点修复 Reviewer 指出的薄弱点，同时保持严格输出格式。",
                    "",
                ]
            )

        output = self._call_llm(
            self.editor_prompt,
            "\n".join(input_text),
            longform=True,
            max_tokens=max(settings.KIMI_EDITOR_MAX_TOKENS, 1200 * len(locked_papers)),
        )
        try:
            self.parse_editor_records(output, locked_papers)
        except Exception as exc:
            raise StructuredOutputError(str(exc), raw_output=output) from exc
        return output

    @classmethod
    def build_fallback_title(cls, title_original: str) -> str:
        normalized = str(title_original or "").strip()
        if not normalized:
            return "待翻译标题"
        if cls.CJK_PATTERN.search(normalized):
            return normalized
        return f"待翻译：{normalized}"

    def localize_title(self, paper: Dict[str, Any]) -> str:
        return self.localize_titles([paper])[paper["arxiv_id"]]

    def localize_titles(
        self,
        papers: Sequence[Dict[str, Any]],
        batch_size: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
    ) -> Dict[str, str]:
        localized_titles: Dict[str, str] = {}
        pending: List[Dict[str, Any]] = []
        for paper in papers:
            arxiv_id = paper["arxiv_id"]
            current_title = str(paper.get("title_zh") or "").strip()
            original_title = str(paper["title_original"] or "").strip()

            has_fallback_prefix = current_title.startswith("待翻译")
            if (
                current_title
                and not has_fallback_prefix
                and self.CJK_PATTERN.search(current_title)
                and current_title.casefold() != original_title.casefold()
            ):
                localized_titles[arxiv_id] = current_title
            else:
                pending.append(paper)

        if not pending:
            return localized_titles

        effective_batch_size = max(1, int(batch_size or settings.KIMI_TITLE_BATCH_SIZE or 1))
        max_localize_attempts = max(1, int(settings.KIMI_TITLE_LOCALIZATION_ATTEMPTS or 1))
        total_batches = max(1, (len(pending) + effective_batch_size - 1) // effective_batch_size)
        for start in range(0, len(pending), effective_batch_size):
            batch = list(pending[start:start + effective_batch_size])
            if progress_callback is not None:
                progress_callback((start // effective_batch_size) + 1, total_batches, len(batch))
            prompt_lines = [
                "请把以下英文论文标题翻译成简洁、自然、面向中文技术读者的中文标题。",
                "保留模型名、数据集名、框架名、缩写和关键专有名词，不要添加编号或解释。",
                "每个中文标题都必须至少包含一个中文汉字，不能直接返回英文原题。",
                "只返回 JSON 对象，key 是 arxiv_id，value 是中文标题。",
                "",
            ]
            prompt_lines.extend(
                f"- {paper['arxiv_id']}: {str(paper['title_original'] or '').strip()}"
                for paper in batch
            )

            parsed_batch: Optional[Dict[str, str]] = None
            retry_note = ""
            for attempt in range(max_localize_attempts):
                try:
                    raw_output = self._call_llm(
                        system_prompt=(
                            "You translate AI paper titles into concise Chinese titles. "
                            "Each localized title must contain Chinese characters and must not be the original English title. "
                            "Return JSON only, without markdown fences or extra commentary."
                        ),
                        user_content="\n".join(prompt_lines + ([retry_note] if retry_note else [])),
                        response_format={"type": "json_object"},
                        max_tokens=max(1024, 256 * len(batch)),
                    )
                    parsed_batch = self._parse_title_localization_output(raw_output, batch)
                    break
                except Exception as exc:
                    if attempt >= max_localize_attempts - 1:
                        parsed_batch = None
                        break
                    retry_note = (
                        "上一次输出没有通过校验。"
                        f"错误原因：{exc}。"
                        "请重新返回 JSON，并确保标题是真正的中文本地化标题。"
                    )

            for paper in batch:
                arxiv_id = paper["arxiv_id"]
                original_title = str(paper["title_original"] or "").strip()
                if parsed_batch and arxiv_id in parsed_batch:
                    localized_titles[arxiv_id] = parsed_batch[arxiv_id]
                else:
                    localized_titles[arxiv_id] = self.build_fallback_title(original_title)

        return localized_titles

    def run_writer(
        self,
        editor_brief: str,
        papers_metadata: Sequence[Dict[str, Any]],
        category: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        selected_ids = [record["arxiv_id"] for record in self.parse_editor_records(editor_brief, papers_metadata)]
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
                    f"- Abstract: {self._truncate_abstract(paper['abstract'])}",
                    "",
                ]
            )

        output = self._call_llm(
            self.writer_prompt,
            f"{editor_brief}\n\n---\n\n" + "\n".join(context),
            history=history,
            longform=True,
            max_tokens=max(
                (
                    settings.KIMI_WRITER_FOCUS_MAX_TOKENS
                    if category == "focus"
                    else settings.KIMI_WRITER_WATCHING_MAX_TOKENS
                ),
                (1800 if category == "focus" else 1200) * len(selected_ids),
            ),
        )
        try:
            self.parse_writer_records(output, papers_metadata, category)
        except Exception as exc:
            raise StructuredOutputError(str(exc), raw_output=output) from exc
        return output

    def run_reviewer(self, writer_output: str) -> Dict[str, Any]:
        output = self._call_llm(
            self.reviewer_prompt,
            writer_output,
            longform=True,
            max_tokens=max(256, settings.KIMI_REVIEWER_MAX_TOKENS),
        ).strip()
        try:
            return self._parse_reviewer_result(output, writer_output)
        except Exception as exc:
            raise StructuredOutputError(str(exc), raw_output=output) from exc

    def repair_editor_output(
        self,
        raw_output: str,
        papers: Sequence[Dict[str, Any]],
        category: str,
    ) -> str:
        expected_ids = ", ".join(paper["arxiv_id"] for paper in papers)
        repaired = self._call_llm(
            system_prompt=(
                "You normalize malformed Editor markdown into a strict contract. "
                "Do not add or remove papers. Preserve facts from the original output."
            ),
            user_content=(
                f"批次类型: {category}\n"
                f"必须覆盖且仅覆盖这些 arxiv_id: [{expected_ids}]\n\n"
                "请把下面的原始输出修复成严格格式：\n"
                "## 论文: [arxiv_id]\n"
                "- **写作角度**: ...\n"
                "- **核心痛点**: ...\n"
                "- **具体解法**: ...\n\n"
                "原始输出如下：\n"
                f"{raw_output}"
            ),
            temperature=0.0,
            max_tokens=max(1200, 500 * len(papers)),
        )
        self.parse_editor_records(repaired, papers)
        return repaired

    def repair_writer_output(
        self,
        raw_output: str,
        papers_metadata: Sequence[Dict[str, Any]],
        category: str,
    ) -> str:
        expected_ids = ", ".join(paper["arxiv_id"] for paper in papers_metadata)
        highlights_rule = "3-5" if category == "focus" else "1-2"
        repaired = self._call_llm(
            system_prompt=(
                "You normalize malformed Writer markdown into a strict bilingual contract. "
                "Do not add or remove papers. Preserve original meaning."
            ),
            user_content=(
                f"批次类型: {category}\n"
                f"必须覆盖且仅覆盖这些 arxiv_id: [{expected_ids}]\n"
                f"每篇中英文亮点条数必须一致，且每篇亮点条数必须是 {highlights_rule} 条。\n\n"
                "严格输出结构：\n"
                "## [arxiv_id]\n"
                "- **一句话总结**: ...\n"
                "- **One-line Summary**: ...\n"
                "- **核心亮点**:\n"
                "- ...\n"
                "- **Core Highlights**:\n"
                "- ...\n"
                "- **应用场景**: ...\n"
                "- **Application Scenarios**: ...\n\n"
                "原始输出如下：\n"
                f"{raw_output}"
            ),
            temperature=0.0,
            max_tokens=max(1800, 800 * len(papers_metadata)),
        )
        self.parse_writer_records(repaired, papers_metadata, category)
        return repaired

    def repair_reviewer_output(self, raw_output: str, writer_output: str) -> Dict[str, Any]:
        writer_ids = ", ".join(arxiv_id for arxiv_id, _ in self._split_markdown_blocks(writer_output, self.WRITER_BLOCK_PATTERN, "Writer"))
        repaired = self._call_llm(
            system_prompt=(
                "You normalize malformed Reviewer markdown into the strict two-line contract. "
                "Use only IDs that exist in the writer batch."
            ),
            user_content=(
                f"Writer 批次的合法 arxiv_id: [{writer_ids}]\n\n"
                "严格输出两行：\n"
                "- **整体结论**: PASSED|REJECTED\n"
                "- **拒绝名单**: [id1, id2]\n"
                "如果是 PASSED，拒绝名单必须是 []。\n\n"
                "原始输出如下：\n"
                f"{raw_output}"
            ),
            temperature=0.0,
            max_tokens=400,
        )
        return self._parse_reviewer_result(repaired, writer_output)

    def parse_final_summaries(
        self,
        writer_output: str,
        rejected_ids: Sequence[str],
        category: str,
    ) -> List[Dict[str, Any]]:
        rejected_set = set(rejected_ids)
        return [
            {
                "arxiv_id": record["arxiv_id"],
                "one_line_summary": record["one_line_summary"],
                "one_line_summary_en": record["one_line_summary_en"],
                "core_highlights": record["core_highlights"],
                "core_highlights_en": record["core_highlights_en"],
                "application_scenarios": record["application_scenarios"],
                "application_scenarios_en": record["application_scenarios_en"],
            }
            for record in self.parse_writer_records(writer_output, None, category)
            if record["arxiv_id"] not in rejected_set
        ]

    def _parse_reviewer_result(self, output: str, writer_output: str) -> Dict[str, Any]:
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
        writer_ids = {
            arxiv_id
            for arxiv_id, _ in self._split_markdown_blocks(writer_output, self.WRITER_BLOCK_PATTERN, "Writer")
        }

        if status == "PASSED" and rejected_ids:
            raise ValueError("Reviewer returned PASSED with a non-empty rejection list.")
        if status == "REJECTED":
            if not rejected_ids:
                raise ValueError("Reviewer returned REJECTED with an empty rejection list.")
            invalid_ids = set(rejected_ids) - writer_ids
            if invalid_ids:
                raise ValueError(f"Reviewer returned invalid rejection IDs: {sorted(invalid_ids)}")

        return {"status": status, "rejected_ids": rejected_ids, "raw_output": normalized_output}

    def parse_editor_records(
        self,
        editor_output: str,
        papers: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        records = self._split_markdown_blocks(editor_output, self.EDITOR_BLOCK_PATTERN, "Editor")
        self._validate_exact_id_set(records, papers, "Editor")

        parsed_records: List[Dict[str, str]] = []
        for arxiv_id, block in records:
            angle = re.search(r"- \*\*写作角度\*\*: (.*?)\n", block)
            problem = re.search(r"- \*\*核心痛点\*\*: (.*?)\n", block)
            solution = re.search(r"- \*\*具体解法\*\*: (.*?)(?:\n|$)", block)
            if not all([angle, problem, solution]):
                raise ValueError(f"Editor block for {arxiv_id} is incomplete.")
            if not all(match.group(1).strip() for match in (angle, problem, solution)):
                raise ValueError(f"Editor block for {arxiv_id} contains empty required fields.")

            parsed_records.append(
                {
                    "arxiv_id": arxiv_id,
                    "writing_angle": angle.group(1).strip(),
                    "core_problem": problem.group(1).strip(),
                    "solution": solution.group(1).strip(),
                    "content": f"## 论文: [{arxiv_id}]\n{block.strip()}",
                }
            )

        return parsed_records

    def parse_writer_records(
        self,
        writer_output: str,
        papers_metadata: Optional[Sequence[Dict[str, Any]]],
        category: str,
    ) -> List[Dict[str, Any]]:
        records = self._split_markdown_blocks(writer_output, self.WRITER_BLOCK_PATTERN, "Writer")
        if papers_metadata is not None:
            self._validate_exact_id_set(records, papers_metadata, "Writer")

        parsed_records: List[Dict[str, Any]] = []
        for arxiv_id, block in records:
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

            parsed_records.append(
                {
                    "arxiv_id": arxiv_id,
                    "one_line_summary": one_line_cn,
                    "one_line_summary_en": one_line_en,
                    "core_highlights": highlights_cn,
                    "core_highlights_en": highlights_en,
                    "application_scenarios": scenarios_cn,
                    "application_scenarios_en": scenarios_en,
                    "content": f"## [{arxiv_id}]\n{block.strip()}",
                }
            )

        return parsed_records

    @staticmethod
    def _split_markdown_blocks(output: str, pattern: str, stage_name: str) -> List[Tuple[str, str]]:
        normalized = AIProcessor._strip_structured_output_wrappers(output, pattern)
        blocks = re.split(pattern, normalized)

        if not blocks or blocks[0].strip():
            raise ValueError(f"{stage_name} output failed zero-prefix validation.")
        if (len(blocks) - 1) % 2 != 0:
            raise ValueError(f"{stage_name} output produced malformed block pairs.")

        return [
            (AIProcessor._normalize_record_id(blocks[index]), blocks[index + 1])
            for index in range(1, len(blocks), 2)
        ]

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
    def _extract_message_content(message: Any) -> str:
        def normalize_text(value: str) -> str:
            return AIProcessor._strip_reasoning_prefix(value)

        content = getattr(message, "content", None)
        if isinstance(content, str):
            normalized = normalize_text(content)
            if normalized:
                return normalized
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text" and item.get("text"):
                        parts.append(str(item["text"]).strip())
                else:
                    item_type = getattr(item, "type", None)
                    item_text = getattr(item, "text", None)
                    if item_type == "text" and item_text:
                        parts.append(normalize_text(str(item_text)))
            normalized = normalize_text("\n".join(part for part in parts if part))
            if normalized:
                return normalized
        if isinstance(content, SimpleNamespace):
            text = getattr(content, "text", None)
            normalized = normalize_text(str(text)) if text else ""
            if normalized:
                return normalized

        # Moonshot/Kimi may occasionally return empty `content` while placing
        # the effective text payload in `reasoning_content`.
        reasoning_content = getattr(message, "reasoning_content", None)
        if isinstance(reasoning_content, str):
            return normalize_text(reasoning_content)
        if isinstance(reasoning_content, list):
            parts: List[str] = []
            for item in reasoning_content:
                if isinstance(item, dict):
                    if item.get("type") == "text" and item.get("text"):
                        parts.append(normalize_text(str(item["text"])))
                else:
                    item_text = getattr(item, "text", None)
                    if item_text:
                        parts.append(normalize_text(str(item_text)))
            return normalize_text("\n".join(part for part in parts if part))

        return ""

    @staticmethod
    def _strip_reasoning_prefix(text: str) -> str:
        normalized = str(text or "").strip()
        if not normalized:
            return ""
        # MiniMax models may prepend internal reasoning blocks.
        normalized = re.sub(r"<think>[\s\S]*?</think>\s*", "", normalized, flags=re.IGNORECASE)
        return normalized.strip()

    @staticmethod
    def _extract_stream_delta_content(delta: Any) -> str:
        content = getattr(delta, "content", None)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text" and item.get("text"):
                        parts.append(str(item["text"]))
                else:
                    item_type = getattr(item, "type", None)
                    item_text = getattr(item, "text", None)
                    if item_type == "text" and item_text:
                        parts.append(str(item_text))
            return "".join(parts)
        return ""

    @classmethod
    def _collect_streamed_content(cls, stream: Any) -> str:
        parts: List[str] = []
        for chunk in stream:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue
            text = cls._extract_stream_delta_content(delta)
            if text:
                parts.append(text)
        return "".join(parts).strip()

    @staticmethod
    def _normalize_record_id(raw_id: str) -> str:
        normalized = str(raw_id or "").strip()
        normalized = normalized.strip("[]")
        normalized = re.sub(r"^(?:arxiv_id|paper_id|id)\s*=\s*", "", normalized, flags=re.I)
        normalized = normalized.strip()
        if not normalized:
            raise ValueError("Structured output block contains an empty paper ID.")
        return normalized

    @staticmethod
    def _truncate_abstract(abstract: str, limit: int = 1600) -> str:
        normalized = " ".join(str(abstract or "").split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 1].rstrip() + "…"

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

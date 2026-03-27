import pytest
from types import SimpleNamespace

from app.services.ai_processor import AIProcessor


def test_parse_title_localization_output_requires_chinese_and_different_title():
    papers = [{"arxiv_id": "2503.00001", "title_original": "Agentic RAG for Production Inference"}]

    with pytest.raises(ValueError, match="Chinese characters"):
        AIProcessor._parse_title_localization_output('{"2503.00001": "Agentic RAG for Production Inference CN"}', papers)

    with pytest.raises(ValueError, match="Chinese characters"):
        AIProcessor._parse_title_localization_output('{"2503.00001": "Agentic RAG for Production Inference"}', papers)

    parsed = AIProcessor._parse_title_localization_output('{"2503.00001": "面向生产推理的智能体 RAG"}', papers)
    assert parsed == {"2503.00001": "面向生产推理的智能体 RAG"}


def test_localize_titles_falls_back_per_paper_when_llm_keeps_failing(monkeypatch):
    processor = AIProcessor(api_key="test-key")
    papers = [
        {"arxiv_id": "2503.00001", "title_original": "Reliable Agent Planning"},
        {"arxiv_id": "2503.00002", "title_original": "Vision Model with 中文"},
    ]

    monkeypatch.setattr(
        processor,
        "_call_llm",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("kimi timeout")),
    )

    localized = processor.localize_titles(papers)

    assert localized["2503.00001"] == "待翻译：Reliable Agent Planning"
    assert localized["2503.00002"] == "Vision Model with 中文"


def test_retry_backoff_seconds_scales_for_standard_and_longform_requests():
    assert AIProcessor._retry_backoff_seconds(0, longform=False) == 15
    assert AIProcessor._retry_backoff_seconds(2, longform=False) == 45
    assert AIProcessor._retry_backoff_seconds(0, longform=True) == 60
    assert AIProcessor._retry_backoff_seconds(4, longform=True) == 180


def test_minimum_request_interval_seconds_distinguishes_longform():
    assert AIProcessor._minimum_request_interval_seconds(longform=False) == 5
    assert AIProcessor._minimum_request_interval_seconds(longform=True) == 20


def test_split_markdown_blocks_enforces_zero_prefix():
    with pytest.raises(ValueError, match="zero-prefix"):
        AIProcessor._split_markdown_blocks(
            "unexpected preface\n## [2503.00001]\n- **一句话总结**: demo",
            r"## \[(.*?)\]",
            "Writer",
        )


def test_strip_structured_output_wrappers_removes_code_fence_and_preface():
    normalized = AIProcessor._strip_structured_output_wrappers(
        "```markdown\n下面是结果。\n## [2503.00001]\n- **一句话总结**: demo\n```",
        r"## \[",
    )
    assert normalized.startswith("## [2503.00001]")


def test_extract_message_content_supports_segment_lists():
    message = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="第一段"),
            SimpleNamespace(type="input_image", text=None),
            {"type": "text", "text": "第二段"},
        ]
    )

    assert AIProcessor._extract_message_content(message) == "第一段\n第二段"


def test_collect_streamed_content_joins_delta_text():
    stream = [
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="第一段 "))]),
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(
                        content=[
                            SimpleNamespace(type="text", text="第二段"),
                            {"type": "text", "text": "第三段"},
                        ]
                    )
                )
            ]
        ),
    ]

    assert AIProcessor._collect_streamed_content(stream) == "第一段 第二段第三段"


def test_split_markdown_blocks_supports_bracketless_editor_headers():
    records = AIProcessor._split_markdown_blocks(
        "## 论文: 2503.00001\n- **写作角度**: demo\n- **核心痛点**: demo\n- **具体解法**: demo\n",
        AIProcessor.EDITOR_BLOCK_PATTERN,
        "Editor",
    )
    assert records[0][0] == "2503.00001"


def test_split_markdown_blocks_normalizes_prefixed_editor_headers():
    records = AIProcessor._split_markdown_blocks(
        "## 论文: [arxiv_id=2602.07274]\n- **写作角度**: demo\n- **核心痛点**: demo\n- **具体解法**: demo\n",
        AIProcessor.EDITOR_BLOCK_PATTERN,
        "Editor",
    )
    assert records[0][0] == "2602.07274"


def test_parse_editor_records_returns_structured_trace_blocks():
    processor = AIProcessor(api_key="test-key")
    editor_output = (
        "## 论文: 2503.00001\n"
        "- **写作角度**: 从生产落地角度切入。\n"
        "- **核心痛点**: 线上检索增强链路缺少稳定编排。\n"
        "- **具体解法**: 用统一 Agent 流程连接检索与推理。\n"
    )

    records = processor.parse_editor_records(
        editor_output,
        [{"arxiv_id": "2503.00001"}],
    )

    assert records[0]["writing_angle"] == "从生产落地角度切入。"
    assert records[0]["content"].startswith("## 论文: [2503.00001]")


def test_run_writer_accepts_prefixed_editor_headers(monkeypatch):
    processor = AIProcessor(api_key="test-key")
    editor_brief = (
        "## 论文: [arxiv_id=2503.00001]\n"
        "- **写作角度**: demo\n"
        "- **核心痛点**: demo\n"
        "- **具体解法**: demo\n"
    )
    papers_metadata = [
        {
            "arxiv_id": "2503.00001",
            "title_zh": "中文标题",
            "title_original": "Original Title",
            "direction": "Agent",
            "venue": "ICLR 2026",
            "abstract": "demo abstract",
        }
    ]

    monkeypatch.setattr(
        processor,
        "_call_llm",
        lambda system_prompt, user_content, history=None, **kwargs: (
            "## [2503.00001]\n"
            "- **一句话总结**: 中文总结\n"
            "- **One-line Summary**: English summary\n"
            "- **核心亮点**:\n"
            "- 亮点一\n- 亮点二\n- 亮点三\n"
            "- **Core Highlights**:\n"
            "- Point 1\n- Point 2\n- Point 3\n"
            "- **应用场景**: 中文场景\n"
            "- **Application Scenarios**: English scenario\n"
        ),
    )

    output = processor.run_writer(editor_brief, papers_metadata, "focus")
    assert "## [2503.00001]" in output


def test_run_editor_uses_large_longform_token_budget(monkeypatch):
    processor = AIProcessor(api_key="test-key")
    captured = {}

    def fake_call_llm(system_prompt, user_content, history=None, **kwargs):
        captured["kwargs"] = kwargs
        return (
            "## 论文: [2503.00001]\n"
            "- **写作角度**: demo\n"
            "- **核心痛点**: demo\n"
            "- **具体解法**: demo\n"
        )

    monkeypatch.setattr(processor, "_call_llm", fake_call_llm)

    processor.run_editor(
        [
            {
                "arxiv_id": "2503.00001",
                "title_zh": "中文标题",
                "title_original": "Original Title",
                "score": 88,
                "direction": "Agent",
                "abstract": "demo abstract",
            }
        ],
        "focus",
    )

    assert captured["kwargs"]["longform"] is True
    assert captured["kwargs"]["max_tokens"] >= 4096


def test_run_writer_accepts_bracketless_editor_headers(monkeypatch):
    processor = AIProcessor(api_key="test-key")
    editor_brief = (
        "## 论文: 2503.00001\n"
        "- **写作角度**: demo\n"
        "- **核心痛点**: demo\n"
        "- **具体解法**: demo\n"
    )
    papers_metadata = [
        {
            "arxiv_id": "2503.00001",
            "title_zh": "中文标题",
            "title_original": "Original Title",
            "direction": "Agent",
            "venue": "ICLR 2026",
            "abstract": "demo abstract",
        }
    ]

    monkeypatch.setattr(
        processor,
        "_call_llm",
        lambda system_prompt, user_content, history=None, **kwargs: (
            "## [2503.00001]\n"
            "- **一句话总结**: 中文总结\n"
            "- **One-line Summary**: English summary\n"
            "- **核心亮点**:\n"
            "- 亮点一\n- 亮点二\n- 亮点三\n"
            "- **Core Highlights**:\n"
            "- Point 1\n- Point 2\n- Point 3\n"
            "- **应用场景**: 中文场景\n"
            "- **Application Scenarios**: English scenario\n"
        ),
    )

    output = processor.run_writer(editor_brief, papers_metadata, "focus")
    assert "## [2503.00001]" in output


def test_run_reviewer_uses_large_longform_token_budget(monkeypatch):
    processor = AIProcessor(api_key="test-key")
    captured = {}

    def fake_call_llm(system_prompt, user_content, history=None, **kwargs):
        captured["kwargs"] = kwargs
        return "- **整体结论**: PASSED\n- **拒绝名单**: []"

    monkeypatch.setattr(processor, "_call_llm", fake_call_llm)

    result = processor.run_reviewer(
        "## [2503.00001]\n"
        "- **一句话总结**: 中文总结\n"
        "- **One-line Summary**: English summary\n"
        "- **核心亮点**:\n"
        "- 亮点一\n- 亮点二\n- 亮点三\n"
        "- **Core Highlights**:\n"
        "- Point 1\n- Point 2\n- Point 3\n"
        "- **应用场景**: 中文场景\n"
        "- **Application Scenarios**: English scenario\n"
    )

    assert result["status"] == "PASSED"
    assert captured["kwargs"]["longform"] is True
    assert captured["kwargs"]["max_tokens"] >= 2048


def test_parse_writer_records_returns_trace_content_and_summary_fields():
    processor = AIProcessor(api_key="test-key")
    writer_output = (
        "## [2503.00001]\n"
        "- **一句话总结**: 中文总结\n"
        "- **One-line Summary**: English summary\n"
        "- **核心亮点**:\n"
        "- 亮点一\n- 亮点二\n- 亮点三\n"
        "- **Core Highlights**:\n"
        "- Point 1\n- Point 2\n- Point 3\n"
        "- **应用场景**: 中文场景\n"
        "- **Application Scenarios**: English scenario\n"
    )

    records = processor.parse_writer_records(
        writer_output,
        [{"arxiv_id": "2503.00001"}],
        "focus",
    )

    assert records[0]["one_line_summary"] == "中文总结"
    assert records[0]["content"].startswith("## [2503.00001]")


def test_run_reviewer_rejects_invalid_ids(monkeypatch):
    processor = AIProcessor(api_key="test-key")
    writer_output = (
        "## [2503.00001]\n"
        "- **一句话总结**: 中文总结\n"
        "- **One-line Summary**: English summary\n"
        "- **核心亮点**:\n"
        "- 亮点一\n- 亮点二\n- 亮点三\n"
        "- **Core Highlights**:\n"
        "- Point 1\n- Point 2\n- Point 3\n"
        "- **应用场景**: 中文场景\n"
        "- **Application Scenarios**: English scenario\n"
    )

    monkeypatch.setattr(
        processor,
        "_call_llm",
        lambda system_prompt, user_content, history=None, **kwargs: "- **整体结论**: REJECTED\n- **拒绝名单**: [2503.99999]",
    )

    with pytest.raises(ValueError, match="invalid rejection IDs"):
        processor.run_reviewer(writer_output)


def test_run_reviewer_strips_wrapper_noise(monkeypatch):
    processor = AIProcessor(api_key="test-key")
    writer_output = (
        "## [2503.00001]\n"
        "- **一句话总结**: 中文总结\n"
        "- **One-line Summary**: English summary\n"
        "- **核心亮点**:\n"
        "- 亮点一\n- 亮点二\n- 亮点三\n"
        "- **Core Highlights**:\n"
        "- Point 1\n- Point 2\n- Point 3\n"
        "- **应用场景**: 中文场景\n"
        "- **Application Scenarios**: English scenario\n"
    )

    monkeypatch.setattr(
        processor,
        "_call_llm",
        lambda system_prompt, user_content, history=None, **kwargs: (
            "```markdown\n说明：如下。\n- **整体结论**: PASSED\n- **拒绝名单**: []\n```"
        ),
    )

    result = processor.run_reviewer(writer_output)
    assert result["status"] == "PASSED"
    assert result["rejected_ids"] == []


def test_parse_final_summaries_validates_highlight_symmetry():
    writer_output = (
        "## [2503.00001]\n"
        "- **一句话总结**: 中文总结\n"
        "- **One-line Summary**: English summary\n"
        "- **核心亮点**:\n"
        "- 亮点一\n- 亮点二\n- 亮点三\n"
        "- **Core Highlights**:\n"
        "- Point 1\n- Point 2\n"
        "- **应用场景**: 中文场景\n"
        "- **Application Scenarios**: English scenario\n"
    )

    with pytest.raises(ValueError, match="asymmetric"):
        AIProcessor(api_key="test-key").parse_final_summaries(writer_output, [], "focus")


def test_call_llm_retries_empty_content(monkeypatch):
    processor = AIProcessor(api_key="test-key")
    calls = {"count": 0}

    class FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    calls["count"] += 1
                    if calls["count"] == 1:
                        return SimpleNamespace(
                            choices=[SimpleNamespace(message=SimpleNamespace(content=""))]
                        )
                    return SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
                    )

    monkeypatch.setattr(processor, "_get_client", lambda timeout_seconds: FakeClient())
    monkeypatch.setattr(processor, "_respect_request_interval", lambda longform: None)
    monkeypatch.setattr(processor, "_retry_backoff_seconds", lambda attempt, longform: 0)

    assert processor._call_llm("system", "user") == "ok"
    assert calls["count"] == 2


def test_call_llm_uses_streaming_for_longform(monkeypatch):
    processor = AIProcessor(api_key="test-key")

    class FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    assert kwargs["stream"] is True
                    return [
                        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="hello "))]),
                        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="world"))]),
                    ]

    monkeypatch.setattr(processor, "_get_client", lambda timeout_seconds: FakeClient())
    monkeypatch.setattr(processor, "_respect_request_interval", lambda longform: None)

    assert processor._call_llm("system", "user", longform=True) == "hello world"

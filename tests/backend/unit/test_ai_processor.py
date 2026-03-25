import pytest

from app.services.ai_processor import AIProcessor


def test_parse_title_localization_output_requires_chinese_and_different_title():
    papers = [{"arxiv_id": "2503.00001", "title_original": "Agentic RAG for Production Inference"}]

    with pytest.raises(ValueError, match="Chinese characters"):
        AIProcessor._parse_title_localization_output('{"2503.00001": "Agentic RAG for Production Inference CN"}', papers)

    with pytest.raises(ValueError, match="Chinese characters"):
        AIProcessor._parse_title_localization_output('{"2503.00001": "Agentic RAG for Production Inference"}', papers)

    parsed = AIProcessor._parse_title_localization_output('{"2503.00001": "面向生产推理的智能体 RAG"}', papers)
    assert parsed == {"2503.00001": "面向生产推理的智能体 RAG"}


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


def test_split_markdown_blocks_supports_bracketless_editor_headers():
    records = AIProcessor._split_markdown_blocks(
        "## 论文: 2503.00001\n- **写作角度**: demo\n- **核心痛点**: demo\n- **具体解法**: demo\n",
        AIProcessor.EDITOR_BLOCK_PATTERN,
        "Editor",
    )
    assert records[0][0] == "2503.00001"


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


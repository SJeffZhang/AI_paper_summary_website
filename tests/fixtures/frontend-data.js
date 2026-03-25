export const paperListPayload = {
  total: 4,
  items: [
    {
      id: 1,
      arxiv_id: '2503.01001',
      title_zh: '中文焦点标题',
      title_original: 'Focus Title Original',
      score: 95,
      category: 'focus',
      candidate_reason: null,
      direction: 'Agent',
      issue_date: '2026-03-23',
      score_reasons: { hf_recommend: 30 },
      one_line_summary: '焦点中文总结',
      one_line_summary_en: 'Focus English Summary'
    },
    {
      id: 2,
      arxiv_id: '2503.01002',
      title_zh: '中文观察标题',
      title_original: 'Watching Title Original',
      score: 68,
      category: 'watching',
      candidate_reason: null,
      direction: 'RAG',
      issue_date: '2026-03-23',
      score_reasons: { community_popularity: 20 },
      one_line_summary: '观察中文总结',
      one_line_summary_en: 'Watching English Summary'
    },
    {
      id: 3,
      arxiv_id: '2503.01003',
      title_zh: '中文候选标题',
      title_original: 'Candidate Title Original',
      score: 42,
      category: 'candidate',
      candidate_reason: 'low_score',
      direction: 'Benchmarking',
      issue_date: '2026-03-23',
      score_reasons: {
        top_org: 20,
        top_conf: 25,
        academic_influence: 12,
        has_code: 15
      },
      one_line_summary: null,
      one_line_summary_en: null
    },
    {
      id: 4,
      arxiv_id: '2503.01004',
      title_zh: '最新候选标题',
      title_original: 'Latest Candidate Title Original',
      score: 49,
      category: 'candidate',
      candidate_reason: 'capacity_overflow',
      direction: 'Reasoning',
      issue_date: '2026-03-23',
      score_reasons: { community_popularity: 10 },
      one_line_summary: null,
      one_line_summary_en: null
    }
  ]
}

export const focusDetail = {
  id: 1,
  arxiv_id: '2503.01001',
  title_zh: '中文焦点标题',
  title_original: 'Focus Title Original',
  score: 95,
  category: 'focus',
  candidate_reason: null,
  direction: 'Agent',
  issue_date: '2026-03-23',
  authors: [{ name: 'Alice', affiliation: 'OpenAI' }],
  venue: 'ICLR 2026',
  abstract: 'Focus abstract',
  pdf_url: 'https://arxiv.org/pdf/2503.01001.pdf',
  arxiv_publish_date: '2026-03-20',
  score_reasons: { hf_recommend: 30 },
  one_line_summary: '焦点中文总结',
  one_line_summary_en: 'Focus English Summary',
  core_highlights: ['亮点一', '亮点二', '亮点三'],
  core_highlights_en: ['Point 1', 'Point 2', 'Point 3'],
  application_scenarios: '企业应用',
  application_scenarios_en: 'Enterprise use'
}

export const candidateDetail = {
  id: 4,
  arxiv_id: '2503.01004',
  title_zh: '最新候选标题',
  title_original: 'Latest Candidate Title Original',
  score: 49,
  category: 'candidate',
  candidate_reason: 'capacity_overflow',
  direction: 'Reasoning',
  issue_date: '2026-03-23',
  authors: [{ name: 'Dave', affiliation: 'Google' }],
  venue: 'NeurIPS 2025',
  abstract: 'Latest candidate abstract',
  pdf_url: 'https://arxiv.org/pdf/2503.01004.pdf',
  arxiv_publish_date: '2026-03-19',
  score_reasons: {
    community_popularity: 10,
    has_code: 15,
    top_org: 20
  },
  one_line_summary: null,
  one_line_summary_en: null,
  core_highlights: null,
  core_highlights_en: null,
  application_scenarios: null,
  application_scenarios_en: null
}

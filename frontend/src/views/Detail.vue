<template>
  <div class="detail-page">
    <button class="secondary-button back-button" type="button" @click="$router.back()">
      {{ lang === 'cn' ? '返回' : 'Back' }}
    </button>

    <div v-if="loading" class="detail-loading">
      <el-skeleton :rows="12" animated />
    </div>

    <div v-else-if="!paper" class="detail-empty surface-panel">
      <p class="eyebrow">{{ lang === 'cn' ? '检索结果' : 'Lookup' }}</p>
      <h2 class="serif-title">{{ lang === 'cn' ? '未找到相关论文。' : 'Paper not found.' }}</h2>
    </div>

    <article v-else class="detail-article">
      <section class="article-hero surface-panel">
        <div class="article-meta-strip">
          <span class="chip" :class="`${paper.category}-chip`">{{ getCategoryLabel(paper.category) }}</span>
          <button
            type="button"
            class="chip direction-chip interactive-press"
            @click="goToTopic(paper.direction)"
          >
            {{ paper.direction }}
          </button>
          <span class="chip"><strong>{{ lang === 'cn' ? '评分' : 'Score' }}</strong> {{ paper.score }}</span>
          <span v-if="paper.candidate_reason" class="chip candidate-chip">{{ formatCandidateReason(paper.candidate_reason) }}</span>
        </div>

        <p class="eyebrow">{{ paper.issue_date }}</p>
        <h1 class="article-title serif-title">
          {{ lang === 'cn' ? paper.title_zh : paper.title_original }}
        </h1>
        <p class="article-subtitle">
          {{
            lang === 'cn'
              ? '一篇经过筛选和多角色审稿后的研究简报。'
              : 'A filtered research brief produced through the multi-agent editorial pipeline.'
          }}
        </p>

        <div class="article-facts">
          <div class="fact-block interactive-lift">
            <span>{{ lang === 'cn' ? '作者' : 'Authors' }}</span>
            <strong>{{ formatAuthors(paper.authors) || '--' }}</strong>
          </div>
          <div class="fact-block interactive-lift">
            <span>{{ lang === 'cn' ? '来源' : 'Venue' }}</span>
            <strong>{{ paper.venue || '--' }}</strong>
          </div>
          <div class="fact-block interactive-lift">
            <span>arXiv</span>
            <strong>{{ paper.arxiv_id }}</strong>
          </div>
        </div>
      </section>

      <section v-if="paper.category !== 'candidate'" class="analysis-grid">
        <div class="summary-panel surface-panel interactive-lift">
          <p class="eyebrow">{{ lang === 'cn' ? '一句话判断' : 'Editorial verdict' }}</p>
          <p class="summary-copy">
            {{ lang === 'cn' ? paper.one_line_summary : paper.one_line_summary_en }}
          </p>
        </div>

        <div class="narrative-panel surface-panel interactive-lift">
          <p class="eyebrow">{{ lang === 'cn' ? '核心亮点' : 'Core highlights' }}</p>
          <ul class="highlights-list">
            <li
              v-for="(item, index) in (lang === 'cn' ? paper.core_highlights : paper.core_highlights_en)"
              :key="index"
            >
              {{ item }}
            </li>
          </ul>
        </div>

        <div class="application-panel surface-panel interactive-lift">
          <p class="eyebrow">{{ lang === 'cn' ? '应用场景' : 'Application scenarios' }}</p>
          <p class="application-copy">
            {{ lang === 'cn' ? paper.application_scenarios : paper.application_scenarios_en }}
          </p>
        </div>
      </section>

      <section v-else class="candidate-state surface-panel interactive-lift">
        <p class="eyebrow">{{ lang === 'cn' ? '候选池状态' : 'Candidate pool status' }}</p>
        <h2 class="serif-title">
          {{
            lang === 'cn'
              ? '该论文留在候选池，未进入最终解读结果。'
              : 'This paper stayed in the candidate pool and was not promoted into the final brief.'
          }}
        </h2>
        <p>
          {{
            lang === 'cn'
              ? '页面仍保留原论文信息与评分原因，方便回看筛选依据。'
              : 'The page still keeps source metadata and scoring reasons for auditability.'
          }}
        </p>
      </section>

      <section class="source-panel surface-panel interactive-lift">
        <details open>
          <summary>{{ lang === 'cn' ? '原论文信息与摘要' : 'Original abstract and paper source' }}</summary>
          <div class="source-body">
            <p class="abstract-text">{{ paper.abstract }}</p>
            <div class="source-actions">
              <a class="primary-button source-action-link" :href="paper.pdf_url" target="_blank" rel="noreferrer">
                {{ lang === 'cn' ? '下载 PDF 原文' : 'Download PDF' }}
              </a>
              <a class="secondary-button source-action-link" :href="'https://arxiv.org/abs/' + paper.arxiv_id" target="_blank" rel="noreferrer">
                {{ lang === 'cn' ? '打开 arXiv' : 'Open arXiv' }}
              </a>
            </div>
          </div>
        </details>
      </section>
    </article>
  </div>
</template>

<script setup>
import { inject, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getPaperDetail } from '../api/papers'

const lang = inject('lang')
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const paper = ref(null)

async function fetchDetail(id) {
  loading.value = true
  try {
    const data = await getPaperDetail(id)
    paper.value = data
  } catch (error) {
    paper.value = null
  } finally {
    loading.value = false
  }
}

function formatAuthors(authors = []) {
  return authors
    .map((author) => (typeof author === 'string' ? author : author.name))
    .filter(Boolean)
    .join(', ')
}

function getCategoryLabel(category) {
  if (category === 'focus') return 'Focus'
  if (category === 'watching') return 'Watching'
  return 'Candidate'
}

function formatCandidateReason(reason) {
  const map = {
    low_score: lang.value === 'cn' ? '低分归档' : 'Low Score',
    capacity_overflow: lang.value === 'cn' ? '容量溢出' : 'Capacity Overflow',
    reviewer_rejected: lang.value === 'cn' ? '审核剔除' : 'Reviewer Rejected',
  }
  return map[reason] || reason
}

function goToTopic(topicKey) {
  if (!topicKey) return
  router.push(`/topic/${encodeURIComponent(topicKey)}`)
}

watch(
  () => route.params.id,
  (paperId) => {
    if (paperId) {
      fetchDetail(paperId)
    } else {
      paper.value = null
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.detail-page {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.back-button {
  align-self: flex-start;
}

.detail-loading {
  padding: 18px 0;
}

.detail-empty,
.article-hero,
.summary-panel,
.narrative-panel,
.application-panel,
.candidate-state,
.source-panel {
  border-radius: var(--radius-xl);
}

.detail-empty {
  padding: 28px;
}

.detail-empty h2 {
  margin: 14px 0 0;
  color: var(--ink-strong);
  font-size: 34px;
}

.detail-article {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.direction-chip {
  cursor: pointer;
}

.article-hero {
  padding: 32px;
}

.article-meta-strip,
.article-facts,
.analysis-grid,
.source-actions {
  display: grid;
  gap: 12px;
}

.article-meta-strip {
  grid-template-columns: repeat(auto-fit, minmax(120px, max-content));
  margin-bottom: 20px;
}

.article-title {
  margin: 12px 0 0;
  max-width: 16ch;
  color: var(--ink-strong);
  font-size: clamp(42px, 5vw, 68px);
  line-height: 0.98;
}

.article-subtitle {
  margin: 16px 0 0;
  max-width: 52ch;
  color: var(--ink-muted);
  font-size: 16px;
  line-height: 1.8;
}

.article-facts {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  margin-top: 24px;
}

.fact-block {
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 250, 242, 0.72);
  border: 1px solid var(--line-soft);
}

.fact-block span {
  display: block;
  font-size: 12px;
  color: var(--ink-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.fact-block strong {
  display: block;
  margin-top: 10px;
  color: var(--ink-strong);
  line-height: 1.55;
}

.analysis-grid {
  grid-template-columns: minmax(0, 0.86fr) minmax(0, 1.14fr);
}

.summary-panel,
.narrative-panel,
.application-panel,
.candidate-state,
.source-panel {
  padding: 28px;
}

.application-panel {
  grid-column: 1 / -1;
}

.summary-copy,
.application-copy {
  margin: 16px 0 0;
  color: var(--ink-strong);
  font-size: 24px;
  line-height: 1.6;
  font-family: var(--font-display);
}

.highlights-list {
  margin: 16px 0 0;
  padding-left: 20px;
  color: var(--ink-body);
  line-height: 1.9;
}

.candidate-state h2 {
  margin: 14px 0 0;
  color: var(--ink-strong);
  font-size: 34px;
}

.candidate-state p:last-child {
  margin: 12px 0 0;
  color: var(--ink-muted);
  line-height: 1.8;
}

.source-panel details {
  display: block;
}

.source-panel summary {
  cursor: pointer;
  list-style: none;
  color: var(--ink-strong);
  font-size: 18px;
  font-weight: 600;
}

.source-panel summary::-webkit-details-marker {
  display: none;
}

.source-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-top: 18px;
}

.abstract-text {
  margin: 0;
  color: var(--ink-body);
  line-height: 1.9;
  white-space: pre-line;
}

.source-actions {
  grid-template-columns: repeat(auto-fit, minmax(180px, max-content));
}

.source-action-link {
  display: inline-flex;
  justify-content: center;
}

@media (max-width: 860px) {
  .analysis-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .article-hero,
  .summary-panel,
  .narrative-panel,
  .application-panel,
  .candidate-state,
  .source-panel {
    padding: 22px;
  }

  .article-meta-strip {
    grid-template-columns: 1fr 1fr;
  }

  .article-title {
    max-width: 11ch;
    font-size: clamp(34px, 10vw, 48px);
  }

  .article-subtitle {
    font-size: 14px;
    line-height: 1.75;
  }

  .article-facts {
    grid-template-columns: 1fr;
  }

  .summary-copy,
  .application-copy {
    font-size: 22px;
    line-height: 1.5;
  }

  .source-actions {
    grid-template-columns: 1fr;
  }

  .source-action-link {
    width: 100%;
  }
}
</style>

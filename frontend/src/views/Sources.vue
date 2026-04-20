<template>
  <div class="sources-page">
    <div class="sources-hero surface-panel">
      <div class="sources-headline">
        <button class="secondary-button" type="button" @click="$router.push('/')">
          {{ lang === 'cn' ? '返回首页' : 'Back to home' }}
        </button>
        <div class="sources-copy-block">
          <p class="eyebrow">{{ lang === 'cn' ? '原始候选池' : 'Candidate pool' }}</p>
          <h1 class="serif-title">
            {{ lang === 'cn' ? '评分结果' : 'All scored papers for the selected issue' }}
          </h1>
          <p class="sources-copy">
            {{
              lang === 'cn'
                ? '展示当日前 50 篇进入评分引擎的论文、加分项、分层结果与未入选原因。'
                : 'A complete audit surface of scored papers, signals, tier assignment, and non-selection reasons.'
            }}
          </p>
        </div>
      </div>

      <div class="sources-stats">
        <div class="sources-stat interactive-lift">
          <span>{{ lang === 'cn' ? 'Issue Date' : 'Issue date' }}</span>
          <strong>{{ $route.params.date }}</strong>
        </div>
        <div class="sources-stat interactive-lift">
          <span>{{ lang === 'cn' ? '当前页条目' : 'Items on page' }}</span>
          <strong>{{ candidates.length }}</strong>
        </div>
        <div class="sources-stat interactive-lift">
          <span>{{ lang === 'cn' ? '总条目' : 'Total' }}</span>
          <strong>{{ total }}</strong>
        </div>
      </div>
    </div>

    <div class="sources-shell">
      <aside class="sources-sidebar">
        <section class="sidebar-card surface-panel interactive-lift">
          <p class="eyebrow">{{ lang === 'cn' ? '阅读方式' : 'How to read this page' }}</p>
          <ul class="sidebar-list">
            <li>{{ lang === 'cn' ? '左侧数字是总分，越高越接近最终入选。' : 'The leading score shows how close a paper is to final selection.' }}</li>
            <li>{{ lang === 'cn' ? 'Signals 展示各项加分来源。' : 'Signals capture the score contributors per paper.' }}</li>
            <li>{{ lang === 'cn' ? 'Candidate reason 解释论文为何没有进入最终简报。' : 'Candidate reason explains why a paper did not enter the final brief.' }}</li>
          </ul>
        </section>
      </aside>

      <section class="sources-main">
        <div v-if="loading" class="loading-state">
          <el-skeleton :rows="10" animated />
        </div>

        <div v-else class="board surface-panel">
          <div class="board-header">
            <span>{{ lang === 'cn' ? '评分' : 'Score' }}</span>
            <span>{{ lang === 'cn' ? '论文' : 'Paper' }}</span>
            <span>{{ lang === 'cn' ? 'Signals' : 'Signals' }}</span>
            <span>{{ lang === 'cn' ? '分层' : 'Tier' }}</span>
          </div>

          <div v-if="!candidates.length" class="board-empty">
            {{ lang === 'cn' ? '该日期暂无候选池数据。' : 'No candidate-pool data for this issue date.' }}
          </div>

          <article v-for="paper in candidates" :key="paper.id" class="board-row interactive-lift">
            <div class="row-score" :class="getScoreClass(paper.score)">
              <span class="row-label mobile-only">{{ lang === 'cn' ? '评分' : 'Score' }}</span>
              <strong>{{ paper.score }}</strong>
            </div>

            <div class="row-paper">
              <span class="row-label mobile-only">{{ lang === 'cn' ? '论文' : 'Paper' }}</span>
              <h3>{{ paper.title_zh }}</h3>
              <p class="paper-original">{{ paper.title_original }}</p>
              <div class="paper-meta">
                <span class="chip">{{ paper.direction }}</span>
                <span class="chip">{{ paper.category }}</span>
              </div>
            </div>

            <div class="row-signals">
              <span class="row-label mobile-only">{{ lang === 'cn' ? 'Signals' : 'Signals' }}</span>
              <span
                v-for="[key, val] in getScoreReasonEntries(paper.score_reasons)"
                :key="key"
                class="chip signal-chip"
              >
                <strong>{{ formatReason(key) }}</strong> +{{ val }}
              </span>
            </div>

            <div class="row-tier">
              <span class="row-label mobile-only">{{ lang === 'cn' ? '分层' : 'Tier' }}</span>
              <span class="chip" :class="getTierChipClass(paper.category)">
                {{ paper.category }}
              </span>
              <span v-if="paper.candidate_reason" class="tier-reason">{{ formatCandidateReason(paper.candidate_reason) }}</span>
            </div>
          </article>
        </div>

        <div class="pagination-area">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :background="true"
            layout="prev, pager, next"
            :total="total"
            @current-change="handlePageChange"
          />
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { inject, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getPapers } from '../api/papers'

const lang = inject('lang')
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const candidates = ref([])
const currentPage = ref(Number(route.query.page) || 1)
const pageSize = ref(50)
const total = ref(0)

async function fetchCandidates() {
  loading.value = true
  try {
    const data = await getPapers({
      issue_date: route.params.date,
      include_candidates: true,
      page: currentPage.value,
      limit: pageSize.value,
    })
    candidates.value = data.items
    total.value = data.total
  } catch (error) {
    candidates.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handlePageChange(value) {
  router.push({ query: { ...route.query, page: value } })
}

function getScoreReasonEntries(scoreReasons) {
  return Object.entries(scoreReasons || {})
}

function formatReason(key) {
  const map = {
    top_org: lang.value === 'cn' ? '顶尖机构' : 'Top Org',
    hf_recommend: lang.value === 'cn' ? 'HF 推荐' : 'HF Daily',
    community_popularity: lang.value === 'cn' ? '社区热度' : 'Popularity',
    top_conf: lang.value === 'cn' ? '顶会收录' : 'Top Conf',
    has_code: lang.value === 'cn' ? '代码可用' : 'Has Code',
    practitioner_relevance: lang.value === 'cn' ? '从业者相关' : 'Practical',
    academic_influence: lang.value === 'cn' ? '学术影响' : 'Citations',
    os_trending: lang.value === 'cn' ? '开源热度' : 'Trending',
  }
  return map[key] || key
}

function formatCandidateReason(reason) {
  const map = {
    low_score: lang.value === 'cn' ? '低分归档' : 'Low Score',
    capacity_overflow: lang.value === 'cn' ? '容量溢出' : 'Capacity Overflow',
    reviewer_rejected: lang.value === 'cn' ? '审核剔除' : 'Reviewer Rejected',
  }
  return map[reason] || reason
}

function getScoreClass(score) {
  if (score >= 80) return 'score-high'
  if (score >= 50) return 'score-mid'
  return 'score-low'
}

function getTierChipClass(category) {
  if (category === 'focus') return 'focus-chip'
  if (category === 'watching') return 'watching-chip'
  return 'candidate-chip'
}

watch(() => route.query.page, (newValue) => {
  currentPage.value = Number(newValue) || 1
  fetchCandidates()
})

onMounted(fetchCandidates)
</script>

<style scoped>
.sources-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.sources-hero,
.sidebar-card,
.board {
  border-radius: var(--radius-xl);
}

.sources-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) 280px;
  gap: 24px;
  padding: 28px;
}

.sources-headline h1 {
  margin: 12px 0 0;
  max-width: 14ch;
  color: var(--ink-strong);
  font-size: clamp(36px, 5vw, 58px);
  line-height: 0.98;
}

.sources-headline {
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 18px;
  min-height: 100%;
}

.sources-headline > .secondary-button {
  justify-self: flex-start;
}

.sources-copy-block {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  min-height: 100%;
  padding-top: clamp(4px, 1vw, 12px);
}

.sources-copy {
  max-width: 56ch;
  margin: 18px 0 0;
  color: var(--ink-muted);
  line-height: 1.8;
}

.sources-stats {
  display: grid;
  gap: 12px;
}

.sources-stat {
  padding: 16px;
  border-radius: 18px;
  background: var(--panel-soft);
  border: 1px solid var(--line-soft);
}

.sources-stat span {
  display: block;
  color: var(--ink-muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.sources-stat strong {
  display: block;
  margin-top: 8px;
  color: var(--ink-strong);
  font-size: 24px;
}

.sources-shell {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 24px;
}

.sources-sidebar,
.sources-main {
  min-width: 0;
}

.sidebar-card {
  padding: 22px;
}

.sidebar-list {
  margin: 16px 0 0;
  padding-left: 18px;
  color: var(--ink-body);
  line-height: 1.8;
}

.loading-state {
  padding: 16px 0;
}

.board {
  overflow: hidden;
}

.board-header,
.board-row {
  display: grid;
  grid-template-columns: 88px minmax(0, 1.15fr) minmax(0, 1fr) 160px;
  gap: 18px;
  padding: 18px 24px;
}

.board-header {
  border-bottom: 1px solid var(--line-soft);
  color: var(--ink-muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.board-row + .board-row {
  border-top: 1px solid var(--line-soft);
}

.row-label {
  display: inline-block;
  margin-bottom: 10px;
  color: var(--ink-muted);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.row-score strong {
  display: block;
  color: var(--ink-strong);
  font-size: 32px;
  line-height: 1;
}

.score-high strong {
  color: var(--focus-tone);
}

.score-mid strong {
  color: #9a6a38;
}

.score-low strong {
  color: var(--ink-muted);
}

.row-paper h3 {
  margin: 0;
  color: var(--ink-strong);
  font-size: 20px;
  line-height: 1.3;
}

.paper-original {
  margin: 8px 0 0;
  color: var(--ink-muted);
  line-height: 1.6;
}

.paper-meta,
.row-signals {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.row-signals {
  gap: 6px;
  align-content: flex-start;
}

.paper-meta {
  margin-top: 12px;
}

.signal-chip {
  gap: 6px;
  min-height: 30px;
  padding: 6px 11px;
  font-size: 12px;
  line-height: 1;
}

.signal-chip strong {
  font-size: 12px;
  font-weight: 600;
}

.row-tier {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tier-reason {
  color: var(--ink-muted);
  line-height: 1.5;
}

.board-empty {
  padding: 30px 24px;
  color: var(--ink-muted);
}

.pagination-area {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

@media (max-width: 1080px) {
  .sources-hero,
  .sources-shell {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .board-header {
    display: none;
  }

  .board-row {
    grid-template-columns: 1fr;
    gap: 14px;
    padding: 20px;
    background: var(--panel-faint);
    border-radius: 22px;
    margin: 12px;
    border: 1px solid var(--line-soft);
  }

  .board-row + .board-row {
    border-top: 0;
  }

  .row-score strong {
    font-size: 28px;
  }

  .row-signals,
  .row-tier {
    gap: 10px;
  }
}
</style>

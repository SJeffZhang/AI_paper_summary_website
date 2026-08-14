<template>
  <div class="brief-home">
    <section class="hero-band surface-panel">
      <div class="hero-copy">
        <p class="eyebrow">{{ lang === 'cn' ? 'Frontier AI editorial brief' : 'Frontier AI editorial brief' }}</p>
        <h1 class="hero-title serif-title" :class="lang === 'en' ? 'hero-title-en' : 'hero-title-cn'">
          <template v-if="lang === 'cn'">
            <span class="hero-title-line">海量论文里</span>
            <span class="hero-title-line">只留下重点</span>
          </template>
          <template v-else>
            Frontier AI, filtered down.
          </template>
        </h1>
        <p class="hero-summary">
          {{ lang === 'cn'
            ? '每日从数百篇前沿AI论文中产出最多5篇Focus与最多12篇Watching，实际数量取决于当日供给与生成结果。每页仅展示一天内容。右侧日历可快速跳转；无数据日期会显示为灰色。'
            : 'Each issue produces up to 5 Focus papers and up to 12 Watching papers from hundreds of frontier AI papers, and the actual count depends on daily supply and generation results. Each page shows one issue date only. Use the calendar on the right for quick jumps; dates without data are shown in gray.' }}
        </p>
        <div class="hero-actions">
          <button class="primary-button" type="button" @click="goToTopics">
            {{ lang === 'cn' ? '进入论文分类' : 'Browse Categories' }}
          </button>
          <button
            class="secondary-button"
            type="button"
            :disabled="!selectedDate"
            @click="goToSources(selectedDate)"
          >
            {{ lang === 'cn' ? '查看原始候选池' : 'View Candidate Pool' }}
          </button>
        </div>
      </div>

      <div class="hero-poster interactive-lift">
        <p class="eyebrow">{{ lang === 'cn' ? '当期概览' : 'Issue overview' }}</p>
        <div class="poster-date serif-title">{{ selectedDate || '--' }}</div>
        <div class="poster-metrics" :class="{ 'poster-metrics-en': lang === 'en' }">
          <div class="poster-metric interactive-lift">
            <span>{{ lang === 'cn' ? 'Focus' : 'Focus' }}</span>
            <strong>{{ focusCount }}</strong>
          </div>
          <div class="poster-metric interactive-lift">
            <span>{{ lang === 'cn' ? 'Watching' : 'Watching' }}</span>
            <strong>{{ watchingCount }}</strong>
          </div>
          <div class="poster-metric interactive-lift">
            <span>{{ lang === 'cn' ? '候选池' : 'Candidate pool' }}</span>
            <strong>{{ candidateCount }}</strong>
          </div>
        </div>
        <p class="poster-note">
          {{
            lang === 'cn'
              ? '重点摘要偏深读，Watching 更像值得继续盯的信号面板。'
              : 'Focus is optimized for deep reading; Watching works more like a curated signal board.'
          }}
        </p>
      </div>
    </section>

    <div class="home-layout">
      <section class="main-rail">
        <div class="section-header">
          <div>
            <p class="eyebrow">Focus</p>
            <h2 class="section-title serif-title">{{ lang === 'cn' ? '当天最值得读的内容' : 'The day’s strongest reads' }}</h2>
          </div>
          <p class="section-caption">{{ selectedDate || '--' }}</p>
        </div>

        <div v-if="loading" class="loading-state">
          <el-skeleton :rows="8" animated />
        </div>

        <div v-else-if="!selectedGroup.focus.length && !selectedGroup.watching.length" class="empty-state surface-panel">
          <p class="eyebrow">{{ lang === 'cn' ? '当前日期' : 'Selected date' }}</p>
          <h3 class="serif-title">
            {{ lang === 'cn' ? '当天暂无可展示内容。' : 'There is no displayable brief for this issue date.' }}
          </h3>
          <p>
            {{
              lang === 'cn'
                ? '可以在右侧日历切换到其他日期。'
                : 'Use the calendar rail on the right to move to another issue.'
            }}
          </p>
        </div>

        <div v-else class="focus-stories">
          <article
            v-for="paper in selectedGroup.focus"
            :key="paper.id"
            class="focus-story surface-panel interactive-lift"
          >
            <div class="story-topline">
              <div class="story-tags">
                <span class="chip focus-chip">Focus</span>
                <button
                  type="button"
                  class="chip direction-chip"
                  @click.stop="goToTopic(paper.direction)"
                >
                  {{ paper.direction }}
                </button>
              </div>
              <div class="story-score">
                <span class="score-label">{{ lang === 'cn' ? '评分' : 'Score' }}</span>
                <strong>{{ paper.score }}</strong>
              </div>
            </div>

            <h3 class="story-title serif-title" @click="goToDetail(paper.id)">
              {{ lang === 'cn' ? paper.title_zh : paper.title_original }}
            </h3>

            <p class="story-summary">
              {{ lang === 'cn' ? paper.one_line_summary : paper.one_line_summary_en }}
            </p>

            <div class="story-signals">
              <span
                v-for="[key, value] in getSignalEntries(paper.score_reasons).slice(0, 3)"
                :key="key"
                class="chip"
              >
                <strong>{{ formatReason(key) }}</strong> +{{ value }}
              </span>
            </div>

            <div class="story-actions">
              <button class="primary-button" type="button" @click="goToDetail(paper.id)">
                {{ lang === 'cn' ? '进入解读' : 'Read brief' }}
              </button>
              <a
                class="story-link app-link"
                :href="'https://arxiv.org/abs/' + paper.arxiv_id"
                target="_blank"
                rel="noreferrer"
              >
                arXiv: {{ paper.arxiv_id }}
              </a>
            </div>
          </article>
        </div>

        <div v-if="selectedGroup.watching.length" class="watching-block">
          <div class="section-header section-header-tight">
            <div>
              <p class="eyebrow">Watching</p>
              <h2 class="section-title serif-title">{{ lang === 'cn' ? '还值得继续盯的信号' : 'Signals still worth tracking' }}</h2>
            </div>
          </div>

          <div class="watching-ledger surface-panel">
            <article
              v-for="paper in selectedGroup.watching"
              :key="paper.id"
              class="watching-row interactive-lift"
              @click="goToDetail(paper.id)"
            >
              <div class="watching-meta">
                <button
                  type="button"
                  class="watching-direction"
                  @click.stop="goToTopic(paper.direction)"
                >
                  {{ paper.direction }}
                </button>
                <strong class="watching-score">{{ paper.score }}</strong>
              </div>
              <div class="watching-copy">
                <h3>{{ lang === 'cn' ? paper.title_zh : paper.title_original }}</h3>
                <p>{{ lang === 'cn' ? paper.one_line_summary : paper.one_line_summary_en }}</p>
              </div>
            </article>
          </div>
        </div>
      </section>

      <aside class="side-rail">
        <details class="rail-disclosure" open>
          <summary class="rail-summary mobile-only">
            <span>{{ lang === 'cn' ? '阅读导航' : 'Reading guide' }}</span>
          </summary>
          <section class="rail-card surface-panel interactive-lift">
            <p class="eyebrow">{{ lang === 'cn' ? '阅读导航' : 'Reading guide' }}</p>
            <h3 class="rail-title serif-title">{{ lang === 'cn' ? '从这里开始读' : 'Start here' }}</h3>
            <ul class="rail-list">
              <li>{{ lang === 'cn' ? '先看 Focus，这是我们认为当天最值得投入时间的内容。' : 'Start with Focus for the pieces most worth your time today.' }}</li>
              <li>{{ lang === 'cn' ? '再看 Watching，快速补齐那些还没到重点解读、但已经值得关注的论文。' : 'Then move to Watching to catch the papers that deserve attention even if they are not full reads yet.' }}</li>
              <li>{{ lang === 'cn' ? '如果你想追溯筛选过程，可以去候选池看当天纳入视野的更多论文。' : 'If you want the wider source picture, open the candidate pool to review the broader set considered that day.' }}</li>
            </ul>
          </section>
        </details>

        <details class="rail-disclosure" open>
          <summary class="rail-summary mobile-only">
            <span>{{ lang === 'cn' ? '日期日历' : 'Issue calendar' }}</span>
          </summary>
          <section class="rail-card surface-panel interactive-lift">
            <div class="calendar-header">
              <button
                type="button"
                class="month-switch interactive-press"
                :disabled="!canGoPrevMonth"
                @click="goPrevMonth"
              >
                ‹
              </button>
              <span class="month-label">{{ monthLabel }}</span>
              <button
                type="button"
                class="month-switch interactive-press"
                :disabled="!canGoNextMonth"
                @click="goNextMonth"
              >
                ›
              </button>
            </div>

            <div class="weekday-row">
              <span v-for="weekday in weekdayLabels" :key="weekday" class="weekday-label">{{ weekday }}</span>
            </div>

            <div class="calendar-grid">
              <button
                v-for="cell in calendarCells"
                :key="cell.key"
                type="button"
                class="calendar-cell interactive-press"
                :class="{
                  empty: !cell.dateKey,
                  selected: cell.isSelected,
                  'has-data': cell.hasData,
                  'no-data': cell.dateKey && !cell.hasData,
                  disabled: !cell.inRange,
                }"
                :disabled="!cell.dateKey || !cell.inRange || loading"
                @click="selectDate(cell.dateKey)"
              >
                <span v-if="cell.dateKey">{{ cell.day }}</span>
              </button>
            </div>

            <div class="calendar-legend">
              <span class="legend-item">
                <span class="legend-dot has-data-dot" />
                {{ lang === 'cn' ? '有数据' : 'Has data' }}
              </span>
              <span class="legend-item">
                <span class="legend-dot no-data-dot" />
                {{ lang === 'cn' ? '无数据' : 'No data' }}
              </span>
            </div>
          </section>
        </details>

        <details class="rail-disclosure" open>
          <summary class="rail-summary mobile-only">
            <span>{{ lang === 'cn' ? '近期日期' : 'Recent issues' }}</span>
          </summary>
          <section class="rail-card surface-panel interactive-lift">
            <p class="eyebrow">{{ lang === 'cn' ? '近期日期' : 'Recent issues' }}</p>
            <div class="recent-issues">
              <button
                v-for="day in recentContentDays"
                :key="day.issue_date"
                type="button"
                class="recent-issue interactive-lift"
                :class="{ active: day.issue_date === selectedDate }"
                @click="selectDate(day.issue_date)"
              >
                <span>{{ day.issue_date }}</span>
                <strong>{{ day.paper_count }}</strong>
              </button>
            </div>
          </section>
        </details>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getPapers, getPapersCalendar } from '../api/papers'

const lang = inject('lang')
const router = useRouter()
const route = useRoute()

const loading = ref(false)
const selectedDate = ref('')
const selectedGroup = ref({ date: '', focus: [], watching: [], candidateCount: 0 })

const minIssueDate = ref('')
const maxIssueDate = ref('')
const latestWithContent = ref('')
const calendarDays = ref([])
const calendarMonth = ref('')

let currentRequestId = 0

const weekdayLabels = computed(() => (
  lang.value === 'cn'
    ? ['一', '二', '三', '四', '五', '六', '日']
    : ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
))

const dateStateMap = computed(() => {
  const map = new Map()
  calendarDays.value.forEach((day) => {
    map.set(day.issue_date, day)
  })
  return map
})

const focusCount = computed(() => selectedGroup.value.focus.length)
const watchingCount = computed(() => selectedGroup.value.watching.length)
const candidateCount = computed(() => selectedGroup.value.candidateCount || 0)

const recentContentDays = computed(() => (
  calendarDays.value
    .filter((day) => day.has_content)
    .slice(-4)
    .reverse()
))

const monthLabel = computed(() => {
  if (!calendarMonth.value) return '--'
  const [year, month] = calendarMonth.value.split('-').map(Number)
  return lang.value === 'cn' ? `${year} 年 ${month} 月` : `${year}-${String(month).padStart(2, '0')}`
})

const canGoPrevMonth = computed(() => {
  if (!calendarMonth.value || !minIssueDate.value) return false
  return calendarMonth.value > minIssueDate.value.slice(0, 7)
})

const canGoNextMonth = computed(() => {
  if (!calendarMonth.value || !maxIssueDate.value) return false
  return calendarMonth.value < maxIssueDate.value.slice(0, 7)
})

const calendarCells = computed(() => {
  if (!calendarMonth.value) return []
  const [year, month] = calendarMonth.value.split('-').map(Number)
  const firstDay = new Date(year, month - 1, 1)
  const daysInMonth = new Date(year, month, 0).getDate()
  const startOffset = (firstDay.getDay() + 6) % 7

  const cells = []
  for (let i = 0; i < startOffset; i += 1) {
    cells.push({ key: `empty-${i}`, dateKey: '', day: '', hasData: false, inRange: false, isSelected: false })
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    const dateKey = toDateKey(new Date(year, month - 1, day))
    const state = dateStateMap.value.get(dateKey)
    const inRange = isDateInRange(dateKey, minIssueDate.value, maxIssueDate.value)
    cells.push({
      key: dateKey,
      dateKey,
      day,
      hasData: !!state?.has_content,
      inRange,
      isSelected: selectedDate.value === dateKey,
    })
  }

  while (cells.length % 7 !== 0) {
    cells.push({
      key: `empty-tail-${cells.length}`,
      dateKey: '',
      day: '',
      hasData: false,
      inRange: false,
      isSelected: false,
    })
  }
  return cells
})

function toDateKey(value) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function parseDateKey(dateKey) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateKey)) return null
  const [year, month, day] = dateKey.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function shiftMonth(monthKey, delta) {
  const [year, month] = monthKey.split('-').map(Number)
  const shifted = new Date(year, month - 1 + delta, 1)
  return toDateKey(shifted).slice(0, 7)
}

function isDateInRange(dateKey, minDate, maxDate) {
  if (!dateKey) return false
  if (minDate && dateKey < minDate) return false
  if (maxDate && dateKey > maxDate) return false
  return true
}

function buildSelectedGroup(items, dateKey, totalCount) {
  const focus = []
  const watching = []
  let candidatesInPage = 0
  items.forEach((paper) => {
    if (paper.category === 'focus') {
      focus.push(paper)
    } else if (paper.category === 'watching') {
      watching.push(paper)
    } else if (paper.category === 'candidate') {
      candidatesInPage += 1
    }
  })
  focus.sort((a, b) => b.score - a.score)
  watching.sort((a, b) => b.score - a.score)
  const parsedTotal = Number(totalCount)
  const candidateCount = Number.isFinite(parsedTotal)
    ? Math.max(parsedTotal - focus.length - watching.length, 0)
    : candidatesInPage
  return { date: dateKey, focus, watching, candidateCount }
}

function getSignalEntries(scoreReasons) {
  return Object.entries(scoreReasons || {}).sort((left, right) => right[1] - left[1])
}

function formatReason(key) {
  const map = {
    top_org: lang.value === 'cn' ? '顶尖机构' : 'Top org',
    hf_recommend: lang.value === 'cn' ? 'HF 推荐' : 'HF daily',
    community_popularity: lang.value === 'cn' ? '社区热度' : 'Popularity',
    top_conf: lang.value === 'cn' ? '顶会' : 'Top conf',
    has_code: lang.value === 'cn' ? '代码' : 'Code',
    practitioner_relevance: lang.value === 'cn' ? '工程相关' : 'Practical',
    academic_influence: lang.value === 'cn' ? '引用影响' : 'Citations',
    os_trending: lang.value === 'cn' ? '开源热度' : 'Trending',
  }
  return map[key] || key
}

async function fetchCalendar() {
  try {
    const calendar = await getPapersCalendar()
    const days = Array.isArray(calendar.days) ? calendar.days : []
    calendarDays.value = days
    minIssueDate.value = calendar.min_issue_date || ''
    maxIssueDate.value = calendar.max_issue_date || ''
    latestWithContent.value = calendar.latest_with_content || ''

    const routeDate = typeof route.query.date === 'string' ? route.query.date : ''
    const defaultDate = routeDate || latestWithContent.value || maxIssueDate.value || ''
    if (!defaultDate) return

    if (!isDateInRange(defaultDate, minIssueDate.value, maxIssueDate.value)) {
      return
    }

    calendarMonth.value = defaultDate.slice(0, 7)
    if (routeDate !== defaultDate) {
      router.replace({ query: { ...route.query, date: defaultDate } })
    } else {
      selectedDate.value = defaultDate
      await fetchPapersByDate(defaultDate)
    }
  } catch (error) {
    calendarDays.value = []
    selectedGroup.value = { date: '', focus: [], watching: [], candidateCount: 0 }
  }
}

async function fetchPapersByDate(issueDate) {
  if (!issueDate) return
  loading.value = true
  const requestId = ++currentRequestId
  try {
    const data = await getPapers({ page: 1, limit: 100, issue_date: issueDate, include_candidates: true })
    if (requestId !== currentRequestId) return
    selectedGroup.value = buildSelectedGroup(data.items || [], issueDate, data.total)
  } catch (error) {
    if (requestId !== currentRequestId) return
    selectedGroup.value = { date: issueDate, focus: [], watching: [], candidateCount: 0 }
  } finally {
    if (requestId === currentRequestId) {
      loading.value = false
    }
  }
}

function selectDate(dateKey) {
  if (!dateKey || !isDateInRange(dateKey, minIssueDate.value, maxIssueDate.value)) return
  if (dateKey === selectedDate.value) return
  router.replace({ query: { ...route.query, date: dateKey } })
}

function goPrevMonth() {
  if (!canGoPrevMonth.value) return
  calendarMonth.value = shiftMonth(calendarMonth.value, -1)
}

function goNextMonth() {
  if (!canGoNextMonth.value) return
  calendarMonth.value = shiftMonth(calendarMonth.value, 1)
}

function goToDetail(id) {
  openRouteInNewTab(`/paper/${id}`)
}

function goToSources(issueDate) {
  if (!issueDate) return
  router.push(`/sources/${issueDate}`)
}

function goToTopics() {
  openRouteInNewTab('/topics')
}

function goToTopic(topicKey) {
  if (!topicKey) return
  openRouteInNewTab(`/topic/${encodeURIComponent(topicKey)}`)
}

function openRouteInNewTab(path) {
  const targetUrl = router.resolve(path).href
  if (typeof window !== 'undefined' && typeof window.open === 'function') {
    window.open(targetUrl, '_blank', 'noopener')
    return
  }
  router.push(path)
}

onMounted(() => {
  fetchCalendar()
})

watch(() => route.query.date, (newDate) => {
  const nextDate = typeof newDate === 'string' ? newDate : ''
  if (!nextDate || !isDateInRange(nextDate, minIssueDate.value, maxIssueDate.value)) return
  selectedDate.value = nextDate
  const parsed = parseDateKey(nextDate)
  if (parsed) {
    calendarMonth.value = toDateKey(parsed).slice(0, 7)
  }
  fetchPapersByDate(nextDate)
})
</script>

<style scoped>
.brief-home {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.hero-band,
.focus-story,
.rail-card,
.watching-ledger,
.empty-state {
  border-radius: var(--radius-xl);
}

.hero-band {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.9fr);
  gap: 28px;
  padding: 34px;
}

.hero-title {
  margin: 16px 0 0;
  max-width: 11ch;
  color: var(--ink-strong);
  font-size: clamp(42px, 6vw, 72px);
  line-height: 0.95;
}

.hero-title-cn {
  width: fit-content;
  max-width: none;
}

.hero-title-line {
  display: block;
  white-space: nowrap;
}

.hero-title-en {
  max-width: 14ch;
  font-size: clamp(31px, 4.1vw, 52px);
  line-height: 0.98;
  text-wrap: balance;
}

.hero-summary {
  max-width: 60ch;
  margin: 18px 0 0;
  color: var(--ink-body);
  font-size: 16px;
  line-height: 1.8;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 24px;
}

.hero-poster {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 24px;
  border-radius: calc(var(--radius-xl) - 4px);
  background:
    linear-gradient(180deg, rgba(255, 251, 244, 0.8), rgba(240, 228, 210, 0.9)),
    radial-gradient(circle at top right, rgba(196, 111, 60, 0.18), transparent 42%);
  border: 1px solid rgba(83, 69, 54, 0.1);
  transition: transform var(--motion-smooth) var(--ease-smooth), box-shadow var(--motion-smooth) var(--ease-smooth);
}

.poster-date {
  color: var(--ink-strong);
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1;
}

.poster-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.poster-metric {
  padding: 14px;
  border-radius: 18px;
  background: rgba(255, 250, 242, 0.82);
  border: 1px solid rgba(83, 69, 54, 0.1);
}

.poster-metric span {
  display: block;
  font-size: 12px;
  color: var(--ink-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.poster-metric strong {
  display: block;
  margin-top: 8px;
  font-size: 28px;
  color: var(--ink-strong);
}

.poster-metrics-en .poster-metric span {
  display: flex;
  align-items: flex-start;
  min-height: 2.5em;
  line-height: 1.25;
}

.poster-note {
  margin: auto 0 0;
  color: var(--ink-muted);
  line-height: 1.7;
}

.home-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 24px;
  align-items: start;
}

.main-rail,
.side-rail {
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-width: 0;
}

.section-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
}

.section-header-tight {
  margin-top: 8px;
}

.section-title {
  margin: 8px 0 0;
  color: var(--ink-strong);
  font-size: clamp(26px, 3vw, 42px);
  line-height: 1.02;
}

.section-caption {
  margin: 0;
  color: var(--ink-muted);
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.loading-state {
  padding: 18px 0;
}

.empty-state {
  padding: 32px;
}

.empty-state h3 {
  margin: 14px 0 0;
  color: var(--ink-strong);
  font-size: 34px;
}

.empty-state p:last-child {
  margin: 12px 0 0;
  color: var(--ink-muted);
}

.focus-stories {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.focus-story {
  padding: 28px;
}

.story-topline,
.story-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.story-tags,
.story-signals {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.direction-chip {
  cursor: pointer;
  transition: border-color var(--motion-fast) ease, color var(--motion-fast) ease, background-color var(--motion-fast) ease;
}

.direction-chip:hover {
  color: var(--accent-deep);
  border-color: rgba(196, 111, 60, 0.28);
  background: rgba(196, 111, 60, 0.12);
}

.story-score {
  text-align: right;
}

.score-label {
  display: block;
  color: var(--ink-muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.story-score strong {
  color: var(--ink-strong);
  font-size: 24px;
}

.story-title {
  margin: 20px 0 0;
  color: var(--ink-strong);
  font-size: clamp(26px, 3vw, 42px);
  line-height: 1.06;
  cursor: pointer;
}

.story-title:hover {
  color: var(--accent-deep);
}

.story-summary {
  max-width: 100%;
  margin: 18px 0 0;
  color: var(--ink-body);
  font-size: 16px;
  line-height: 1.85;
}

.story-signals {
  margin-top: 18px;
}

.story-actions {
  margin-top: 22px;
}

.story-link {
  font-size: 14px;
}

.watching-block {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.watching-ledger {
  padding: 0;
  overflow: hidden;
}

.watching-row {
  display: grid;
  grid-template-columns: 120px minmax(0, 1fr);
  gap: 18px;
  padding: 20px 24px;
  cursor: pointer;
  border-radius: 0;
  position: relative;
}

.watching-row + .watching-row {
  border-top: 1px solid var(--line-soft);
}

.watching-row:first-child {
  border-top-left-radius: calc(var(--radius-xl) - 12px);
  border-top-right-radius: calc(var(--radius-xl) - 12px);
}

.watching-row:last-child {
  border-bottom-left-radius: calc(var(--radius-xl) - 12px);
  border-bottom-right-radius: calc(var(--radius-xl) - 12px);
}

.watching-row:hover {
  background: rgba(255, 250, 242, 0.56);
}

.watching-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.watching-direction {
  appearance: none;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ink-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 12px;
  text-align: left;
  cursor: pointer;
}

.watching-direction:hover {
  color: var(--accent-deep);
}

.watching-score {
  color: var(--watch-tone);
  font-size: 26px;
}

.watching-copy h3 {
  margin: 0;
  color: var(--ink-strong);
  font-size: 22px;
  line-height: 1.24;
}

.watching-copy p {
  margin: 10px 0 0;
  color: var(--ink-body);
  line-height: 1.7;
}

.rail-card {
  padding: 22px;
}

.rail-disclosure {
  display: block;
}

.rail-summary {
  display: none;
}

.rail-title {
  margin: 10px 0 0;
  color: var(--ink-strong);
  font-size: 30px;
  line-height: 1.06;
}

.rail-list {
  margin: 18px 0 0;
  padding-left: 18px;
  color: var(--ink-body);
  line-height: 1.8;
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.month-label {
  color: var(--ink-strong);
  font-weight: 600;
}

.month-switch {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid var(--line-soft);
  background: rgba(255, 250, 242, 0.7);
  color: var(--ink-body);
  cursor: pointer;
}

.month-switch:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.weekday-row,
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 8px;
}

.weekday-row {
  margin-bottom: 10px;
}

.weekday-label {
  text-align: center;
  color: var(--ink-muted);
  font-size: 11px;
  text-transform: uppercase;
}

.calendar-cell {
  height: 38px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: rgba(255, 250, 242, 0.92);
  color: var(--ink-body);
  cursor: pointer;
  transition: background-color 0.18s ease, color 0.18s ease, border-color 0.18s ease;
}

.calendar-cell.empty {
  background: transparent;
  cursor: default;
}

.calendar-cell.has-data {
  background: rgba(196, 111, 60, 0.12);
}

.calendar-cell.no-data {
  background: rgba(103, 92, 79, 0.08);
  color: rgba(67, 58, 49, 0.44);
}

.calendar-cell.selected {
  background: var(--ink-strong);
  color: #fffaf2;
  border-color: var(--ink-strong);
}

.calendar-cell.disabled {
  opacity: 0.48;
  cursor: not-allowed;
}

.calendar-legend {
  display: flex;
  gap: 14px;
  margin-top: 14px;
  color: var(--ink-muted);
  font-size: 12px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.has-data-dot {
  background: var(--accent);
}

.no-data-dot {
  background: rgba(103, 92, 79, 0.32);
}

.recent-issues {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
}

.recent-issue {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 16px;
  border: 1px solid var(--line-soft);
  background: rgba(255, 250, 242, 0.68);
  color: var(--ink-body);
  cursor: pointer;
}

.recent-issue.active {
  border-color: rgba(196, 111, 60, 0.34);
  background: rgba(196, 111, 60, 0.1);
}

.recent-issue strong {
  color: var(--accent-deep);
}

@media (max-width: 1080px) {
  .hero-band,
  .home-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .hero-band,
  .focus-story,
  .rail-card,
  .empty-state {
    padding: 22px;
  }

  .hero-band {
    gap: 22px;
  }

  .hero-title {
    max-width: 9ch;
    font-size: clamp(34px, 10vw, 52px);
  }

  .hero-title-cn {
    max-width: none;
  }

  .hero-title-line {
    white-space: normal;
  }

  .hero-summary {
    font-size: 14px;
    line-height: 1.7;
  }

  .hero-actions {
    flex-direction: column;
  }

  .hero-actions .primary-button,
  .hero-actions .secondary-button {
    width: 100%;
    justify-content: center;
  }

  .story-topline,
  .story-actions,
  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .poster-metrics {
    grid-template-columns: 1fr;
  }

  .watching-row {
    grid-template-columns: 1fr;
  }

  .watching-row,
  .focus-story {
    padding: 18px;
  }

  .story-summary,
  .watching-copy p {
    font-size: 15px;
    line-height: 1.75;
  }

  .rail-disclosure + .rail-disclosure {
    margin-top: -6px;
  }

  .rail-summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 18px;
    border-radius: 18px;
    border: 1px solid var(--line-soft);
    background: rgba(255, 250, 242, 0.72);
    color: var(--ink-strong);
    cursor: pointer;
    list-style: none;
    box-shadow: var(--shadow-card);
  }

  .rail-summary::-webkit-details-marker {
    display: none;
  }

  .rail-summary::after {
    content: '+';
    font-size: 18px;
    color: var(--ink-muted);
  }

  .rail-disclosure[open] .rail-summary::after {
    content: '−';
  }

  .rail-disclosure .rail-card {
    margin-top: 10px;
  }

  .calendar-grid {
    gap: 10px;
  }

  .calendar-cell {
    height: 44px;
    border-radius: 14px;
  }

  .month-switch {
    width: 42px;
    height: 42px;
  }

  .recent-issues {
    gap: 12px;
  }

  .recent-issue {
    padding: 14px 16px;
  }
}
</style>

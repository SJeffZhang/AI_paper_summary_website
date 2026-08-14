<template>
  <div class="topic-page">
    <div class="page-header">
      <div>
        <p class="eyebrow">{{ lang === 'cn' ? '技术方向' : 'Topic' }}</p>
        <h1 class="serif-title">
          {{ lang === 'cn' ? (topicMeta?.labelCn || $route.params.name) : (topicMeta?.labelEn || $route.params.name) }}
        </h1>
        <p class="subtitle">
          {{
            lang === 'cn'
              ? (topicMeta?.descriptionCn || '聚合该方向下的所有历史精选论文')
              : (topicMeta?.descriptionEn || 'All curated papers under this technical direction')
          }}
        </p>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="8" animated />
    </div>

    <div v-else class="topic-feed">
      <article v-for="paper in papers" :key="paper.id" class="topic-row surface-panel interactive-lift">
        <div class="topic-row-meta">
          <span class="chip" :class="paper.category === 'focus' ? 'focus-chip' : 'watching-chip'">
            {{ paper.category === 'focus' ? 'Focus' : 'Watching' }}
          </span>
          <span class="topic-date">{{ paper.issue_date }}</span>
        </div>
        <div class="topic-row-main">
          <h3 class="serif-title" @click="openPaperInNewTab(paper.id)">
            {{ lang === 'cn' ? paper.title_zh : paper.title_original }}
          </h3>
          <p>{{ lang === 'cn' ? paper.one_line_summary : paper.one_line_summary_en }}</p>
        </div>
      </article>

      <div v-if="!papers.length" class="empty-state surface-panel">
        {{ lang === 'cn' ? '暂无该方向论文' : 'No papers found for this topic' }}
      </div>

      <div class="pagination-area" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :background="true"
          layout="prev, pager, next"
          :total="total"
          @current-change="handlePageChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getPapers } from '../api/papers'
import { getTopicMeta } from '../constants/topics'

const lang = inject('lang')
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const papers = ref([])
const currentPage = ref(Number(route.query.page) || 1)
const pageSize = ref(20)
const total = ref(0)
const topicMeta = computed(() => getTopicMeta(route.params.name))

async function fetchTopicPapers() {
  loading.value = true
  try {
    const data = await getPapers({
      direction: route.params.name,
      page: currentPage.value,
      limit: pageSize.value,
    })
    papers.value = data.items
    total.value = data.total
  } catch (error) {
    papers.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function handlePageChange(value) {
  router.push({ query: { ...route.query, page: value } })
}

function openPaperInNewTab(paperId) {
  const targetUrl = router.resolve(`/paper/${paperId}`).href
  if (typeof window !== 'undefined' && typeof window.open === 'function') {
    window.open(targetUrl, '_blank', 'noopener')
    return
  }
  router.push(`/paper/${paperId}`)
}

watch(() => route.query.page, (newValue) => {
  currentPage.value = Number(newValue) || 1
  fetchTopicPapers()
})

onMounted(fetchTopicPapers)
</script>

<style scoped>
.topic-page {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.page-header {
  display: block;
}

.page-header h1 {
  margin: 10px 0 0;
  color: var(--ink-strong);
  font-size: clamp(34px, 5vw, 54px);
  line-height: 0.98;
}

.subtitle {
  max-width: 54ch;
  margin: 14px 0 0;
  color: var(--ink-muted);
  line-height: 1.8;
}

.topic-feed {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.topic-row {
  display: grid;
  grid-template-columns: 140px minmax(0, 1fr);
  gap: 20px;
  padding: 22px;
  border-radius: var(--radius-xl);
}

.topic-row-meta {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.topic-date {
  color: var(--ink-muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.topic-row-main h3 {
  margin: 0;
  color: var(--ink-strong);
  font-size: 30px;
  line-height: 1.08;
  cursor: pointer;
}

.topic-row-main p {
  margin: 12px 0 0;
  color: var(--ink-body);
  line-height: 1.8;
}

.empty-state {
  padding: 24px;
  border-radius: var(--radius-xl);
  color: var(--ink-muted);
}

.pagination-area {
  display: flex;
  justify-content: center;
  margin-top: 10px;
}

@media (max-width: 768px) {
  .page-header,
  .topic-row {
    grid-template-columns: 1fr;
  }

  .page-header {
    display: block;
  }

  .page-header h1 {
    font-size: clamp(32px, 11vw, 44px);
  }

  .topic-row {
    padding: 18px;
  }

  .topic-row-main h3 {
    font-size: 26px;
  }
}
</style>

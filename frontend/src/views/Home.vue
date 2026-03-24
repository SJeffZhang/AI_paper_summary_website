<template>
  <div class="home-page">
    <div class="page-header">
      <h2 v-if="lang === 'cn'">最新简报</h2>
      <h2 v-else>Latest Briefings</h2>
      <p class="subtitle">
        {{ lang === 'cn' ? '每日从数百篇前沿 AI 论文中精选 3-5 篇深度解读，8-12 篇值得关注' : 'Handpicked 3-5 deep dives and 8-12 key mentions from hundreds of AI papers daily' }}
      </p>
    </div>

    <div v-if="loading && groupedPapers.length === 0" class="loading-state">
      <el-skeleton :rows="5" animated />
      <el-skeleton :rows="5" animated style="margin-top: 20px" />
    </div>

    <div v-else-if="!loading && groupedPapers.length === 0" class="empty-state">
      <el-empty :description="lang === 'cn' ? '暂无简报数据' : 'No data available'" />
    </div>

    <div v-else class="paper-feed">
      <div v-for="group in groupedPapers" :key="group.date" class="date-group">
        <el-divider content-position="left">
          <span class="group-date">{{ group.date }}</span>
          <el-link :underline="false" class="source-link" @click="$router.push(`/sources/${group.date}`)">
            {{ lang === 'cn' ? '查看原始候选池' : 'View Candidate Pool' }}
          </el-link>
        </el-divider>

        <!-- Focus Papers (Top 3-5) -->
        <div class="focus-section">
          <div class="section-title">
            <el-tag type="danger" effect="dark" round>Focus</el-tag>
            <span class="title-text">{{ lang === 'cn' ? '重点关注' : 'Top Recommendations' }}</span>
          </div>
          
          <el-card v-for="paper in group.focus" :key="paper.id" class="paper-card focus-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <div class="title-area">
                  <el-tag size="small" effect="plain" class="direction-tag">{{ paper.direction }}</el-tag>
                  <h3 class="paper-title" @click="goToDetail(paper.id)">
                    {{ lang === 'cn' ? paper.title_zh : paper.title_original }}
                  </h3>
                </div>
                <div class="score-badge">
                  <span class="score-val">{{ paper.score }}</span>
                  <span class="score-label">PTS</span>
                </div>
              </div>
            </template>
            
            <div class="paper-content">
              <div class="summary-box">
                <p class="one-line">{{ lang === 'cn' ? paper.one_line_summary : paper.one_line_summary_en }}</p>
              </div>
            </div>

            <div class="card-footer">
              <el-button type="primary" @click="goToDetail(paper.id)">
                {{ lang === 'cn' ? '解读全文' : 'Read Full Brief' }}
              </el-button>
              <el-link :href="'https://arxiv.org/abs/' + paper.arxiv_id" target="_blank" type="info" :underline="false">
                arXiv:{{ paper.arxiv_id }}
              </el-link>
            </div>
          </el-card>
        </div>

        <!-- Watching Papers (Next 8-12) -->
        <div v-if="group.watching.length > 0" class="watching-section">
          <div class="section-title">
            <el-tag type="info" effect="dark" round>Watching</el-tag>
            <span class="title-text">{{ lang === 'cn' ? '也值得关注' : 'Also Worth Watching' }}</span>
          </div>

          <div class="watching-list">
            <div v-for="paper in group.watching" :key="paper.id" class="watching-item" @click="goToDetail(paper.id)">
              <div class="wi-header">
                <span class="wi-direction">[{{ paper.direction }}]</span>
                <span class="wi-title">{{ lang === 'cn' ? paper.title_zh : paper.title_original }}</span>
                <span class="wi-score">{{ paper.score }}</span>
              </div>
              <p class="wi-summary">{{ lang === 'cn' ? paper.one_line_summary : paper.one_line_summary_en }}</p>
            </div>
          </div>
        </div>
      </div>

      <div class="pagination-area">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :background="true"
          layout="prev, pager, next"
          :total="totalPapers"
          @current-change="handlePageChange"
          class="custom-pagination"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, inject } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getPapers } from '../api/papers'

const lang = inject('lang')
const router = useRouter()
const route = useRoute()

const currentPage = ref(Number(route.query.page) || 1)
const pageSize = ref(17) // Approx one day's worth (5 + 12)
const totalPapers = ref(0)
const groupedPapers = ref([])
const loading = ref(false)

let currentRequestId = 0

const groupPapersByDate = (items) => {
  const groups = {}
  items.forEach(paper => {
    const date = paper.issue_date
    if (!groups[date]) {
      groups[date] = { focus: [], watching: [] }
    }
    if (paper.category === 'focus') {
      groups[date].focus.push(paper)
    } else if (paper.category === 'watching') {
      groups[date].watching.push(paper)
    }
  })
  
  return Object.keys(groups)
    .sort((a, b) => new Date(b) - new Date(a))
    .map(date => ({
      date,
      focus: groups[date].focus.sort((a, b) => b.score - a.score),
      watching: groups[date].watching.sort((a, b) => b.score - a.score)
    }))
}

const fetchPapersList = async (page) => {
  loading.value = true
  const requestId = ++currentRequestId
  
  try {
    const data = await getPapers({ page, limit: pageSize.value })
    if (requestId !== currentRequestId) return

    totalPapers.value = data.total || 0
    groupedPapers.value = groupPapersByDate(data.items || [])
  } catch (error) {
    if (requestId === currentRequestId) groupedPapers.value = []
  } finally {
    if (requestId === currentRequestId) loading.value = false
  }
}

onMounted(() => {
  fetchPapersList(currentPage.value)
})

watch(() => route.query.page, (newPage) => {
  const pageNum = Number(newPage) || 1
  currentPage.value = pageNum
  fetchPapersList(pageNum)
})

const handlePageChange = (val) => {
  router.push({ query: { page: val } })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const goToDetail = (id) => {
  router.push(`/paper/${id}`)
}
</script>

<style scoped>
.page-header {
  margin-bottom: 30px;
}

.page-header h2 {
  margin: 0;
  color: #303133;
  font-size: 24px;
}

.subtitle {
  margin: 8px 0 0 0;
  color: #909399;
  font-size: 15px;
}

.date-group {
  margin-bottom: 50px;
}

.group-date {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.source-link {
  margin-left: 15px;
  font-size: 13px;
  font-weight: normal;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.title-text {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.focus-section {
  margin-bottom: 40px;
}

.paper-card {
  margin-bottom: 25px;
  border-radius: 12px;
  border: 1px solid #ebeef5;
  transition: all 0.3s cubic-bezier(.25,.8,.25,1);
}

.focus-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 20px rgba(0,0,0,0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.title-area {
  flex: 1;
}

.direction-tag {
  margin-bottom: 8px;
}

.paper-title {
  margin: 0;
  font-size: 20px;
  color: #1a1a1a;
  cursor: pointer;
  line-height: 1.4;
}

.paper-title:hover {
  color: #409eff;
}

.score-badge {
  background: #fdf6ec;
  border: 1px solid #faecd8;
  color: #e6a23c;
  padding: 5px 10px;
  border-radius: 8px;
  text-align: center;
  margin-left: 15px;
}

.score-val {
  display: block;
  font-size: 18px;
  font-weight: bold;
}

.score-label {
  font-size: 10px;
  opacity: 0.8;
}

.summary-box {
  background-color: #f0f9eb;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
  border-left: 4px solid #67c23a;
}

.one-line {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: #2c3e50;
  line-height: 1.6;
}

.card-footer {
  margin-top: 25px;
  display: flex;
  align-items: center;
  gap: 20px;
}

.watching-list {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #ebeef5;
  overflow: hidden;
}

.watching-item {
  padding: 15px 20px;
  border-bottom: 1px solid #f0f2f5;
  cursor: pointer;
  transition: background 0.2s;
}

.watching-item:last-child {
  border-bottom: none;
}

.watching-item:hover {
  background-color: #f9fbff;
}

.wi-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 5px;
}

.wi-direction {
  color: #909399;
  font-size: 13px;
  font-family: monospace;
}

.wi-title {
  font-weight: bold;
  color: #303133;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wi-score {
  font-size: 12px;
  color: #e6a23c;
  font-weight: bold;
}

.wi-summary {
  margin: 0;
  font-size: 14px;
  color: #606266;
  padding-left: 0;
}

.pagination-area {
  display: flex;
  justify-content: center;
  margin-top: 50px;
  padding-bottom: 40px;
}
</style>

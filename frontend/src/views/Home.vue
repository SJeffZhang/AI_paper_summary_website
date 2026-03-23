<template>
  <div class="home-page">
    <div class="page-header">
      <h2>最新简报</h2>
      <p class="subtitle">每日从数百篇前沿 AI 论文中精选 3-5 篇为您解读</p>
    </div>

    <div v-if="loading && groupedPapers.length === 0" class="loading-state">
      <el-skeleton :rows="5" animated />
      <el-skeleton :rows="5" animated style="margin-top: 20px" />
    </div>

    <div v-else-if="!loading && groupedPapers.length === 0" class="empty-state">
      <el-empty description="暂无简报数据" />
    </div>

    <div v-else class="paper-feed">
      <div v-for="(group, index) in groupedPapers" :key="group.date" class="date-group">
        <el-divider content-position="left">
          <span class="group-date">{{ group.date }}</span>
        </el-divider>

        <el-card v-for="paper in group.items" :key="paper.id" class="paper-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <h3 class="paper-title" @click="goToDetail(paper.id)">{{ paper.title }}</h3>
            </div>
          </template>
          
          <div class="paper-content">
            <el-alert
              :title="paper.one_line_summary"
              type="success"
              :closable="false"
              class="summary-alert"
            />
            
            <div class="highlights">
              <h4>✨ 核心亮点</h4>
              <ul>
                <li v-for="(highlight, hIndex) in paper.core_highlights.slice(0, 2)" :key="hIndex">
                  {{ highlight }}
                </li>
                <li v-if="paper.core_highlights.length > 2" class="more-highlights">...</li>
              </ul>
            </div>
          </div>

          <div class="card-footer">
            <el-button type="primary" @click="goToDetail(paper.id)">阅读全文</el-button>
            <el-link :href="'https://arxiv.org/abs/' + paper.arxiv_id" target="_blank" type="info" :underline="false">
              查看原论文
            </el-link>
          </div>
        </el-card>
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
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getPapers } from '../api/papers'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()

const currentPage = ref(Number(route.query.page) || 1)
const pageSize = ref(10) // e.g., 10 papers per page (approx 2-3 days worth)
const totalPapers = ref(0)
const groupedPapers = ref([])
const loading = ref(false)

// Use a request counter for race-condition protection
let currentRequestId = 0

// Group items by issue_date
const groupPapersByDate = (items) => {
  const groups = {}
  items.forEach(paper => {
    const date = paper.issue_date
    if (!groups[date]) {
      groups[date] = []
    }
    groups[date].push(paper)
  })
  
  // Convert to array sorted by date descending (assuming issue_date is sortable string)
  return Object.keys(groups)
    .sort((a, b) => new Date(b) - new Date(a))
    .map(date => ({
      date,
      items: groups[date]
    }))
}

const fetchPapersList = async (page) => {
  loading.value = true
  const requestId = ++currentRequestId
  
  try {
    const data = await getPapers({ page, limit: pageSize.value })
    
    // If a newer request has been initiated, discard this response
    if (requestId !== currentRequestId) {
      return
    }

    totalPapers.value = data.total || 0
    groupedPapers.value = groupPapersByDate(data.items || [])
  } catch (error) {
    if (requestId === currentRequestId) {
      // Error handling is already done in the interceptor, but we can reset states here
      groupedPapers.value = []
    }
  } finally {
    if (requestId === currentRequestId) {
      loading.value = false
    }
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
  font-size: 14px;
}

.date-group {
  margin-bottom: 40px;
}

.group-date {
  font-size: 18px;
  font-weight: bold;
  color: #409EFF;
}

.paper-card {
  margin-bottom: 20px;
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.paper-title {
  margin: 0;
  font-size: 18px;
  color: #303133;
  cursor: pointer;
  transition: color 0.2s;
  flex-grow: 1;
  padding-right: 15px;
  line-height: 1.4;
}

.paper-title:hover {
  color: #409eff;
}

.summary-alert {
  margin-bottom: 15px;
}

.summary-alert :deep(.el-alert__title) {
  font-size: 15px;
  font-weight: bold;
  line-height: 1.5;
}

.highlights h4 {
  margin: 0 0 10px 0;
  color: #606266;
}

.highlights ul {
  margin: 0;
  padding-left: 20px;
  color: #606266;
  line-height: 1.6;
}

.more-highlights {
  list-style: none;
  color: #909399;
}

.card-footer {
  margin-top: 20px;
  display: flex;
  align-items: center;
  gap: 15px;
}

.pagination-area {
  display: flex;
  justify-content: center;
  margin-top: 40px;
  padding-bottom: 20px;
}
</style>

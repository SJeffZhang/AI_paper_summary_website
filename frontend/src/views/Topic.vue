<template>
  <div class="topic-page">
    <div class="page-header">
      <el-button :icon="Back" @click="$router.push('/')">{{ lang === 'cn' ? '返回首页' : 'Back to Home' }}</el-button>
      <h2 class="title">{{ lang === 'cn' ? '技术方向' : 'Topic' }}: {{ $route.params.name }}</h2>
      <p class="subtitle">{{ lang === 'cn' ? '聚合该方向下的所有历史精选论文' : 'All curated papers under this technical direction' }}</p>
    </div>

    <div v-loading="loading" class="topic-feed">
      <el-card v-for="paper in papers" :key="paper.id" class="paper-card" shadow="hover">
        <div class="card-content">
          <div class="meta-left">
            <el-tag size="small" type="danger" effect="dark" v-if="paper.category === 'focus'">Focus</el-tag>
            <el-tag size="small" type="info" v-else>Watching</el-tag>
            <div class="date-text">{{ paper.issue_date }}</div>
          </div>
          <div class="main-right">
            <h3 class="paper-title" @click="$router.push(`/paper/${paper.id}`)">
              {{ lang === 'cn' ? paper.title : (paper.title_en || paper.title) }}
            </h3>
            <p class="summary">{{ lang === 'cn' ? paper.one_line_summary : paper.one_line_summary_en }}</p>
          </div>
        </div>
      </el-card>

      <div v-if="!loading && papers.length === 0" class="empty-state">
        <el-empty :description="lang === 'cn' ? '暂无该方向论文' : 'No papers found for this topic'" />
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
import { ref, onMounted, inject, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Back } from '@element-plus/icons-vue'
import { getPapers } from '../api/papers'

const lang = inject('lang')
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const papers = ref([])
const currentPage = ref(Number(route.query.page) || 1)
const pageSize = ref(20)
const total = ref(0)

const fetchTopicPapers = async () => {
  loading.value = true
  try {
    // Use server-side filtering for direction
    const data = await getPapers({ 
      direction: route.params.name, 
      page: currentPage.value,
      limit: pageSize.value 
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

const handlePageChange = (val) => {
  router.push({ query: { ...route.query, page: val } })
}

watch(() => route.query.page, (newVal) => {
  currentPage.value = Number(newVal) || 1
  fetchTopicPapers()
})

onMounted(fetchTopicPapers)
</script>

<style scoped>
.topic-page {
  padding-bottom: 50px;
}
.page-header {
  margin-bottom: 30px;
}
.title {
  margin: 15px 0 5px 0;
  font-size: 22px;
}
.subtitle {
  color: #909399;
  font-size: 14px;
}
.paper-card {
  margin-bottom: 15px;
  border-radius: 8px;
}
.card-content {
  display: flex;
  gap: 20px;
}
.meta-left {
  width: 100px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}
.date-text {
  font-size: 12px;
  color: #909399;
}
.main-right {
  flex: 1;
}
.paper-title {
  margin: 0 0 10px 0;
  font-size: 18px;
  color: #303133;
  cursor: pointer;
}
.paper-title:hover {
  color: #409eff;
}
.summary {
  margin: 0;
  color: #606266;
  font-size: 14px;
}
.pagination-area {
  display: flex;
  justify-content: center;
  margin-top: 30px;
}
</style>

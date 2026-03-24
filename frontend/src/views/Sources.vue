<template>
  <div class="sources-page">
    <div class="page-header">
      <el-button :icon="Back" @click="$router.push('/')">{{ lang === 'cn' ? '返回首页' : 'Back to Home' }}</el-button>
      <h2 class="title">{{ lang === 'cn' ? '原始候选池明细' : 'Candidate Pool Details' }} ({{ $route.params.date }})</h2>
      <p class="subtitle">{{ lang === 'cn' ? '展示当日所有经过评分引擎扫描的论文及其得分维度' : 'All papers scanned by the scoring engine for this day' }}</p>
    </div>

    <el-table :data="candidates" stripe style="width: 100%" v-loading="loading">
      <el-table-column prop="score" :label="lang === 'cn' ? '总分' : 'Score'" width="80" sortable>
        <template #default="scope">
          <b :class="getScoreClass(scope.row.score)">{{ scope.row.score }}</b>
        </template>
      </el-table-column>
      <el-table-column prop="title_zh" :label="lang === 'cn' ? '论文标题' : 'Title'">
        <template #default="scope">
          <div class="table-title">{{ scope.row.title_zh }}</div>
          <div class="table-original">{{ scope.row.title_original }}</div>
          <div class="table-direction">{{ scope.row.direction }}</div>
        </template>
      </el-table-column>
      <el-table-column :label="lang === 'cn' ? '加分项' : 'Signals'" width="300">
        <template #default="scope">
          <div class="reasons-tags">
            <el-tag v-for="(val, key) in (scope.row.score_reasons || {})" :key="key" size="small" effect="plain" type="success">
              {{ formatReason(key) }}: +{{ val }}
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column :label="lang === 'cn' ? '分层' : 'Tier'" width="100">
        <template #default="scope">
          <el-tag :type="getTierType(scope.row.category)" size="small">{{ scope.row.category }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="candidate_reason" :label="lang === 'cn' ? '候选原因' : 'Candidate Reason'" width="180">
        <template #default="scope">
          <span>{{ formatCandidateReason(scope.row.candidate_reason) }}</span>
        </template>
      </el-table-column>
    </el-table>

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
const candidates = ref([])
const currentPage = ref(Number(route.query.page) || 1)
const pageSize = ref(50)
const total = ref(0)

const fetchCandidates = async () => {
  loading.value = true
  try {
    // Use server-side filtering for date and include candidates
    const data = await getPapers({ 
      issue_date: route.params.date,
      include_candidates: true,
      page: currentPage.value,
      limit: pageSize.value
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

const handlePageChange = (val) => {
  router.push({ query: { ...route.query, page: val } })
}

watch(() => route.query.page, (newVal) => {
  currentPage.value = Number(newVal) || 1
  fetchCandidates()
})

const formatReason = (key) => {
  const map = {
    'top_org': lang.value === 'cn' ? '顶尖机构' : 'Top Org',
    'hf_recommend': lang.value === 'cn' ? 'HF推荐' : 'HF Daily',
    'community_popularity': lang.value === 'cn' ? '社区热度' : 'Popularity',
    'top_conf': lang.value === 'cn' ? '顶会收录' : 'Top Conf',
    'has_code': lang.value === 'cn' ? '代码可用' : 'Has Code',
    'practitioner_relevance': lang.value === 'cn' ? '从业者相关' : 'Relevant',
    'academic_influence': lang.value === 'cn' ? '学术影响' : 'Citations',
    'os_trending': lang.value === 'cn' ? '开源热度' : 'Trending'
  }
  return map[key] || key
}

const formatCandidateReason = (reason) => {
  if (!reason) return '-'
  const map = {
    low_score: lang.value === 'cn' ? '低分归档' : 'Low Score',
    capacity_overflow: lang.value === 'cn' ? '容量溢出' : 'Capacity Overflow',
    reviewer_rejected: lang.value === 'cn' ? '审核剔除' : 'Reviewer Rejected'
  }
  return map[reason] || reason
}

const getScoreClass = (score) => {
  if (score >= 80) return 'score-high'
  if (score >= 50) return 'score-med'
  return 'score-low'
}

const getTierType = (cat) => {
  if (cat === 'focus') return 'danger'
  if (cat === 'watching') return 'info'
  return ''
}

onMounted(fetchCandidates)
</script>

<style scoped>
.sources-page {
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
.score-high { color: #f56c6c; }
.score-med { color: #e6a23c; }
.score-low { color: #909399; }
.table-title {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}
.table-direction {
  font-size: 12px;
  color: #909399;
}
.table-original {
  font-size: 12px;
  color: #606266;
  margin-bottom: 4px;
}
.reasons-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.pagination-area {
  display: flex;
  justify-content: center;
  margin-top: 30px;
}
</style>

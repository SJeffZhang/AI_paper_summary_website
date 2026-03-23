<template>
  <div class="detail-page">
    <div class="page-header">
      <el-button :icon="Back" @click="$router.back()">返回</el-button>
    </div>

    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="10" animated />
    </div>

    <div v-else-if="!loading && !paper" class="empty-state" style="margin-top: 50px;">
      <el-empty description="未找到相关论文或数据加载失败" />
    </div>

    <div v-else-if="paper" class="paper-article">
      <h1 class="article-title">{{ paper.title }}</h1>
      <div class="article-meta">
        <el-tag size="small" type="info">{{ paper.issue_date }}</el-tag>
        <span class="authors">作者: {{ paper.authors.join(', ') }}</span>
      </div>

      <div class="ai-summary-section">
        <el-alert
          title="💡 一句话总结"
          :description="paper.one_line_summary"
          type="success"
          :closable="false"
          class="highlight-alert"
        />

        <div class="section-block">
          <h3>✨ 核心亮点</h3>
          <ul>
            <li v-for="(item, index) in paper.core_highlights" :key="index">
              {{ item }}
            </li>
          </ul>
        </div>

        <div class="section-block">
          <h3>🚀 应用场景</h3>
          <p>{{ paper.application_scenarios }}</p>
        </div>
      </div>

      <div class="original-section">
        <el-collapse>
          <el-collapse-item title="查看原论文英文摘要 (Abstract)" name="1">
            <p class="abstract-text">{{ paper.abstract }}</p>
            <div class="pdf-link">
              <el-button type="primary" plain tag="a" :href="paper.pdf_url" target="_blank" :icon="Document">
                下载 PDF 原文
              </el-button>
              <el-link :href="'https://arxiv.org/abs/' + paper.arxiv_id" target="_blank" style="margin-left:15px">
                在 arXiv 上查看
              </el-link>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Back, Document } from '@element-plus/icons-vue'
import { getPaperDetail } from '../api/papers'
import { ElMessage } from 'element-plus'

const route = useRoute()
const loading = ref(false)
const paper = ref(null)

const fetchDetail = async (id) => {
  loading.value = true
  try {
    const data = await getPaperDetail(id)
    paper.value = data
  } catch (error) {
    // Error is handled in interceptor
    paper.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDetail(route.params.id)
})
</script>

<style scoped>
.page-header {
  margin-bottom: 20px;
}

.article-title {
  font-size: 24px;
  color: #303133;
  margin-top: 0;
  margin-bottom: 15px;
  line-height: 1.4;
}

.article-meta {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 30px;
  color: #909399;
  font-size: 14px;
}

.ai-summary-section {
  background-color: #ffffff;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  margin-bottom: 30px;
}

.highlight-alert {
  margin-bottom: 25px;
}

.highlight-alert :deep(.el-alert__title) {
  font-size: 16px;
  font-weight: bold;
}

.highlight-alert :deep(.el-alert__description) {
  font-size: 15px;
  margin-top: 8px;
  line-height: 1.5;
}

.section-block {
  margin-bottom: 25px;
}

.section-block h3 {
  color: #303133;
  font-size: 18px;
  margin-bottom: 12px;
}

.section-block ul {
  padding-left: 20px;
  color: #606266;
  line-height: 1.8;
  font-size: 15px;
}

.section-block p {
  color: #606266;
  line-height: 1.8;
  font-size: 15px;
}

.original-section {
  background-color: #ffffff;
  border-radius: 8px;
  padding: 10px 20px;
}

.abstract-text {
  color: #606266;
  line-height: 1.6;
  font-style: italic;
  margin-bottom: 20px;
}

.pdf-link {
  display: flex;
  align-items: center;
}
</style>

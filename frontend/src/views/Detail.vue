<template>
  <div class="detail-page">
    <div class="page-header">
      <el-button :icon="Back" @click="$router.back()">
        {{ lang === 'cn' ? '返回' : 'Back' }}
      </el-button>
    </div>

    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="10" animated />
    </div>

    <div v-else-if="!loading && !paper" class="empty-state" style="margin-top: 50px;">
      <el-empty :description="lang === 'cn' ? '未找到相关论文' : 'Paper not found'" />
    </div>

    <div v-else-if="paper" class="paper-article">
      <div class="category-badge">
        <el-tag :type="paper.category === 'focus' ? 'danger' : 'info'" effect="dark">
          {{ paper.category === 'focus' ? 'Focus' : 'Watching' }}
        </el-tag>
        <el-tag type="warning" effect="plain" class="score-tag">Score: {{ paper.score }}</el-tag>
      </div>
      
      <h1 class="article-title">
        {{ lang === 'cn' ? paper.title : (paper.title_en || paper.title) }}
      </h1>
      
      <div class="article-meta">
        <el-tag size="small" type="info">{{ paper.direction }}</el-tag>
        <span class="authors">{{ lang === 'cn' ? '作者' : 'Authors' }}: {{ paper.authors.join(', ') }}</span>
      </div>

      <div class="ai-summary-section">
        <div class="section-block">
          <h3 class="s-title">💡 {{ lang === 'cn' ? '一句话总结' : 'One-line Summary' }}</h3>
          <p class="summary-text">{{ lang === 'cn' ? paper.one_line_summary : paper.one_line_summary_en }}</p>
        </div>

        <div class="section-block">
          <h3 class="s-title">✨ {{ lang === 'cn' ? '核心亮点' : 'Core Highlights' }}</h3>
          <ul class="highlights-list">
            <li v-for="(item, index) in (lang === 'cn' ? paper.core_highlights : paper.core_highlights_en)" :key="index">
              {{ item }}
            </li>
          </ul>
        </div>

        <div class="section-block">
          <h3 class="s-title">🚀 {{ lang === 'cn' ? '应用场景' : 'Application Scenarios' }}</h3>
          <p class="scenario-text">{{ lang === 'cn' ? paper.application_scenarios : paper.application_scenarios_en }}</p>
        </div>
      </div>

      <div class="original-section">
        <el-collapse>
          <el-collapse-item :title="lang === 'cn' ? '查看原论文摘要 (Abstract)' : 'View Original Abstract'" name="1">
            <p class="abstract-text">{{ paper.abstract }}</p>
            <div class="pdf-link">
              <el-button type="primary" plain tag="a" :href="paper.pdf_url" target="_blank" :icon="Document">
                {{ lang === 'cn' ? '下载 PDF 原文' : 'Download PDF' }}
              </el-button>
              <el-link :href="'https://arxiv.org/abs/' + paper.arxiv_id" target="_blank" style="margin-left:15px">
                arXiv:{{ paper.arxiv_id }}
              </el-link>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'
import { useRoute } from 'vue-router'
import { Back, Document } from '@element-plus/icons-vue'
import { getPaperDetail } from '../api/papers'

const lang = inject('lang')
const route = useRoute()
const loading = ref(false)
const paper = ref(null)

const fetchDetail = async (id) => {
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

onMounted(() => {
  fetchDetail(route.params.id)
})
</script>

<style scoped>
.page-header {
  margin-bottom: 25px;
}

.category-badge {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.score-tag {
  font-weight: bold;
}

.article-title {
  font-size: 28px;
  color: #1a1a1a;
  margin-top: 0;
  margin-bottom: 20px;
  line-height: 1.4;
}

.article-meta {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 35px;
  color: #606266;
  font-size: 15px;
}

.ai-summary-section {
  background-color: #ffffff;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  margin-bottom: 35px;
  border: 1px solid #f0f2f5;
}

.section-block {
  margin-bottom: 35px;
}

.section-block:last-child {
  margin-bottom: 0;
}

.s-title {
  color: #303133;
  font-size: 20px;
  margin-bottom: 15px;
  font-weight: 600;
}

.summary-text {
  font-size: 18px;
  line-height: 1.6;
  color: #2c3e50;
  font-weight: 500;
  background: #f0f9eb;
  padding: 15px 20px;
  border-radius: 8px;
  border-left: 4px solid #67c23a;
}

.highlights-list {
  padding-left: 20px;
  color: #4a4a4a;
  line-height: 1.8;
  font-size: 16px;
}

.scenario-text {
  color: #4a4a4a;
  line-height: 1.8;
  font-size: 16px;
}

.original-section {
  background-color: #ffffff;
  border-radius: 12px;
  padding: 15px 25px;
  border: 1px solid #f0f2f5;
}

.abstract-text {
  color: #606266;
  line-height: 1.7;
  font-style: italic;
  margin-bottom: 25px;
  font-size: 15px;
  background: #fafafa;
  padding: 20px;
  border-radius: 8px;
}

.pdf-link {
  display: flex;
  align-items: center;
}
</style>

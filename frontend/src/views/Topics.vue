<template>
  <div class="topics-page">
    <div class="page-header">
      <el-button @click="$router.push('/')">
        {{ lang === 'cn' ? '返回首页' : 'Back to Home' }}
      </el-button>
      <div class="header-copy">
        <h2>{{ lang === 'cn' ? '论文分类' : 'Paper Categories' }}</h2>
        <p>
          {{
            lang === 'cn'
              ? '按技术方向浏览全部历史精选论文。'
              : 'Browse all curated papers by technical category.'
          }}
        </p>
      </div>
    </div>

    <div class="topic-grid">
      <div
        v-for="topic in TOPIC_CATALOG"
        :key="topic.key"
        class="topic-card"
        role="button"
        tabindex="0"
        @click="goToTopic(topic.key)"
        @keydown.enter.prevent="goToTopic(topic.key)"
        @keydown.space.prevent="goToTopic(topic.key)"
      >
        <el-card class="topic-card-panel" shadow="hover">
          <div class="topic-card-body">
            <div class="topic-topline">
              <el-tag size="small" effect="plain">{{ topic.key }}</el-tag>
            </div>
            <h3 class="topic-title">
              {{ lang === 'cn' ? topic.labelCn : topic.labelEn }}
            </h3>
            <p class="topic-description">
              {{ lang === 'cn' ? topic.descriptionCn : topic.descriptionEn }}
            </p>
            <el-button type="primary" plain @click.stop="goToTopic(topic.key)">
              {{ lang === 'cn' ? '进入分类' : 'Open Category' }}
            </el-button>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject } from 'vue'
import { useRouter } from 'vue-router'

import { TOPIC_CATALOG } from '../constants/topics'

const lang = inject('lang')
const router = useRouter()

const goToTopic = (topicKey) => {
  router.push(`/topic/${topicKey}`)
}
</script>

<style scoped>
.topics-page {
  padding-bottom: 48px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 28px;
}

.header-copy h2 {
  margin: 0 0 8px;
  color: #303133;
  font-size: 26px;
}

.header-copy p {
  margin: 0;
  color: #909399;
  font-size: 15px;
}

.topic-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 18px;
}

.topic-card {
  cursor: pointer;
  border-radius: 14px;
  transition: transform 0.2s ease;
}

.topic-card:hover {
  transform: translateY(-4px);
}

.topic-card:focus-visible {
  outline: 2px solid #409eff;
  outline-offset: 4px;
}

.topic-card-panel {
  height: 100%;
  border-radius: 14px;
  border: 1px solid #ebeef5;
}

.topic-card-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
}

.topic-topline {
  display: flex;
  justify-content: space-between;
  width: 100%;
}

.topic-title {
  margin: 0;
  font-size: 20px;
  color: #1f2937;
}

.topic-description {
  margin: 0;
  min-height: 64px;
  color: #606266;
  line-height: 1.65;
  font-size: 14px;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .topic-grid {
    grid-template-columns: 1fr;
  }
}
</style>

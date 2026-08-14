<template>
  <div class="topics-page">
    <div class="page-header">
      <div class="header-copy">
        <p class="eyebrow">{{ lang === 'cn' ? '研究方向' : 'Research tracks' }}</p>
        <h1 class="serif-title">{{ lang === 'cn' ? '论文分类' : 'Browse the archive by direction' }}</h1>
        <p>
          {{
            lang === 'cn'
              ? '专注了解细分方向'
              : 'Open each track to review how Focus and Watching papers accumulate over time.'
          }}
        </p>
      </div>
    </div>

    <div class="topic-grid">
      <div
        v-for="topic in TOPIC_CATALOG"
        :key="topic.key"
        class="topic-card surface-panel interactive-lift"
        role="button"
        tabindex="0"
        @click="goToTopic(topic.key)"
        @keydown.enter.prevent="goToTopic(topic.key)"
        @keydown.space.prevent="goToTopic(topic.key)"
      >
        <div class="topic-topline">
          <span class="chip">{{ topic.key }}</span>
        </div>
        <h2 class="serif-title topic-title">
          {{ lang === 'cn' ? topic.labelCn : topic.labelEn }}
        </h2>
        <p class="topic-description">
          {{ lang === 'cn' ? topic.descriptionCn : topic.descriptionEn }}
        </p>
        <button class="secondary-button interactive-press" type="button" @click.stop="goToTopic(topic.key)">
          {{ lang === 'cn' ? '进入分类' : 'Open category' }}
        </button>
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

function goToTopic(topicKey) {
  const targetUrl = router.resolve(`/topic/${topicKey}`).href
  if (typeof window !== 'undefined' && typeof window.open === 'function') {
    window.open(targetUrl, '_blank', 'noopener')
    return
  }
  router.push(`/topic/${topicKey}`)
}
</script>

<style scoped>
.topics-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  display: block;
}

.header-copy h1 {
  margin: 10px 0 0;
  color: var(--ink-strong);
  font-size: clamp(34px, 5vw, 54px);
  line-height: 0.98;
}

.header-copy p:last-child {
  max-width: 56ch;
  margin: 14px 0 0;
  color: var(--ink-muted);
  line-height: 1.8;
}

.topic-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 18px;
}

.topic-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 22px;
  border-radius: var(--radius-xl);
  cursor: pointer;
}

.topic-card:focus-visible {
  outline: 2px solid rgba(196, 111, 60, 0.36);
  outline-offset: 4px;
}

.topic-title {
  margin: 0;
  color: var(--ink-strong);
  font-size: 28px;
}

.topic-description {
  margin: 0;
  color: var(--ink-body);
  line-height: 1.8;
}

@media (max-width: 768px) {
  .page-header {
    display: block;
  }

  .topic-card {
    padding: 18px;
  }

  .header-copy h1 {
    font-size: clamp(32px, 11vw, 44px);
  }
}
</style>

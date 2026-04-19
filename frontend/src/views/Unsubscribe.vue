<template>
  <div class="unsubscribe-page">
    <div class="result-card surface-panel interactive-lift">
      <div v-if="loading" class="status-content">
        <el-icon class="is-loading" :size="46" color="var(--accent-deep)"><Loading /></el-icon>
        <p>{{ lang === 'cn' ? '正在处理退订请求...' : 'Processing unsubscribe request...' }}</p>
      </div>

      <div v-else-if="success" class="status-content">
        <el-icon :size="46" color="var(--success-tone)"><CircleCheckFilled /></el-icon>
        <h2 class="serif-title">{{ lang === 'cn' ? '退订成功' : 'Successfully unsubscribed' }}</h2>
        <p>
          {{
            lang === 'cn'
              ? '你已停止接收每日 AI 论文简报。欢迎未来再回来。'
              : 'You will no longer receive the daily AI paper brief.'
          }}
        </p>
        <button class="primary-button" type="button" @click="$router.push('/')">
          {{ lang === 'cn' ? '返回首页' : 'Back home' }}
        </button>
      </div>

      <div v-else class="status-content">
        <el-icon :size="46" color="var(--danger-tone)"><CircleCloseFilled /></el-icon>
        <h2 class="serif-title">{{ lang === 'cn' ? '退订失败' : 'Unsubscribe failed' }}</h2>
        <p>{{ errorMessage || (lang === 'cn' ? '退订链接无效或已过期，请确认链接完整性。' : 'The unsubscribe link is invalid or expired.') }}</p>
        <button class="secondary-button" type="button" @click="$router.push('/')">
          {{ lang === 'cn' ? '返回首页' : 'Back home' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { CircleCheckFilled, CircleCloseFilled, Loading } from '@element-plus/icons-vue'

import { unsubscribeEmail } from '../api/papers'

const lang = inject('lang')
const route = useRoute()
const loading = ref(true)
const success = ref(false)
const errorMessage = ref('')

onMounted(async () => {
  const token = route.query.token
  if (!token) {
    loading.value = false
    success.value = false
    errorMessage.value = lang.value === 'cn' ? '未找到退订凭证 (Token)。' : 'Missing unsubscribe token.'
    return
  }

  try {
    await unsubscribeEmail(token)
    success.value = true
  } catch (error) {
    success.value = false
    errorMessage.value = error.message || ''
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.unsubscribe-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.result-card {
  width: min(560px, 100%);
  padding: 30px;
  border-radius: var(--radius-xl);
}

.status-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  text-align: center;
}

.status-content h2 {
  margin: 0;
  color: var(--ink-strong);
  font-size: 36px;
}

.status-content p {
  margin: 0;
  color: var(--ink-muted);
  line-height: 1.8;
}

@media (max-width: 640px) {
  .result-card {
    padding: 22px;
  }

  .status-content h2 {
    font-size: 30px;
  }
}
</style>

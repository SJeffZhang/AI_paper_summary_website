<template>
  <div class="unsubscribe-page">
    <el-card class="result-card" shadow="hover">
      <div v-if="loading" class="status-content">
        <el-icon class="is-loading" :size="50" color="#409EFC"><Loading /></el-icon>
        <p>正在处理退订请求...</p>
      </div>

      <div v-else-if="success" class="status-content success">
        <el-icon :size="50" color="#67C23A"><CircleCheckFilled /></el-icon>
        <h2>退订成功</h2>
        <p>您已成功退订每日 AI 论文简报。<br>期待未来能再次为您服务！</p>
        <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
      </div>

      <div v-else class="status-content error">
        <el-icon :size="50" color="#F56C6C"><CircleCloseFilled /></el-icon>
        <h2>退订失败</h2>
        <p>{{ errorMessage || '退订链接无效或已过期，请确认链接完整性。' }}</p>
        <el-button @click="$router.push('/')">返回首页</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Loading, CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import { unsubscribeEmail } from '../api/papers'

const route = useRoute()
const loading = ref(true)
const success = ref(false)
const errorMessage = ref('')

onMounted(async () => {
  const token = route.query.token
  if (!token) {
    loading.value = false
    success.value = false
    errorMessage.value = '未找到退订凭证 (Token)。'
    return
  }

  try {
    await unsubscribeEmail(token)
    success.value = true
  } catch (error) {
    success.value = false
    errorMessage.value = error.message || '退订链接无效或已过期，请确认链接完整性。'
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
  width: 100%;
  max-width: 500px;
  text-align: center;
  padding: 20px 0;
}

.status-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
}

.status-content h2 {
  margin: 10px 0 0;
  color: #303133;
}

.status-content p {
  color: #606266;
  line-height: 1.6;
  margin-bottom: 20px;
}
</style>

<template>
  <el-container class="layout-container">
    <el-header class="app-header">
      <div class="header-content">
        <div class="logo-area">
          <h1 class="logo-text" @click="$router.push('/')">AI 论文简报</h1>
        </div>
        <el-menu mode="horizontal" :router="true" class="nav-menu" :ellipsis="false" default-active="/">
          <el-menu-item index="/">首页</el-menu-item>
        </el-menu>
        <div class="action-area">
          <el-button type="primary" plain @click="subscribeDialogVisible = true">
            <el-icon><Message /></el-icon> 邮件订阅
          </el-button>
        </div>
      </div>
    </el-header>

    <el-main class="app-main">
      <div class="main-content">
        <router-view />
      </div>
    </el-main>

    <el-footer class="app-footer">
      <p>© 2026 AI 论文简报. All rights reserved.</p>
    </el-footer>

    <!-- Subscription Dialog -->
    <el-dialog v-model="subscribeDialogVisible" title="订阅每日简报" width="400px" center>
      <el-form :model="subscribeForm" :rules="rules" ref="subscribeFormRef" @submit.prevent="handleSubscribe">
        <el-form-item prop="email">
          <el-input 
            v-model="subscribeForm.email" 
            placeholder="请输入您的邮箱地址"
            :prefix-icon="Message"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="subscribeDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubscribe" :loading="subscribing">
            订阅
          </el-button>
        </span>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { Message } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { subscribeEmail } from './api/papers'

const subscribeDialogVisible = ref(false)
const subscribing = ref(false)
const subscribeFormRef = ref(null)

const subscribeForm = reactive({
  email: ''
})

const rules = {
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: ['blur', 'change'] }
  ]
}

const handleSubscribe = async () => {
  if (!subscribeFormRef.value) return
  await subscribeFormRef.value.validate(async (valid) => {
    if (valid) {
      subscribing.value = true
      try {
        await subscribeEmail(subscribeForm.email)
        subscribeDialogVisible.value = false
        ElMessage({
          message: '验证邮件已发送，请前往邮箱点击确认链接完成订阅！',
          type: 'success',
        })
        subscribeForm.email = ''
      } catch (error) {
        // Error handling is already done in the interceptor
      } finally {
        subscribing.value = false
      }
    }
  })
}
</script>

<style>
body {
  margin: 0;
  font-family: "Helvetica Neue", Helvetica, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "微软雅黑", Arial, sans-serif;
  background-color: #f5f7fa;
}

.layout-container {
  min-height: 100vh;
}

.app-header {
  background-color: #ffffff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0 20px;
}

.header-content {
  width: 100%;
  max-width: 800px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo-text {
  font-size: 20px;
  font-weight: bold;
  color: #409eff;
  cursor: pointer;
  margin: 0;
}

.nav-menu {
  flex-grow: 1;
  justify-content: center;
  border-bottom: none !important;
}

.app-main {
  display: flex;
  justify-content: center;
  padding: 20px;
}

.main-content {
  width: 100%;
  max-width: 800px;
}

.app-footer {
  text-align: center;
  color: #909399;
  font-size: 14px;
  padding: 20px 0;
  margin-top: auto;
}
</style>

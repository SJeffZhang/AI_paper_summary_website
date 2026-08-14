<template>
  <div class="app-shell">
    <header class="shell-header">
      <div class="shell-header-inner surface-panel">
        <button class="brand-lockup interactive-press" type="button" @click="navigateHome">
          <span class="brand-kicker">ArxivDaily</span>
          <span class="brand-title serif-title">
            {{ lang === 'cn' ? 'AI 研究简报' : 'AI Research Brief' }}
          </span>
        </button>

        <nav class="shell-nav desktop-only" aria-label="Primary">
          <button
            type="button"
            class="nav-link interactive-press"
            :class="{ active: route.path === '/' }"
            @click="navigateHome"
          >
            {{ lang === 'cn' ? '首页' : 'Home' }}
          </button>
          <button
            type="button"
            class="nav-link interactive-press"
            :class="{ active: isTopicRoute }"
            @click="navigateTopics"
          >
            {{ lang === 'cn' ? '分类' : 'Topics' }}
          </button>
        </nav>

        <div class="shell-actions desktop-only">
          <div class="lang-pill" role="tablist" :aria-label="lang === 'cn' ? '语言切换' : 'Language switch'">
            <button
              type="button"
              class="lang-option interactive-press"
              :class="{ active: lang === 'cn' }"
              @click="handleLangChange('cn')"
            >
              中文
            </button>
            <button
              type="button"
              class="lang-option interactive-press"
              :class="{ active: lang === 'en' }"
              @click="handleLangChange('en')"
            >
              EN
            </button>
          </div>
          <button class="primary-button subscribe-button interactive-press" type="button" @click="subscribeDialogVisible = true">
            {{ lang === 'cn' ? '订阅日报' : 'Subscribe' }}
          </button>
        </div>

        <div class="mobile-actions">
          <button class="tertiary-button mobile-subscribe interactive-press" type="button" @click="subscribeDialogVisible = true">
            <span class="mobile-subscribe-text">{{ lang === 'cn' ? '订阅' : 'Subscribe' }}</span>
          </button>
          <button
            class="menu-toggle interactive-press"
            type="button"
            :aria-expanded="mobileNavOpen ? 'true' : 'false'"
            :aria-label="lang === 'cn' ? '打开导航菜单' : 'Open navigation menu'"
            @click="toggleMobileNav"
          >
            <el-icon :size="20"><Menu /></el-icon>
          </button>
        </div>
      </div>
    </header>

    <transition name="mobile-overlay">
      <button
        v-if="mobileNavOpen"
        class="mobile-nav-overlay"
        type="button"
        aria-label="Close navigation"
        @click="closeMobileNav"
      />
    </transition>

    <transition name="mobile-drawer">
      <aside
        v-if="mobileNavOpen"
        ref="mobileDrawerRef"
        class="mobile-drawer surface-panel"
        tabindex="-1"
        aria-label="Mobile navigation"
      >
        <div class="mobile-drawer-head">
          <div>
            <p class="eyebrow">{{ lang === 'cn' ? '导航' : 'Navigation' }}</p>
            <h2 class="serif-title">{{ lang === 'cn' ? '快速入口' : 'Quick access' }}</h2>
          </div>
          <button
            type="button"
            class="menu-toggle drawer-close-button interactive-press"
            :aria-label="lang === 'cn' ? '关闭导航菜单' : 'Close navigation menu'"
            @click="closeMobileNav"
          >
            <el-icon :size="20"><Close /></el-icon>
          </button>
        </div>

        <div class="mobile-drawer-links">
          <button
            type="button"
            class="drawer-link interactive-lift"
            :class="{ active: route.path === '/' }"
            @click="navigateHome"
          >
            <span>{{ lang === 'cn' ? '首页' : 'Home' }}</span>
            <small>{{ lang === 'cn' ? '浏览今日摘要与日历' : 'Read the current issue and jump by date' }}</small>
          </button>
          <button
            type="button"
            class="drawer-link interactive-lift"
            :class="{ active: isTopicRoute }"
            @click="navigateTopics"
          >
            <span>{{ lang === 'cn' ? '分类页' : 'Topics' }}</span>
            <small>{{ lang === 'cn' ? '按方向查看历史精选' : 'Browse the archive by research track' }}</small>
          </button>
        </div>

        <div class="drawer-block">
          <p class="eyebrow">{{ lang === 'cn' ? '语言' : 'Language' }}</p>
          <div class="lang-pill">
            <button
              type="button"
              class="lang-option interactive-press"
              :class="{ active: lang === 'cn' }"
              @click="handleLangChange('cn')"
            >
              中文
            </button>
            <button
              type="button"
              class="lang-option interactive-press"
              :class="{ active: lang === 'en' }"
              @click="handleLangChange('en')"
            >
              EN
            </button>
          </div>
        </div>

        <div class="drawer-block drawer-subscribe">
          <p class="eyebrow">{{ lang === 'cn' ? '订阅' : 'Subscribe' }}</p>
          <p>
            {{
              lang === 'cn'
                ? '把每日精选论文简报直接发到邮箱。'
                : 'Send the curated daily brief directly to your inbox.'
            }}
          </p>
          <button class="primary-button interactive-press" type="button" @click="openSubscribeFromDrawer">
            {{ lang === 'cn' ? '打开订阅' : 'Open subscribe' }}
          </button>
        </div>
      </aside>
    </transition>

    <main class="shell-main">
      <router-view :key="lang" />
    </main>

    <footer class="shell-footer">
      <div class="shell-footer-inner">
        <div>
          <p class="footer-label">{{ lang === 'cn' ? '每日研究选题' : 'Daily research curation' }}</p>
          <p class="footer-copy">
            {{
              lang === 'cn'
                ? '从多源前沿 AI 论文中筛出值得跟踪的少数内容。'
                : 'Curated from multi-source frontier AI papers into a small set worth following.'
            }}
          </p>
        </div>
        <p class="footer-meta">© 2026 ArxivDaily</p>
      </div>
    </footer>

    <el-dialog
      v-model="subscribeDialogVisible"
      :title="lang === 'cn' ? '订阅每日简报' : 'Subscribe to the daily brief'"
      width="420px"
      class="subscribe-dialog"
      align-center
    >
      <p class="dialog-copy">
        {{
          lang === 'cn'
            ? '每天早上收到最新一期论文简报。'
            : 'Get each issue delivered to your inbox every morning.'
        }}
      </p>
      <el-form ref="subscribeFormRef" :model="subscribeForm" :rules="rules" @submit.prevent="handleSubscribe">
        <el-form-item prop="email">
          <el-input
            v-model="subscribeForm.email"
            :placeholder="lang === 'cn' ? '请输入邮箱地址' : 'Enter your email'"
            :prefix-icon="Message"
            size="large"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-actions">
          <button class="secondary-button interactive-press" type="button" @click="subscribeDialogVisible = false">
            {{ lang === 'cn' ? '取消' : 'Cancel' }}
          </button>
          <button class="primary-button interactive-press" type="button" @click="handleSubscribe">
            {{ subscribing ? (lang === 'cn' ? '提交中' : 'Submitting') : (lang === 'cn' ? '确认订阅' : 'Subscribe') }}
          </button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, provide, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Close, Menu, Message } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import { subscribeEmail } from './api/papers'
import { applyPageTitle } from './utils/pageTitle'

const router = useRouter()
const route = useRoute()

function readStoredLang() {
  try {
    if (typeof window !== 'undefined' && typeof window.localStorage?.getItem === 'function') {
      return window.localStorage.getItem('lang') || 'cn'
    }
  } catch (error) {
    return 'cn'
  }
  return 'cn'
}

const lang = ref(readStoredLang())
provide('lang', lang)

const subscribeDialogVisible = ref(false)
const subscribing = ref(false)
const subscribeFormRef = ref(null)
const mobileNavOpen = ref(false)
const mobileDrawerRef = ref(null)

const subscribeForm = reactive({
  email: '',
})

const isTopicRoute = computed(() => route.path.startsWith('/topics') || route.path.startsWith('/topic/'))

const emailMessages = computed(() => ({
  required: lang.value === 'cn' ? '请输入邮箱地址' : 'Please enter an email',
  invalid: lang.value === 'cn' ? '请输入正确的邮箱格式' : 'Please enter a valid email address',
}))

const rules = computed(() => ({
  email: [
    { required: true, message: emailMessages.value.required, trigger: 'blur' },
    { type: 'email', message: emailMessages.value.invalid, trigger: ['blur', 'change'] },
  ],
}))

function handleLangChange(nextLang) {
  lang.value = nextLang
  if (typeof window !== 'undefined' && typeof window.localStorage?.setItem === 'function') {
    window.localStorage.setItem('lang', nextLang)
  }
  applyPageTitle(route, nextLang)
}

function navigateHome() {
  closeMobileNav()
  router.push('/')
}

function navigateTopics() {
  closeMobileNav()
  router.push('/topics')
}

function toggleMobileNav() {
  mobileNavOpen.value = !mobileNavOpen.value
}

function closeMobileNav() {
  mobileNavOpen.value = false
}

function openSubscribeFromDrawer() {
  closeMobileNav()
  subscribeDialogVisible.value = true
}

function handleEscape(event) {
  if (event.key === 'Escape') {
    closeMobileNav()
  }
}

watch(
  () => route.fullPath,
  () => {
    applyPageTitle(route, lang.value)
    closeMobileNav()
  },
)

watch(mobileNavOpen, async (isOpen) => {
  document.body.style.overflow = isOpen ? 'hidden' : ''
  if (isOpen) {
    await nextTick()
    mobileDrawerRef.value?.focus()
  }
})

onMounted(() => {
  applyPageTitle(route, lang.value)
  window.addEventListener('keydown', handleEscape)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleEscape)
  document.body.style.overflow = ''
})

async function handleSubscribe() {
  if (!subscribeFormRef.value || subscribing.value) return

  await subscribeFormRef.value.validate(async (valid) => {
    if (!valid) return

    subscribing.value = true
    try {
      await subscribeEmail(subscribeForm.email)
      subscribeDialogVisible.value = false
      subscribeForm.email = ''
      ElMessage({
        message:
          lang.value === 'cn'
            ? '验证邮件已发送，请前往邮箱完成确认。'
            : 'Verification email sent. Please confirm from your inbox.',
        type: 'success',
      })
    } finally {
      subscribing.value = false
    }
  })
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  color: var(--ink-body);
}

.shell-header {
  position: sticky;
  top: 0;
  z-index: 30;
  padding: 20px 24px 0;
}

.shell-header-inner,
.shell-footer-inner {
  width: min(1240px, 100%);
  margin: 0 auto;
}

.shell-header-inner {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 14px 18px;
  border-radius: 999px;
  isolation: isolate;
}

.brand-lockup,
.nav-link,
.lang-option,
.menu-toggle,
.drawer-link {
  appearance: none;
  border: 0;
  background: transparent;
}

.brand-lockup {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 0;
  margin-left: 20px;
  cursor: pointer;
  color: var(--ink-strong);
  text-align: center;
}

.brand-kicker {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--ink-muted);
}

.brand-title {
  font-size: 24px;
  line-height: 1;
}

.shell-nav {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-link {
  padding: 10px 14px;
  border-radius: 999px;
  color: var(--ink-muted);
  cursor: pointer;
  transition: background-color var(--motion-fast) ease, color var(--motion-fast) ease;
}

.nav-link.active,
.nav-link:hover {
  color: var(--ink-strong);
  background: rgba(196, 111, 60, 0.1);
}

.shell-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.lang-pill {
  display: inline-flex;
  padding: 4px;
  border-radius: 999px;
  border: 1px solid var(--line-soft);
  background: rgba(255, 250, 242, 0.84);
}

.lang-option {
  padding: 8px 12px;
  border-radius: 999px;
  color: var(--ink-muted);
  cursor: pointer;
  transition: background-color var(--motion-fast) ease, color var(--motion-fast) ease;
}

.lang-option.active {
  background: var(--ink-strong);
  color: #fffaf2;
}

.subscribe-button {
  padding-inline: 20px;
}

.shell-main {
  width: min(1240px, 100%);
  margin: 0 auto;
  padding: 40px 24px 64px;
}

.shell-footer {
  padding: 0 24px 28px;
}

.shell-footer-inner {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--line-soft);
}

.footer-label,
.footer-meta {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink-muted);
}

.footer-copy {
  margin: 8px 0 0;
  color: var(--ink-body);
  font-size: 14px;
}

.mobile-actions {
  display: none;
  align-items: stretch;
  gap: 10px;
  height: 48px;
}

.mobile-actions > button {
  margin: 0;
  flex-shrink: 0;
}

.mobile-subscribe {
  height: 100%;
  min-height: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 16px;
  white-space: nowrap;
}

.mobile-subscribe-text {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 1em;
  line-height: 1;
  transform: translateY(-0.5px);
}

.menu-toggle {
  width: 48px;
  min-width: 48px;
  height: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: var(--ink-strong);
  background: rgba(255, 250, 242, 0.7);
  border: 1px solid var(--line-soft);
  cursor: pointer;
  flex-shrink: 0;
  line-height: 1;
}

.drawer-close-button {
  width: 48px;
  min-width: 48px;
  height: 48px;
  min-height: 48px;
}

.menu-toggle :deep(.el-icon) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.mobile-nav-overlay {
  position: fixed;
  inset: 0;
  z-index: 39;
  border: 0;
  background: rgba(34, 29, 23, 0.22);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  cursor: pointer;
}

.mobile-drawer {
  position: fixed;
  inset: auto 16px 16px 16px;
  z-index: 40;
  padding: 22px;
  border-radius: 28px;
  outline: none;
}

.mobile-drawer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.mobile-drawer-head h2 {
  margin: 10px 0 0;
  color: var(--ink-strong);
  font-size: 34px;
  line-height: 0.96;
}

.mobile-drawer-links {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 20px;
}

.drawer-link,
.drawer-block {
  width: 100%;
  padding: 16px;
  border-radius: 20px;
  border: 1px solid var(--line-soft);
  background: rgba(255, 250, 242, 0.7);
}

.drawer-link {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  cursor: pointer;
  text-align: left;
}

.drawer-link span {
  color: var(--ink-strong);
  font-weight: 600;
}

.drawer-link small,
.drawer-block p:last-child {
  color: var(--ink-muted);
  line-height: 1.65;
}

.drawer-link.active {
  border-color: rgba(196, 111, 60, 0.24);
  background: rgba(196, 111, 60, 0.1);
}

.drawer-block {
  margin-top: 14px;
}

.drawer-block .lang-pill {
  margin-top: 14px;
}

.drawer-subscribe button {
  margin-top: 12px;
}

.dialog-copy {
  margin: 0 0 16px;
  color: var(--ink-muted);
  line-height: 1.6;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.mobile-overlay-enter-active,
.mobile-overlay-leave-active,
.mobile-drawer-enter-active,
.mobile-drawer-leave-active {
  transition: opacity var(--motion-smooth) var(--ease-smooth), transform var(--motion-smooth) var(--ease-smooth);
}

.mobile-overlay-enter-from,
.mobile-overlay-leave-to {
  opacity: 0;
}

.mobile-drawer-enter-from,
.mobile-drawer-leave-to {
  opacity: 0;
  transform: translateY(16px);
}

@media (max-width: 960px) {
  .shell-header {
    padding-top: 18px;
  }

  .shell-header-inner {
    border-radius: 28px;
  }
}

@media (max-width: 860px) {
  .shell-header {
    position: sticky;
    padding: 14px 16px 0;
  }

  .shell-header-inner {
    gap: 12px;
    padding: 12px 14px;
  }

  .brand-title {
    font-size: 20px;
  }

  .mobile-actions {
    display: flex;
    margin-left: auto;
  }

  .shell-main,
  .shell-footer {
    padding-left: 16px;
    padding-right: 16px;
  }
}

@media (max-width: 520px) {
  .shell-header-inner {
    border-radius: 22px;
  }

  .mobile-subscribe {
    padding-inline: 14px;
    font-size: 13px;
  }

  .dialog-actions {
    flex-direction: column;
  }
}
</style>

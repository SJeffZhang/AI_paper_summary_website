import { ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, ElementPlus, mount } from '../../frontend/test-utils.js'

import { flushPromises } from './helpers'

const subscribeEmailMock = vi.fn()

vi.mock('../../frontend/src/api/papers', () => ({
  subscribeEmail: (...args) => subscribeEmailMock(...args)
}))

import App from '../../frontend/src/App.vue'

describe('App shell', () => {
  beforeEach(() => {
    const storage = {}
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: {
        getItem: (key) => (key in storage ? storage[key] : null),
        setItem: (key, value) => {
          storage[key] = String(value)
        },
        removeItem: (key) => {
          delete storage[key]
        },
      },
    })
    subscribeEmailMock.mockReset()
    window.localStorage.setItem('lang', 'cn')
    window.localStorage.removeItem('theme')
    delete document.documentElement.dataset.theme
  })

  it('opens the mobile drawer and routes to topics', async () => {
    const HomeStub = { template: '<div>home stub</div>' }
    const TopicStub = { template: '<div>topics stub</div>' }
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: HomeStub },
        { path: '/topics', component: TopicStub },
      ],
    })

    await router.push('/')
    await router.isReady()

    const wrapper = mount(App, {
      global: {
        provide: { lang: ref('cn') },
        plugins: [ElementPlus, router],
      },
    })

    await wrapper.find('.menu-toggle').trigger('click')
    expect(wrapper.find('.mobile-drawer').exists()).toBe(true)

    const topicButton = wrapper.findAll('.drawer-link')[1]
    await topicButton.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/topics')
    expect(wrapper.find('.mobile-drawer').exists()).toBe(false)
  })

  it('updates document title for route and language changes', async () => {
    const HomeStub = { template: '<div>home stub</div>' }
    const TopicStub = { template: '<div>topics stub</div>' }
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'home', component: HomeStub },
        { path: '/topics', name: 'topics', component: TopicStub },
      ],
    })

    await router.push('/')
    await router.isReady()

    const wrapper = mount(App, {
      global: {
        plugins: [ElementPlus, router],
      },
    })

    expect(document.title).toBe('arXivDaily')

    const langButtons = wrapper.findAll('.lang-option')
    await langButtons[1].trigger('click')
    expect(document.title).toBe('arXivDaily')

    await router.push('/topics')
    await flushPromises()
    expect(document.title).toBe('Topics')
  })

  it('toggles dark mode and persists the theme choice', async () => {
    const HomeStub = { template: '<div>home stub</div>' }
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'home', component: HomeStub },
      ],
    })

    await router.push('/')
    await router.isReady()

    const wrapper = mount(App, {
      global: {
        plugins: [ElementPlus, router],
      },
    })

    expect(document.documentElement.dataset.theme).toBe('light')

    await wrapper.find('.theme-toggle').trigger('click')
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(window.localStorage.getItem('theme')).toBe('dark')

    await wrapper.find('.theme-toggle').trigger('click')
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(window.localStorage.getItem('theme')).toBe('light')
  })
})

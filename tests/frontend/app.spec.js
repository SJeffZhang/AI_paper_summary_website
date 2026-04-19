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
    subscribeEmailMock.mockReset()
    window.localStorage?.setItem?.('lang', 'cn')
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
})

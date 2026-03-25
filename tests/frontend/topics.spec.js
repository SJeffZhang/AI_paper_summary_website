import { ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, ElementPlus, mount } from '../../frontend/test-utils.js'
import { flushPromises } from './helpers'

const getPapersMock = vi.fn()

vi.mock('../../frontend/src/api/papers', () => ({
  getPapers: (...args) => getPapersMock(...args)
}))

import Topics from '../../frontend/src/views/Topics.vue'
import Topic from '../../frontend/src/views/Topic.vue'

describe('Topics view', () => {
  beforeEach(() => {
    getPapersMock.mockReset()
  })

  it('renders the category catalog and can route to a topic page', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/topics', component: Topics },
        { path: '/topic/:name', component: Topic }
      ]
    })

    await router.push('/topics')
    await router.isReady()

    const wrapper = mount(Topics, {
      global: {
        provide: { lang: ref('cn') },
        plugins: [ElementPlus, router]
      }
    })

    expect(wrapper.text()).toContain('论文分类')
    expect(wrapper.text()).toContain('智能体')

    await wrapper.findAll('.topic-card')[0].trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.fullPath).toBe('/topic/Agent')
  })
})

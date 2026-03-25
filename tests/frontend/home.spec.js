import { ref } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '../../frontend/test-utils.js'

import { paperListPayload } from '../fixtures/frontend-data'
import { createTestRouter, flushPromises, testPlugins } from './helpers'
const getPapersMock = vi.fn()

vi.mock('../../frontend/src/api/papers', () => ({
  getPapers: (...args) => getPapersMock(...args)
}))

import Home from '../../frontend/src/views/Home.vue'

describe('Home view', () => {
  beforeEach(() => {
    getPapersMock.mockReset()
    getPapersMock.mockResolvedValue(paperListPayload)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders grouped focus and watching papers in Chinese mode', async () => {
    const router = await createTestRouter('/', '/', Home)
    const wrapper = mount(Home, {
      global: {
        provide: { lang: ref('cn') },
        plugins: [...testPlugins, router]
      }
    })

    await flushPromises()

    expect(getPapersMock).toHaveBeenCalledWith({ page: 1, limit: 17 })
    expect(wrapper.text()).toContain('中文焦点标题')
    expect(wrapper.text()).toContain('中文观察标题')
    expect(wrapper.text()).not.toContain('中文候选标题')
    expect(wrapper.text().indexOf('中文焦点标题')).toBeLessThan(wrapper.text().indexOf('中文观察标题'))
  })

  it('switches to original titles in English mode', async () => {
    const router = await createTestRouter('/', '/', Home)
    const wrapper = mount(Home, {
      global: {
        provide: { lang: ref('en') },
        plugins: [...testPlugins, router]
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Focus Title Original')
    expect(wrapper.text()).toContain('Watching Title Original')
  })

  it('shows a category entry button on the homepage', async () => {
    const router = await createTestRouter('/', '/', Home)
    const wrapper = mount(Home, {
      global: {
        provide: { lang: ref('cn') },
        plugins: [...testPlugins, router]
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('进入论文分类')
    expect(wrapper.text()).toContain('最多 5 篇 Focus 与最多 12 篇 Watching')
  })
})

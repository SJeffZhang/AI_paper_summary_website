import { ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '../../frontend/test-utils.js'

import { paperListPayload } from '../fixtures/frontend-data'
import { createTestRouter, flushPromises, testPlugins } from './helpers'
const getPapersMock = vi.fn()

vi.mock('../../frontend/src/api/papers', () => ({
  getPapers: (...args) => getPapersMock(...args)
}))

import Topic from '../../frontend/src/views/Topic.vue'

describe('Topic view', () => {
  let openSpy

  beforeEach(() => {
    getPapersMock.mockReset()
    getPapersMock.mockResolvedValue({
      total: 1,
      items: [paperListPayload.items[0]]
    })
    openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
  })

  afterEach(() => {
    openSpy.mockRestore()
  })

  it('requests direction-filtered papers and renders topic content', async () => {
    const router = await createTestRouter('/topic/:name', '/topic/Agent', Topic)
    const wrapper = mount(Topic, {
      global: {
        provide: { lang: ref('cn') },
        plugins: [...testPlugins, router]
      }
    })

    await flushPromises()

    expect(getPapersMock).toHaveBeenCalledWith({
      direction: 'Agent',
      page: 1,
      limit: 20
    })
    expect(wrapper.text()).toContain('中文焦点标题')
    expect(wrapper.text()).toContain('焦点中文总结')
    expect(wrapper.text()).not.toContain('返回分类')
  })

  it('opens detail pages in a new tab', async () => {
    const router = await createTestRouter('/topic/:name', '/topic/Agent', Topic)
    const wrapper = mount(Topic, {
      global: {
        provide: { lang: ref('cn') },
        plugins: [...testPlugins, router]
      }
    })

    await flushPromises()

    await wrapper.find('.topic-row-main h3').trigger('click')

    expect(openSpy).toHaveBeenCalledWith('/paper/1', '_blank', 'noopener')
  })
})

import { ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '../../frontend/test-utils.js'

import { paperListPayload } from '../fixtures/frontend-data'
import { createTestRouter, flushPromises, testPlugins } from './helpers'
const getPapersMock = vi.fn()

vi.mock('../../frontend/src/api/papers', () => ({
  getPapers: (...args) => getPapersMock(...args)
}))

import Sources from '../../frontend/src/views/Sources.vue'

describe('Sources view', () => {
  beforeEach(() => {
    getPapersMock.mockReset()
    getPapersMock.mockResolvedValue(paperListPayload)
  })

  it('requests candidate pool and renders score reasons and candidate reason text', async () => {
    const router = await createTestRouter('/sources/:date', '/sources/2026-03-23', Sources)
    const wrapper = mount(Sources, {
      global: {
        provide: { lang: ref('cn') },
        plugins: [...testPlugins, router]
      }
    })

    await flushPromises()

    expect(getPapersMock).toHaveBeenCalledWith({
      issue_date: '2026-03-23',
      include_candidates: true,
      page: 1,
      limit: 50
    })
    expect(wrapper.text()).toContain('中文候选标题')
    expect(wrapper.text()).toContain('顶尖机构')
    expect(wrapper.text()).toContain('顶会收录')
    expect(wrapper.text()).toContain('学术影响')
    expect(wrapper.text()).toContain('代码可用')
    expect(wrapper.text()).toContain('低分归档')
  })
})

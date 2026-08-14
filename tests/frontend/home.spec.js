import { ref } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '../../frontend/test-utils.js'

import { paperCalendarPayload, paperListPayload } from '../fixtures/frontend-data'
import { createTestRouter, flushPromises, testPlugins } from './helpers'
const getPapersMock = vi.fn()
const getPapersCalendarMock = vi.fn()

vi.mock('../../frontend/src/api/papers', () => ({
  getPapers: (...args) => getPapersMock(...args),
  getPapersCalendar: (...args) => getPapersCalendarMock(...args)
}))

import Home from '../../frontend/src/views/Home.vue'

describe('Home view', () => {
  let openSpy

  beforeEach(() => {
    getPapersMock.mockReset()
    getPapersCalendarMock.mockReset()
    getPapersMock.mockResolvedValue(paperListPayload)
    getPapersCalendarMock.mockResolvedValue(paperCalendarPayload)
    openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
  })

  afterEach(() => {
    vi.clearAllMocks()
    openSpy.mockRestore()
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

    expect(getPapersCalendarMock).toHaveBeenCalled()
    expect(getPapersMock).toHaveBeenCalledWith({
      page: 1,
      limit: 100,
      issue_date: '2026-03-23',
      include_candidates: true
    })
    expect(wrapper.text()).toContain('中文焦点标题')
    expect(wrapper.text()).toContain('中文观察标题')
    expect(wrapper.text()).not.toContain('中文候选标题')
    expect(wrapper.text().indexOf('中文焦点标题')).toBeLessThan(wrapper.text().indexOf('中文观察标题'))
  })

  it('shows the candidate pool count from the full issue payload', async () => {
    const router = await createTestRouter('/', '/', Home)
    const wrapper = mount(Home, {
      global: {
        provide: { lang: ref('cn') },
        plugins: [...testPlugins, router]
      }
    })

    await flushPromises()

    const metrics = wrapper.findAll('.poster-metric strong')
    expect(metrics.map((metric) => metric.text())).toEqual(['1', '1', '2'])
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

    expect(getPapersCalendarMock).toHaveBeenCalled()
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
    expect(wrapper.text()).toContain('每页仅展示一天内容')
  })

  it('opens detail and topic routes in a new tab instead of replacing the current page', async () => {
    const router = await createTestRouter('/', '/', Home)
    const wrapper = mount(Home, {
      global: {
        provide: { lang: ref('cn') },
        plugins: [...testPlugins, router]
      }
    })

    await flushPromises()

    await wrapper.find('.story-actions .primary-button').trigger('click')
    await wrapper.find('.hero-actions .primary-button').trigger('click')

    expect(openSpy).toHaveBeenCalledWith('/paper/1', '_blank', 'noopener')
    expect(openSpy).toHaveBeenCalledWith('/topics', '_blank', 'noopener')
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('renders gray calendar cells for dates without data', async () => {
    const router = await createTestRouter('/', '/', Home)
    const wrapper = mount(Home, {
      global: {
        provide: { lang: ref('cn') },
        plugins: [...testPlugins, router]
      }
    })

    await flushPromises()

    const noDataCells = wrapper.findAll('.calendar-cell.no-data')
    expect(noDataCells.length).toBeGreaterThan(0)
  })
})

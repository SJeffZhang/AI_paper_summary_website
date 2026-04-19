import { ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '../../frontend/test-utils.js'

import { candidateDetail, focusDetail } from '../fixtures/frontend-data'
import { createTestRouter, flushPromises, testPlugins } from './helpers'
const getPaperDetailMock = vi.fn()

vi.mock('../../frontend/src/api/papers', () => ({
  getPaperDetail: (...args) => getPaperDetailMock(...args)
}))

import Detail from '../../frontend/src/views/Detail.vue'

describe('Detail view', () => {
  beforeEach(() => {
    getPaperDetailMock.mockReset()
  })

  it('renders narrative sections for non-candidate papers', async () => {
    getPaperDetailMock.mockResolvedValue(focusDetail)
    const router = await createTestRouter('/paper/:id', '/paper/1', Detail)

    const wrapper = mount(Detail, {
      global: {
        provide: { lang: ref('cn') },
        plugins: [...testPlugins, router]
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('中文焦点标题')
    expect(wrapper.text()).toContain('焦点中文总结')
    expect(wrapper.text()).toContain('亮点一')
    expect(wrapper.findAll('.fact-block strong')[1].text()).toBe('OpenAI')
    expect(wrapper.text()).not.toContain('候选池')
  })

  it('summarizes multiple affiliations and keeps the full list in the tooltip', async () => {
    getPaperDetailMock.mockResolvedValue({
      ...focusDetail,
      venue: null,
      authors: [
        { name: 'Alice', affiliation: 'OpenAI' },
        { name: 'Bob', affiliation: 'Stanford University' },
        { name: 'Carol', affiliation: 'OpenAI' },
        { name: 'Dave', affiliation: 'Google DeepMind' },
      ],
    })
    const router = await createTestRouter('/paper/:id', '/paper/1', Detail)

    const wrapper = mount(Detail, {
      global: {
        provide: { lang: ref('cn') },
        plugins: [...testPlugins, router]
      }
    })

    await flushPromises()

    const affiliationBlock = wrapper.findAll('.fact-block strong')[1]
    expect(affiliationBlock.text()).toBe('OpenAI / Stanford University 等 3 家机构')
    expect(affiliationBlock.attributes('title')).toBe('OpenAI\nStanford University\nGoogle DeepMind')
  })

  it('shows an explicit fallback when the source does not provide affiliations', async () => {
    getPaperDetailMock.mockResolvedValue({
      ...focusDetail,
      authors: [{ name: 'Alice', affiliation: '' }],
      venue: null,
    })
    const router = await createTestRouter('/paper/:id', '/paper/1', Detail)

    const wrapper = mount(Detail, {
      global: {
        provide: { lang: ref('cn') },
        plugins: [...testPlugins, router]
      }
    })

    await flushPromises()

    const affiliationBlock = wrapper.findAll('.fact-block strong')[1]
    expect(affiliationBlock.text()).toBe('论文源未提供作者单位')
    expect(affiliationBlock.attributes('title')).toBe('')
  })

  it('renders candidate fallback without AI narrative content', async () => {
    getPaperDetailMock.mockResolvedValue(candidateDetail)
    const router = await createTestRouter('/paper/:id', '/paper/4', Detail)

    const wrapper = mount(Detail, {
      global: {
        provide: { lang: ref('cn') },
        plugins: [...testPlugins, router]
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('最新候选标题')
    expect(wrapper.text()).toContain('容量溢出')
    expect(wrapper.text()).toContain('候选池')
    expect(wrapper.text()).not.toContain('亮点一')
  })
})

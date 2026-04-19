import request from '../utils/request'

const useMockBriefData = import.meta.env.VITE_USE_MOCK_BRIEF_DATA === 'true'
let mockProviderPromise

function getMockProvider() {
  if (!mockProviderPromise) {
    mockProviderPromise = import('../mocks/papers')
  }
  return mockProviderPromise
}

/**
 * 获取简报列表 (Feed 流)
 * @param {Object} params - Query parameters
 * @param {number} params.page - Page number (default: 1)
 * @param {number} params.limit - Items per page (default: 10)
 * @returns {Promise<Object>} Promise resolving to { total: number, items: Array }
 */
export function getPapers(params = { page: 1, limit: 10 }) {
  if (useMockBriefData) {
    return getMockProvider().then(({ getMockPapers }) => getMockPapers(params))
  }
  return request({
    url: '/api/v1/papers',
    method: 'get',
    params
  })
}

/**
 * 获取首页日期日历（包含有数据与无数据日期）
 * @returns {Promise<Object>} Promise resolving to { min_issue_date, max_issue_date, latest_with_content, days }
 */
export function getPapersCalendar() {
  if (useMockBriefData) {
    return getMockProvider().then(({ getMockPapersCalendar }) => getMockPapersCalendar())
  }
  return request({
    url: '/api/v1/papers/calendar',
    method: 'get'
  })
}

/**
 * 获取单篇简报详细信息
 * @param {number|string} id - The ID of the paper
 * @returns {Promise<Object>} Promise resolving to the paper detail object
 */
export function getPaperDetail(id) {
  if (useMockBriefData) {
    return getMockProvider().then(({ getMockPaperDetail }) => getMockPaperDetail(id))
  }
  return request({
    url: `/api/v1/papers/${id}`,
    method: 'get'
  })
}

/**
 * 提交邮箱订阅申请
 * @param {string} email - User's email address
 * @returns {Promise<Object>} Promise resolving to the success message
 */
export function subscribeEmail(email) {
  if (useMockBriefData) {
    return getMockProvider().then(({ subscribeMockEmail }) => subscribeMockEmail(email))
  }
  return request({
    url: '/api/v1/subscribe',
    method: 'post',
    data: {
      email
    }
  })
}

/**
 * 提交退订请求
 * @param {string} token - User's unique unsubscribe token
 * @returns {Promise<Object>} Promise resolving to the success message
 */
export function unsubscribeEmail(token) {
  if (useMockBriefData) {
    return getMockProvider().then(({ unsubscribeMockEmail }) => unsubscribeMockEmail(token))
  }
  return request({
    url: '/api/v1/unsubscribe',
    method: 'post',
    data: {
      token
    }
  })
}

import request from '../utils/request'

/**
 * 获取简报列表 (Feed 流)
 * @param {Object} params - Query parameters
 * @param {number} params.page - Page number (default: 1)
 * @param {number} params.limit - Items per page (default: 10)
 * @returns {Promise<Object>} Promise resolving to { total: number, items: Array }
 */
export function getPapers(params = { page: 1, limit: 10 }) {
  return request({
    url: '/api/v1/papers',
    method: 'get',
    params
  })
}

/**
 * 获取单篇简报详细信息
 * @param {number|string} id - The ID of the paper
 * @returns {Promise<Object>} Promise resolving to the paper detail object
 */
export function getPaperDetail(id) {
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
  return request({
    url: '/api/v1/unsubscribe',
    method: 'post',
    data: {
      token
    }
  })
}

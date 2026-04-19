import { mockCalendarPayload, mockPaperDetails, mockPaperList } from './briefingData'

function delay(payload, wait = 180) {
  return new Promise((resolve) => {
    setTimeout(() => resolve(payload), wait)
  })
}

function normalizePage(page) {
  const parsed = Number(page)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1
}

function normalizeLimit(limit) {
  const parsed = Number(limit)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 10
}

function categoryRank(category) {
  if (category === 'focus') return 0
  if (category === 'watching') return 1
  return 2
}

function sortPapers(items) {
  return [...items].sort((left, right) => {
    if (left.issue_date !== right.issue_date) {
      return right.issue_date.localeCompare(left.issue_date)
    }
    if (left.category !== right.category) {
      return categoryRank(left.category) - categoryRank(right.category)
    }
    return right.score - left.score
  })
}

export async function getMockPapers(params = { page: 1, limit: 10 }) {
  const page = normalizePage(params.page)
  const limit = normalizeLimit(params.limit)
  const includeCandidates = params.include_candidates === true || params.include_candidates === 'true'

  let items = [...mockPaperList]

  if (params.issue_date) {
    items = items.filter((paper) => paper.issue_date === params.issue_date)
  }

  if (params.direction) {
    items = items.filter((paper) => paper.direction === params.direction)
  }

  if (!includeCandidates) {
    items = items.filter((paper) => paper.category !== 'candidate')
  }

  const ordered = sortPapers(items)
  const start = (page - 1) * limit
  const pagedItems = ordered.slice(start, start + limit)

  return delay({
    total: ordered.length,
    items: pagedItems,
  })
}

export async function getMockPapersCalendar() {
  return delay(mockCalendarPayload)
}

export async function getMockPaperDetail(id) {
  const numericId = Number(id)
  const detail = mockPaperDetails.get(numericId)
  if (!detail) {
    return Promise.reject(new Error('Paper not found'))
  }
  return delay(detail)
}

export async function subscribeMockEmail(email) {
  return delay({
    message: `Mock subscription request accepted for ${email}`,
  }, 120)
}

export async function unsubscribeMockEmail(token) {
  if (!token) {
    return Promise.reject(new Error('Missing unsubscribe token'))
  }

  return delay({
    message: 'Mock unsubscribe succeeded',
  }, 120)
}

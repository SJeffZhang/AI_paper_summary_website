export function getPageTitle(route, lang = 'cn') {
  const pageLabel = getPageLabel(route, lang)
  return pageLabel || 'ArxivDaily'
}

export function applyPageTitle(route, lang = 'cn') {
  if (typeof document === 'undefined') return
  document.title = getPageTitle(route, lang)
}

function getPageLabel(route, lang) {
  const isCn = lang === 'cn'

  switch (route?.name) {
    case 'home':
      return 'arXivDaily'
    case 'detail':
      return isCn ? '论文详情' : 'Paper Detail'
    case 'sources':
      return isCn ? '原始候选池' : 'Candidate Pool'
    case 'topics':
      return isCn ? '论文分类' : 'Topics'
    case 'topic':
      return getTopicTitle(route?.params?.name, isCn)
    case 'unsubscribe':
      return isCn ? '退订日报' : 'Unsubscribe'
    default:
      return ''
  }
}

function getTopicTitle(topicName, isCn) {
  if (!topicName) {
    return isCn ? '方向详情' : 'Topic Detail'
  }
  return isCn ? `${topicName} 分类` : `${topicName} Topic`
}

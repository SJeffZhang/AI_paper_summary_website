import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Detail from '../views/Detail.vue'
import Unsubscribe from '../views/Unsubscribe.vue'
import Sources from '../views/Sources.vue'
import Topic from '../views/Topic.vue'
import Topics from '../views/Topics.vue'
import { applyPageTitle } from '../utils/pageTitle'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home
    },
    {
      path: '/paper/:id',
      name: 'detail',
      component: Detail
    },
    {
      path: '/sources/:date',
      name: 'sources',
      component: Sources
    },
    {
      path: '/topic/:name',
      name: 'topic',
      component: Topic
    },
    {
      path: '/topics',
      name: 'topics',
      component: Topics
    },
    {
      path: '/unsubscribe',
      name: 'unsubscribe',
      component: Unsubscribe
    }
  ]
})

router.afterEach((to) => {
  const lang = typeof window !== 'undefined' ? window.localStorage?.getItem('lang') || 'cn' : 'cn'
  applyPageTitle(to, lang)
})

export default router

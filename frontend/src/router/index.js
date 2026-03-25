import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Detail from '../views/Detail.vue'
import Unsubscribe from '../views/Unsubscribe.vue'
import Sources from '../views/Sources.vue'
import Topic from '../views/Topic.vue'
import Topics from '../views/Topics.vue'

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

export default router

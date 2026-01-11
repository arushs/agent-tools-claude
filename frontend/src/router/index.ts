import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '../components/LandingPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'landing',
      component: LandingPage
    },
    {
      path: '/demo',
      name: 'demo',
      component: () => import('../views/DemoView.vue')
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('../views/AdminView.vue')
    }
  ]
})

export default router

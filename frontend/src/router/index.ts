import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('../views/Login.vue'), meta: { public: true } },
    { path: '/', name: 'list', component: () => import('../views/TripList.vue') },
    { path: '/create', name: 'create', component: () => import('../views/TripCreate.vue') },
    { path: '/trips/:id', name: 'detail', component: () => import('../views/TripDetail.vue') },
    { path: '/profile', name: 'profile', component: () => import('../views/Profile.vue') },
    { path: '/settings', name: 'settings', component: () => import('../views/Settings.vue'), meta: { admin: true } },
  ],
})

router.beforeEach(async (to) => {
  const userStore = useUserStore()
  // 首次进入时恢复登录态
  if (!userStore.user && localStorage.getItem('tripcanvas_token')) {
    await userStore.fetchMe()
  }
  if (to.meta.public) {
    if (userStore.isLoggedIn) return '/'
    return true
  }
  if (!userStore.isLoggedIn) return '/login'
  if (to.meta.admin && !userStore.isAdmin) return '/'
  return true
})

export default router

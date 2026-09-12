import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'
import { getToken } from '../api'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('../views/Login.vue'), meta: { public: true } },
    { path: '/', name: 'list', component: () => import('../views/TripList.vue') },
    { path: '/create', name: 'create', component: () => import('../views/TripCreate.vue') },
    { path: '/trips/:id', name: 'detail', component: () => import('../views/TripDetail.vue') },
    { path: '/profile', name: 'profile', component: () => import('../views/Profile.vue') },
    { path: '/settings', name: 'settings', component: () => import('../views/Settings.vue'), meta: { admin: true } },
    { path: '/share/:token', name: 'share', component: () => import('../views/ShareView.vue'), meta: { public: true } },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  const userStore = useUserStore()
  // 分享页面始终可访问，不需要登录
  if (to.name === 'share') return true
  // 恢复登录态（仅在没有user信息且有token时）
  if (!userStore.user && getToken()) {
    try {
      await userStore.fetchMe()
    } catch {
      // fetchMe失败不阻塞，继续后续判断
    }
  }
  // 公开页面：已登录则跳首页，未登录放行
  if (to.meta.public) {
    return userStore.isLoggedIn ? '/' : true
  }
  // 私有页面：未登录跳登录页
  if (!userStore.isLoggedIn) return '/login'
  // 管理员页面：非管理员跳首页
  if (to.meta.admin && !userStore.isAdmin) return '/'
  return true
})

export default router

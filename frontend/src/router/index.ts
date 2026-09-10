import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'list', component: () => import('../views/TripList.vue') },
    { path: '/create', name: 'create', component: () => import('../views/TripCreate.vue') },
    { path: '/trips/:id', name: 'detail', component: () => import('../views/TripDetail.vue') },
    { path: '/settings', name: 'settings', component: () => import('../views/Settings.vue') },
  ],
})

export default router

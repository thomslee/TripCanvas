import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'list', component: () => import('../views/TripList.vue') },
    { path: '/create', name: 'create', component: () => import('../views/TripCreate.vue') },
    { path: '/trips/:id', name: 'detail', component: () => import('../views/TripDetail.vue') },
  ],
})

export default router

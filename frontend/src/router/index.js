import { createRouter, createWebHistory } from 'vue-router'
import TenantLogin from '../views/TenantLogin.vue'
import PlatformLogin from '../views/PlatformLogin.vue'
import Layout from '../views/Layout.vue'

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: TenantLogin },
  { path: '/platform/login', component: PlatformLogin },
  {
    path: '/app',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/app/chat' },
      { path: 'chat', component: () => import('../views/ChatView.vue') },
      { path: 'history', component: () => import('../views/ChatHistory.vue') },
      { path: 'kbs', component: () => import('../views/KnowledgeBases.vue') },
      { path: 'docs/:kbId', component: () => import('../views/Documents.vue'), props: true },
      { path: 'admin/users', component: () => import('../views/admin/Users.vue') },
      { path: 'admin/depts', component: () => import('../views/admin/Departments.vue') },
      { path: 'admin/audit', component: () => import('../views/admin/Audit.vue') },
      { path: 'admin/dashboard', component: () => import('../views/admin/Dashboard.vue') },
      { path: 'admin/failed-docs', component: () => import('../views/admin/FailedDocs.vue') },
      { path: 'profile', component: () => import('../views/Profile.vue') },
    ],
  },
  {
    path: '/platform',
    component: () => import('../views/platform/PlatformLayout.vue'),
    meta: { requiresPlatform: true },
    children: [
      { path: '', redirect: '/platform/overview' },
      { path: 'overview', component: () => import('../views/platform/PlatformOverview.vue') },
      { path: 'tenants', component: () => import('../views/platform/Tenants.vue') },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !localStorage.getItem('token')) return '/login'
  if (to.meta.requiresPlatform) {
    if (!localStorage.getItem('token') || localStorage.getItem('auth_type') !== 'platform') {
      return '/platform/login'
    }
  }
  return true
})

export default router

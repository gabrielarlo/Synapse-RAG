import { createRouter, createWebHistory } from 'vue-router'
import Login from './views/Login.vue'
import Accounts from './views/Accounts.vue'
import Staff from './views/Staff.vue'
import Documents from './views/Documents.vue'
import Chat from './views/Chat.vue'
import Audit from './views/Audit.vue'

const routes = [
  { path: '/login', component: Login },
  { path: '/', redirect: '/chat' },
  { path: '/accounts', component: Accounts },
  { path: '/staff', component: Staff },
  { path: '/documents', component: Documents },
  { path: '/chat', component: Chat },
  { path: '/audit', component: Audit }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  if (to.path !== '/login' && !localStorage.getItem('access_token')) {
    return '/login'
  }
})

export default router

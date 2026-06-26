import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Home', component: () => import('../views/HomeView.vue') },
  { path: '/settings', name: 'Settings', component: () => import('../views/SettingsView.vue') },
  {
    path: '/novel/:id',
    component: () => import('../components/layout/NovelLayout.vue'),
    children: [
      { path: '', name: 'Writing', component: () => import('../views/WritingView.vue') },
      { path: 'outline', name: 'Outline', component: () => import('../views/OutlineView.vue') },
      { path: 'characters', name: 'Characters', component: () => import('../views/CharactersView.vue') },
      { path: 'foreshadows', name: 'Foreshadows', component: () => import('../views/ForeshadowsView.vue') },
    ],
  },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})

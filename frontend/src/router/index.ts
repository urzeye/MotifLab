import { createRouter, createWebHistory } from 'vue-router'

// 新首页
import LandingView from '../views/LandingView.vue'

// 小红书模式页面
import HomeView from '../views/HomeView.vue'
import OutlineView from '../views/OutlineView.vue'
import GenerateView from '../views/GenerateView.vue'
import ResultView from '../views/ResultView.vue'
import PublishView from '../views/PublishView.vue'

// 概念图模式页面
import ConceptView from '../views/ConceptView.vue'

// 通用页面
import HistoryView from '../views/HistoryView.vue'
import SettingsView from '../views/SettingsView.vue'
import KnowledgeView from '../views/KnowledgeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // 首页 - 模式选择
    {
      path: '/',
      name: 'landing',
      component: LandingView
    },

    // ============ 小红书模式 ============
    {
      path: '/redbook',
      name: 'redbook',
      component: HomeView
    },
    {
      path: '/redbook/outline',
      name: 'redbook-outline',
      component: OutlineView
    },
    {
      path: '/redbook/generate',
      name: 'redbook-generate',
      component: GenerateView
    },
    {
      path: '/redbook/result',
      name: 'redbook-result',
      component: ResultView
    },
    {
      path: '/redbook/publish',
      name: 'redbook-publish',
      component: PublishView
    },

    // ============ 概念图模式 ============
    {
      path: '/concept',
      name: 'concept',
      component: ConceptView
    },
    // 概念图子页面待实现
    // {
    //   path: '/concept/analyze',
    //   name: 'concept-analyze',
    //   component: ConceptAnalyzeView
    // },

    // ============ 通用页面 ============
    {
      path: '/history',
      name: 'history',
      component: HistoryView
    },
    {
      path: '/history/:id',
      name: 'history-detail',
      component: HistoryView
    },
    {
      path: '/knowledge',
      name: 'knowledge',
      component: KnowledgeView
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView
    },

    // ============ 向后兼容旧路由 ============
    // 保持旧路由可用，重定向到新路径
    {
      path: '/outline',
      redirect: '/redbook/outline'
    },
    {
      path: '/generate',
      redirect: '/redbook/generate'
    },
    {
      path: '/result',
      redirect: '/redbook/result'
    },
    {
      path: '/publish',
      redirect: '/redbook/publish'
    },
  ]
})

export default router

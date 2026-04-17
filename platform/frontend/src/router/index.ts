import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';

import DashboardPage from '@/pages/DashboardPage.vue';
import CasesPage from '@/pages/CasesPage.vue';
import SuitesPage from '@/pages/SuitesPage.vue';
import EnvironmentsPage from '@/pages/EnvironmentsPage.vue';
import RunsPage from '@/pages/RunsPage.vue';
import SchedulesPage from '@/pages/SchedulesPage.vue';
import { useAppStore } from '@/stores/app';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: { name: 'dashboard' },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: DashboardPage,
    meta: {
      title: '仪表盘',
      description: '先看全局健康度、重点迁移项和最近运行，适合作为日常进入平台的首页。',
      navLabel: '仪表盘',
      shortLabel: 'DB',
      section: 'dashboard',
    },
  },
  {
    path: '/cases',
    name: 'cases',
    component: CasesPage,
    meta: {
      title: '用例管理',
      description: '承载 HTTP 用例、断言、变量提取与标签等结构化资产。',
      navLabel: '用例管理',
      shortLabel: 'CA',
      section: 'cases',
    },
  },
  {
    path: '/suites',
    name: 'suites',
    component: SuitesPage,
    meta: {
      title: '套件管理',
      description: '用于组合用例、整理执行顺序，并给调度中心提供稳定入口。',
      navLabel: '套件管理',
      shortLabel: 'SU',
      section: 'suites',
    },
  },
  {
    path: '/environments',
    name: 'environments',
    component: EnvironmentsPage,
    meta: {
      title: '环境管理',
      description: '统一管理 base_url、鉴权策略和环境变量，避免散落在 YAML 中。',
      navLabel: '环境管理',
      shortLabel: 'EN',
      section: 'environments',
    },
  },
  {
    path: '/runs',
    name: 'runs',
    component: RunsPage,
    meta: {
      title: '执行结果',
      description: '集中查看运行记录、失败上下文和后续问题分析入口。',
      navLabel: '执行结果',
      shortLabel: 'RU',
      section: 'runs',
    },
  },
  {
    path: '/schedules',
    name: 'schedules',
    component: SchedulesPage,
    meta: {
      title: '调度任务',
      description: '配置轻量任务计划，让平台负责记录与触发，worker 负责执行。',
      navLabel: '调度任务',
      shortLabel: 'SC',
      section: 'schedules',
    },
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior: () => ({ top: 0 }),
});

router.afterEach((to) => {
  // 路由 meta 是页面信息的单一入口：
  // 标题、描述、导航高亮都优先从这里取，避免每个组件自己维护一套副本。
  const appStore = useAppStore();
  appStore.setCurrentSection(to.meta.section);
  document.title = `测试平台 · ${to.meta.title}`;
});

export default router;


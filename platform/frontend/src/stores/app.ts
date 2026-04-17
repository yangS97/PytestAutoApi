import { computed, ref } from 'vue';
import { defineStore } from 'pinia';

import type { NavigationItem, RouteName } from '@/types/platform';

const defaultNavigation: NavigationItem[] = [
  { name: 'dashboard', label: '仪表盘', shortLabel: 'DB', description: '查看平台整体健康度与迁移重点。' },
  { name: 'cases', label: '用例管理', shortLabel: 'CA', description: '维护 HTTP 用例、断言与变量提取。' },
  { name: 'suites', label: '套件管理', shortLabel: 'SU', description: '组织用例顺序、分组与依赖。' },
  { name: 'environments', label: '环境管理', shortLabel: 'EN', description: '维护 base_url、鉴权和环境变量。' },
  { name: 'runs', label: '执行结果', shortLabel: 'RU', description: '查看运行记录、失败明细与定位信息。' },
  { name: 'schedules', label: '调度任务', shortLabel: 'SC', description: '配置轻量 cron 任务与执行入口。' },
];

export const useAppStore = defineStore('app', () => {
  // 这个 store 只放“壳层状态”：
  // 品牌信息、导航配置、当前所在模块等都属于页面外壳，不属于具体业务页。
  const platformName = ref('TestFlow Platform');
  const platformSlogan = ref('平台主真源 / 轻量执行 / 可渐进迁移');
  const phaseLabel = ref('阶段一：1-3 人测试团队提效');
  const navigation = ref(defaultNavigation);
  const currentSection = ref<RouteName>('dashboard');

  const currentNavigation = computed(() =>
    navigation.value.find((item) => item.name === currentSection.value),
  );

  const setCurrentSection = (section: RouteName) => {
    currentSection.value = section;
  };

  return {
    platformName,
    platformSlogan,
    phaseLabel,
    navigation,
    currentSection,
    currentNavigation,
    setCurrentSection,
  };
});


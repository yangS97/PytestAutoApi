import { ref } from 'vue';
import { defineStore } from 'pinia';

import { dashboardApi } from '@/api';
import type { ApiDataSource, DashboardOverview } from '@/types/platform';

const createEmptyOverview = (): DashboardOverview => ({
  metrics: [],
  focusItems: [],
  recentRuns: [],
});

export const useDashboardStore = defineStore('dashboard', () => {
  // dashboard store 演示“页面数据进入 Pinia”的最小闭环：
  // 页面只发起 load，异步状态、最后更新时间和数据结果由 store 统一维护。
  const overview = ref<DashboardOverview>(createEmptyOverview());
  const loading = ref(false);
  const lastLoadedAt = ref('');
  const errorMessage = ref('');
  const source = ref<ApiDataSource>('mock');
  const note = ref('');

  const loadOverview = async () => {
    loading.value = true;
    errorMessage.value = '';

    try {
      const result = await dashboardApi.getOverview();
      overview.value = result.data;
      source.value = result.source;
      note.value = result.note ?? '';
      lastLoadedAt.value = new Date().toLocaleString('zh-CN', { hour12: false });
    } catch (error) {
      overview.value = createEmptyOverview();
      note.value = '';
      errorMessage.value = error instanceof Error ? error.message : '仪表盘加载失败，请稍后重试。';
    } finally {
      loading.value = false;
    }
  };

  return {
    overview,
    loading,
    lastLoadedAt,
    errorMessage,
    source,
    note,
    loadOverview,
  };
});

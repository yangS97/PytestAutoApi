<template>
  <section class="page-grid">
    <div class="content-grid">
      <PlaceholderPanel
        title="用例目录占位"
        description="先固定列表结构：名称、模块、请求方法、优先级、启用状态。后续再接筛选器和编辑器。"
      >
        <p v-if="errorMessage" class="state-banner state-banner--error">{{ errorMessage }}</p>
        <div v-if="loading" class="empty-copy">正在加载用例列表...</div>

        <div v-else class="table-shell">
          <table>
            <thead>
              <tr>
                <th>用例</th>
                <th>模块</th>
                <th>方法</th>
                <th>优先级</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in cases" :key="item.id">
                <td>{{ item.name }}</td>
                <td>{{ item.module }}</td>
                <td>{{ item.method }}</td>
                <td>{{ item.priority }}</td>
                <td>
                  <StatusTag
                    :label="caseStatusLabelMap[item.status]"
                    :tone="item.status === 'active' ? 'success' : 'neutral'"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </PlaceholderPanel>

      <PlaceholderPanel
        title="页面拆分建议"
        description="这一页后续建议继续拆成更细的组件，避免所有编辑逻辑都堆在一个大页面里。"
      >
        <ul class="hint-list">
          <li>列表筛选区：模块、标签、优先级、启用状态。</li>
          <li>右侧编辑区：基础信息、请求参数、断言、变量提取、前后置 hook。</li>
          <li>保存流程：先校验结构化表单，再提交到 FastAPI 的 cases API。</li>
        </ul>
      </PlaceholderPanel>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { managementApi } from '@/api';
import PlaceholderPanel from '@/components/common/PlaceholderPanel.vue';
import StatusTag from '@/components/common/StatusTag.vue';
import type { CaseSummary } from '@/types/platform';
import { resolveApiErrorMessage } from '@/utils/apiErrors';

// 用例页当前只做“列表骨架 + 拆分建议”，
// 真实编辑器、断言设计器和变量提取面板后续再按模块拆出去。
const cases = ref<CaseSummary[]>([]);
const loading = ref(false);
const errorMessage = ref('');

const caseStatusLabelMap = {
  active: '已启用',
  draft: '草稿',
} as const;

const loadCases = async () => {
  loading.value = true;
  errorMessage.value = '';

  try {
    cases.value = await managementApi.listCases();
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, '用例列表加载失败，请稍后重试。');
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  void loadCases();
});
</script>

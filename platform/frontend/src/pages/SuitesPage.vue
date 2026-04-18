<template>
  <section class="page-grid">
    <div class="content-grid">
      <PlaceholderPanel
        title="套件目录占位"
        description="套件页负责组织执行顺序，因此这里先保留 caseCount、最近运行和调度绑定信息。"
      >
        <p v-if="errorMessage" class="state-banner state-banner--error">{{ errorMessage }}</p>
        <div v-if="loading" class="empty-copy">正在加载套件列表...</div>

        <div v-else class="table-shell">
          <table>
            <thead>
              <tr>
                <th>套件</th>
                <th>用例数</th>
                <th>最近运行</th>
                <th>调度计划</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in suites" :key="item.id">
                <td>{{ item.name }}</td>
                <td>{{ item.caseCount }}</td>
                <td>{{ item.lastRun }}</td>
                <td>{{ item.schedule }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </PlaceholderPanel>

      <PlaceholderPanel
        title="后续扩展点"
        description="套件页通常会比列表页更复杂，因为它承担依赖顺序和分组编排。"
      >
        <ul class="hint-list">
          <li>拖拽排序不是第一阶段重点，先用清晰的顺序列表和分组字段即可。</li>
          <li>前置依赖、共享变量和失败是否中断，是套件模型要优先明确的字段。</li>
          <li>调度页应该引用套件页产出的稳定 ID，而不是临时名称。</li>
        </ul>
      </PlaceholderPanel>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { managementApi } from '@/api';
import PlaceholderPanel from '@/components/common/PlaceholderPanel.vue';
import type { SuiteSummary } from '@/types/platform';
import { resolveApiErrorMessage } from '@/utils/apiErrors';

// 套件页骨架强调“执行组织能力”，
// 让后续的排序、分组、依赖关系有明确落点。
const suites = ref<SuiteSummary[]>([]);
const loading = ref(false);
const errorMessage = ref('');

const loadSuites = async () => {
  loading.value = true;
  errorMessage.value = '';

  try {
    suites.value = await managementApi.listSuites();
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, '套件列表加载失败，请稍后重试。');
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  void loadSuites();
});
</script>

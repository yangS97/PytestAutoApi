<template>
  <section class="page-grid">
    <div class="content-grid">
      <PlaceholderPanel
        title="环境配置占位"
        description="环境页用于收口 base_url、鉴权方式和环境变量，避免未来仍把这些信息散落在 YAML 或脚本里。"
      >
        <div v-if="loading" class="empty-copy">正在加载环境配置...</div>

        <div v-else class="table-shell">
          <table>
            <thead>
              <tr>
                <th>环境</th>
                <th>Base URL</th>
                <th>鉴权方式</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in environments" :key="item.id">
                <td>{{ item.name }}</td>
                <td>{{ item.baseUrl }}</td>
                <td>{{ item.authMode }}</td>
                <td>
                  <StatusTag
                    :label="environmentStatusLabelMap[item.status]"
                    :tone="item.status === 'online' ? 'success' : 'warning'"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </PlaceholderPanel>

      <PlaceholderPanel
        title="设计提示"
        description="这一页最终会影响用例执行，所以字段设计要尽量结构化，不要只留一个大文本框。"
      >
        <ul class="hint-list">
          <li>基础信息：环境名、base_url、是否默认。</li>
          <li>鉴权配置：token、cookie、租户头、自定义 signer 插件入口。</li>
          <li>环境变量：按 key-value 结构保存，方便执行时统一注入。</li>
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
import type { EnvironmentSummary } from '@/types/platform';

// 环境页先证明“环境是平台的一等资源”，
// 后续再往里补充变量编辑器、鉴权插件和敏感信息处理。
const environments = ref<EnvironmentSummary[]>([]);
const loading = ref(false);

const environmentStatusLabelMap = {
  online: '可用',
  draft: '待配置',
} as const;

const loadEnvironments = async () => {
  loading.value = true;

  try {
    environments.value = await managementApi.listEnvironments();
  } finally {
    loading.value = false;
  }
};

onMounted(loadEnvironments);
</script>


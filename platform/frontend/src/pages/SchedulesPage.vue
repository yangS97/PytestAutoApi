<template>
  <section class="page-grid">
    <div class="content-grid">
      <PlaceholderPanel
        title="调度任务占位"
        description="第一阶段调度只需轻量能力：谁在什么时间触发哪个套件或用例。"
      >
        <div v-if="loading" class="empty-copy">正在加载调度任务...</div>

        <div v-else class="table-shell">
          <table>
            <thead>
              <tr>
                <th>任务名</th>
                <th>Cron</th>
                <th>目标</th>
                <th>最近执行</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in schedules" :key="item.id">
                <td>{{ item.name }}</td>
                <td>{{ item.cron }}</td>
                <td>{{ item.target }}</td>
                <td>{{ item.lastRun }}</td>
                <td>
                  <StatusTag
                    :label="scheduleStatusLabelMap[item.status]"
                    :tone="item.status === 'active' ? 'success' : 'warning'"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </PlaceholderPanel>

      <PlaceholderPanel
        title="实现边界"
        description="平台前端先展示清晰结构，不在第一阶段过度追求可视化编排。"
      >
        <ul class="hint-list">
          <li>先支持 cron 文本、启停状态、目标选择和失败通知策略。</li>
          <li>长耗时任务执行仍交给 worker，调度页只负责配置与查看记录。</li>
          <li>若后续接入更复杂的编排器，应作为独立模块扩展，而不是挤进当前表格页。</li>
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
import type { ScheduleSummary } from '@/types/platform';

// 调度页只承接轻量计划任务，不把真正长任务执行塞进前端页面。
const schedules = ref<ScheduleSummary[]>([]);
const loading = ref(false);

const scheduleStatusLabelMap = {
  active: '已启用',
  paused: '已暂停',
} as const;

const loadSchedules = async () => {
  loading.value = true;

  try {
    schedules.value = await managementApi.listSchedules();
  } finally {
    loading.value = false;
  }
};

onMounted(loadSchedules);
</script>


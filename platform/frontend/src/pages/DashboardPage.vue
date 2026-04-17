<template>
  <section class="page-grid">
    <section class="hero-banner">
      <div>
        <p class="hero-banner__eyebrow">MVP 总览</p>
        <h2 class="hero-banner__title">先把测试资产、执行入口和运行结果收拢到同一平台。</h2>
        <p class="hero-banner__copy">
          当前页会优先请求真实的仪表盘接口；如果后端暂未提供 `dashboard/overview`，
          就退到 runs 与 health/live 的兼容聚合层；只有后端整体不可用时才使用 mock。
        </p>
      </div>

      <div class="hero-banner__meta">
        <span class="hero-banner__pill">平台主真源</span>
        <span class="hero-banner__pill">{{ appStore.phaseLabel }}</span>
        <span class="hero-banner__pill">数据源：{{ sourceLabel }}</span>
        <span class="hero-banner__pill" v-if="dashboardStore.lastLoadedAt">
          更新于 {{ dashboardStore.lastLoadedAt }}
        </span>
      </div>
    </section>

    <p v-if="dashboardStore.note" class="state-banner state-banner--info">{{ dashboardStore.note }}</p>
    <p v-if="dashboardStore.errorMessage" class="state-banner state-banner--error">
      {{ dashboardStore.errorMessage }}
    </p>

    <div v-if="dashboardStore.loading && !dashboardStore.overview.metrics.length" class="empty-copy">
      正在加载仪表盘数据...
    </div>

    <div v-else-if="dashboardStore.overview.metrics.length" class="metrics-grid">
      <MetricCard
        v-for="metric in dashboardStore.overview.metrics"
        :key="metric.key"
        :metric="metric"
      />
    </div>

    <div v-else class="empty-card">
      <p class="empty-copy">当前没有可展示的仪表盘统计数据。</p>
      <button class="action-button" type="button" :disabled="dashboardStore.loading" @click="reload">
        {{ dashboardStore.loading ? '加载中...' : '重新加载' }}
      </button>
    </div>

    <div class="content-grid">
      <PlaceholderPanel
        title="当前重点"
        description="这些卡片用于提示团队近期最值得产品化的平台能力。"
      >
        <template #actions>
          <button class="action-button" type="button" :disabled="dashboardStore.loading" @click="reload">
            {{ dashboardStore.loading ? '加载中...' : '刷新数据' }}
          </button>
        </template>

        <div v-if="dashboardStore.loading && !dashboardStore.overview.focusItems.length" class="empty-copy">
          正在整理当前重点...
        </div>

        <div v-else-if="dashboardStore.overview.focusItems.length" class="focus-list">
          <article
            v-for="item in dashboardStore.overview.focusItems"
            :key="item.id"
            class="focus-item"
          >
            <div class="focus-item__header">
              <h3>{{ item.title }}</h3>
              <StatusTag :label="focusLabelMap[item.status]" :tone="focusToneMap[item.status]" />
            </div>
            <p class="focus-item__meta">归属：{{ item.owner }}</p>
            <p class="focus-item__summary">{{ item.summary }}</p>
          </article>
        </div>

        <div v-else class="empty-copy">当前暂无重点事项，等后端补齐 overview 后可展示更细粒度建议。</div>
      </PlaceholderPanel>

      <PlaceholderPanel
        title="最近运行"
        description="结果中心未来会接入日志、响应片段和问题分析入口，这里先承接最近运行摘要。"
      >
        <div v-if="dashboardStore.loading && !dashboardStore.overview.recentRuns.length" class="empty-copy">
          正在整理最近运行...
        </div>

        <div v-else-if="dashboardStore.overview.recentRuns.length" class="run-list">
          <article
            v-for="run in dashboardStore.overview.recentRuns"
            :key="run.id"
            class="run-item"
          >
            <div class="run-item__header">
              <div>
                <h3>{{ run.name }}</h3>
                <p>{{ run.target }}</p>
              </div>
              <StatusTag
                :label="getRunStatusMeta(run.status).label"
                :tone="getRunStatusMeta(run.status).tone"
              />
            </div>
            <dl class="run-item__meta">
              <div>
                <dt>触发人</dt>
                <dd>{{ run.starter }}</dd>
              </div>
              <div>
                <dt>开始时间</dt>
                <dd>{{ run.startedAt }}</dd>
              </div>
              <div>
                <dt>耗时</dt>
                <dd>{{ run.duration }}</dd>
              </div>
            </dl>
          </article>
        </div>

        <div v-else class="empty-copy">
          当前没有可展示的最近运行摘要。若后端只有 health/live，本区会先保持空态而不伪造真实记录。
        </div>
      </PlaceholderPanel>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';

import MetricCard from '@/components/common/MetricCard.vue';
import PlaceholderPanel from '@/components/common/PlaceholderPanel.vue';
import StatusTag from '@/components/common/StatusTag.vue';
import { useAppStore } from '@/stores/app';
import { useDashboardStore } from '@/stores/dashboard';
import type { ApiDataSource } from '@/types/platform';
import { getRunStatusMeta } from '@/utils/runStatus';

const appStore = useAppStore();
const dashboardStore = useDashboardStore();

const focusToneMap = {
  stable: 'success',
  attention: 'attention',
  planned: 'neutral',
} as const;

const focusLabelMap = {
  stable: '稳定',
  attention: '需关注',
  planned: '规划中',
} as const;

const sourceLabelMap: Record<ApiDataSource, string> = {
  api: '真实接口',
  compatibility: '兼容聚合',
  mock: 'Mock 兜底',
};

const sourceLabel = computed(() => sourceLabelMap[dashboardStore.source]);

// 页面本身不再区分真实接口 / mock 的细节，统一交给 store + API 适配层收口。
const reload = async () => {
  await dashboardStore.loadOverview();
};

onMounted(async () => {
  if (!dashboardStore.overview.metrics.length && !dashboardStore.loading) {
    await reload();
  }
});
</script>

<style scoped>
.hero-banner {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 1.25rem;
  padding: 1.35rem;
  border-radius: 1.5rem;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(245, 249, 255, 0.92)),
    linear-gradient(135deg, rgba(96, 165, 250, 0.16), transparent);
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: var(--shadow-soft);
}

.hero-banner__eyebrow {
  margin: 0 0 0.55rem;
  color: var(--color-accent-strong);
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.hero-banner__title {
  margin: 0;
  font-size: clamp(1.5rem, 2vw, 2rem);
  line-height: 1.2;
  letter-spacing: -0.04em;
}

.hero-banner__copy {
  max-width: 46rem;
  margin: 0.85rem 0 0;
  color: var(--color-ink-muted);
  line-height: 1.8;
}

.hero-banner__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  align-content: flex-start;
  justify-content: flex-end;
}

.hero-banner__pill {
  display: inline-flex;
  align-items: center;
  min-height: 2.3rem;
  padding: 0.5rem 0.85rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.18);
  color: var(--color-ink-base);
  font-size: 0.88rem;
  box-shadow: var(--shadow-soft);
}

.state-banner {
  margin: 0;
  padding: 0.95rem 1rem;
  border-radius: 1rem;
  line-height: 1.7;
}

.state-banner--info {
  background: rgba(59, 130, 246, 0.08);
  color: #1d4ed8;
}

.state-banner--error {
  background: rgba(244, 63, 94, 0.08);
  color: #be123c;
}

.empty-card {
  display: grid;
  gap: 1rem;
  justify-items: start;
  padding: 1.2rem;
  border-radius: 1.2rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-soft);
}

.action-button {
  min-height: 2.25rem;
  padding: 0.55rem 0.9rem;
  border: 0;
  border-radius: 999px;
  background: var(--color-accent-strong);
  color: var(--color-ink-inverse);
  cursor: pointer;
}

.action-button:disabled {
  opacity: 0.65;
  cursor: wait;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
}

.focus-list,
.run-list {
  display: grid;
  gap: 1rem;
}

.focus-item,
.run-item {
  padding: 1rem;
  border-radius: 1rem;
  background: rgba(248, 250, 252, 0.8);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.focus-item__header,
.run-item__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.focus-item__header h3,
.run-item__header h3 {
  margin: 0;
  font-size: 1rem;
}

.focus-item__meta,
.run-item__header p {
  margin: 0.4rem 0 0;
  color: var(--color-ink-subtle);
}

.focus-item__summary {
  margin: 0.8rem 0 0;
  line-height: 1.8;
  color: var(--color-ink-muted);
}

.run-item__meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.75rem;
  margin: 0.9rem 0 0;
}

.run-item__meta dt {
  color: var(--color-ink-subtle);
  font-size: 0.82rem;
}

.run-item__meta dd {
  margin: 0.28rem 0 0;
  font-weight: 600;
}

@media (max-width: 1200px) {
  .metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 960px) {
  .hero-banner {
    grid-template-columns: 1fr;
  }

  .hero-banner__meta {
    justify-content: flex-start;
  }

  .metrics-grid,
  .run-item__meta {
    grid-template-columns: 1fr;
  }
}
</style>

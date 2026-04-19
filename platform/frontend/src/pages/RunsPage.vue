<template>
  <section class="page-grid">
    <section class="hero-banner">
      <div>
        <p class="hero-banner__eyebrow">执行结果</p>
        <h2 class="hero-banner__title">先把“最近跑了什么、现在处于什么状态”看清楚。</h2>
        <p class="hero-banner__copy">
          本页优先接真实后端的运行记录契约；如果后端暂时只有创建 run、还没有列表查询，
          前端会自动回退 mock，确保排障入口先可用。
        </p>
      </div>

      <div class="hero-banner__meta">
        <span class="hero-banner__pill">数据源：{{ sourceLabel }}</span>
        <span class="hero-banner__pill" v-if="lastLoadedAt">更新于 {{ lastLoadedAt }}</span>
      </div>
    </section>

    <div class="metrics-grid">
      <MetricCard v-for="metric in summaryMetrics" :key="metric.key" :metric="metric" />
    </div>

    <div class="content-grid">
      <PlaceholderPanel
        title="最近运行列表"
        description="左侧先看全量运行摘要，点击任意一行后，右侧详情区会切换到对应的排障视角。"
      >
        <template #actions>
          <button class="action-button" type="button" :disabled="loading" @click="reloadRuns">
            {{ loading ? '加载中...' : '重新加载' }}
          </button>
        </template>

        <p v-if="actionMessage" class="state-banner state-banner--info">{{ actionMessage }}</p>
        <p v-if="note" class="state-banner state-banner--info">{{ note }}</p>
        <p v-if="errorMessage" class="state-banner state-banner--error">{{ errorMessage }}</p>
        <p v-if="runs.length" class="panel-tip">点击某一行，可在右侧查看状态说明、原始状态和备注。</p>

        <div v-if="loading && !runs.length" class="empty-copy">正在加载运行记录...</div>

        <div v-else-if="!loading && !runs.length" class="empty-copy">
          当前还没有可展示的运行记录。等后端补齐列表接口后，这里会优先展示真实数据。
        </div>

        <div v-else class="table-shell">
          <table>
            <thead>
              <tr>
                <th>运行名称</th>
                <th>目标</th>
                <th>环境</th>
                <th>触发人</th>
                <th>开始时间</th>
                <th>耗时</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in runs"
                :key="item.id"
                class="run-row"
                :class="{ 'run-row--selected': item.id === selectedRunId }"
                tabindex="0"
                role="button"
                :aria-selected="item.id === selectedRunId"
                @click="selectRun(item.id)"
                @keydown.enter.prevent="selectRun(item.id)"
                @keydown.space.prevent="selectRun(item.id)"
              >
                <td>
                  <div class="run-name-row">
                    <div class="run-name">{{ item.name }}</div>
                    <span v-if="item.id === selectedRunId" class="run-current">当前查看</span>
                  </div>
                  <div v-if="item.rawStatus" class="run-subtle">
                    原始状态：{{ item.rawStatus }}
                  </div>
                </td>
                <td>{{ item.target }}</td>
                <td>{{ item.environmentLabel || '未绑定' }}</td>
                <td>{{ item.starter }}</td>
                <td>{{ item.startedAt }}</td>
                <td>{{ item.duration }}</td>
                <td>
                  <StatusTag
                    :label="getRunStatusMeta(item.status).label"
                    :tone="getRunStatusMeta(item.status).tone"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </PlaceholderPanel>

      <PlaceholderPanel
        title="运行详情"
        description="详情区收口状态说明、基础上下文、错误/备注和统一状态映射，页面更适合作为排障入口。"
      >
        <template #actions>
          <div class="action-row">
            <button
              class="action-button action-button--secondary"
              type="button"
              :disabled="detailLoading || !selectedRunId"
              @click="reloadSelectedRunDetail"
            >
              {{ detailLoading ? '加载中...' : '刷新详情' }}
            </button>
            <button
              class="action-button"
              type="button"
              :disabled="rerunLoading || !canRerunSelected"
              @click="rerunSelectedRun"
            >
              {{ rerunLoading ? '复跑中...' : '快速复跑' }}
            </button>
          </div>
        </template>

        <div v-if="selectedRun && selectedRunMeta && selectedRunInsight" class="detail-stack">
          <section class="detail-hero">
            <div class="detail-hero__header">
              <div>
                <p class="detail-hero__eyebrow">当前选中</p>
                <h3 class="detail-hero__title">{{ selectedRun.name }}</h3>
              </div>
              <StatusTag :label="selectedRunMeta.label" :tone="selectedRunMeta.tone" />
            </div>

            <p class="detail-hero__copy">{{ selectedRunInsight.summary }}</p>

            <div class="detail-pill-row">
              <span class="detail-pill">目标：{{ selectedRun.target }}</span>
              <span class="detail-pill">环境：{{ selectedRun.environmentLabel || '未绑定' }}</span>
              <span class="detail-pill">数据源：{{ sourceLabel }}</span>
              <span class="detail-pill">原始状态：{{ selectedRun.rawStatus || '未回传' }}</span>
            </div>
          </section>

          <section class="detail-section">
            <div class="detail-section__header">
              <h3 class="detail-section__title">基础上下文</h3>
              <p class="detail-section__copy">
                页面只保存“当前选中了哪一条”，真正的数据仍然来自左侧列表，避免详情区和列表出现双份状态。
              </p>
            </div>

            <dl class="detail-grid">
              <div v-for="field in selectedContextFields" :key="field.key" class="detail-grid__item">
                <dt>{{ field.label }}</dt>
                <dd>{{ field.value }}</dd>
              </div>
            </dl>
          </section>

          <section class="detail-section">
            <h3 class="detail-section__title">状态说明</h3>
            <p class="detail-section__copy">{{ selectedRunInsight.description }}</p>
          </section>

          <section class="detail-section">
            <h3 class="detail-section__title">错误 / 备注</h3>
            <div class="remark-list">
              <article
                v-for="item in selectedRemarkBlocks"
                :key="item.key"
                class="remark-card"
                :class="`remark-card--${item.tone}`"
              >
                <h4>{{ item.title }}</h4>
                <p>{{ item.body }}</p>
              </article>
            </div>
          </section>

          <section class="detail-section">
            <div class="detail-section__header">
              <h3 class="detail-section__title">运行快照</h3>
              <p class="detail-section__copy">
                这里优先展示真实 `run detail` 返回的状态说明、环境快照和 payload，避免只靠列表摘要猜上下文。
              </p>
            </div>

            <p v-if="detailErrorMessage" class="state-banner state-banner--error">
              {{ detailErrorMessage }}
            </p>
            <div v-else-if="detailLoading" class="empty-copy">正在加载真实运行详情...</div>
            <div v-else-if="selectedRunDetail" class="detail-snapshot">
              <article v-if="selectedRunDetail.statusMessage" class="snapshot-card">
                <h4>状态说明</h4>
                <p>{{ selectedRunDetail.statusMessage }}</p>
              </article>

              <article v-if="selectedEnvironmentSnapshotJson" class="snapshot-card">
                <h4>环境快照</h4>
                <pre>{{ selectedEnvironmentSnapshotJson }}</pre>
              </article>

              <article class="snapshot-card">
                <h4>运行 Payload</h4>
                <pre>{{ selectedPayloadJson }}</pre>
              </article>
            </div>
            <p v-else class="empty-copy">
              当前为 {{ sourceLabel }} 数据，暂不加载真实运行详情。
            </p>
          </section>

          <section class="detail-section">
            <h3 class="detail-section__title">建议下一步</h3>
            <ul class="hint-list">
              <li v-for="step in selectedRunInsight.nextSteps" :key="step">{{ step }}</li>
            </ul>
          </section>

          <section class="detail-section">
            <h3 class="detail-section__title">状态映射说明</h3>
            <div class="side-stack">
              <div class="status-legend">
                <div v-for="item in legendItems" :key="item.key" class="status-legend__row">
                  <StatusTag :label="item.label" :tone="item.tone" />
                  <p>{{ item.description }}</p>
                </div>
              </div>

              <ul class="hint-list">
                <li>`queued / pending` 会统一展示为“排队中”。</li>
                <li>`succeeded / passed` 会统一展示为“成功”。</li>
                <li>`warning / partial_success` 会统一展示为“告警”。</li>
                <li>如果真实列表接口缺失，页面会自动回退 mock，并在上方给出提示。</li>
              </ul>
            </div>
          </section>
        </div>

        <div v-else class="empty-copy">请选择一条运行记录后查看详情。</div>
      </PlaceholderPanel>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { executionApi, managementApi } from '@/api';
import MetricCard from '@/components/common/MetricCard.vue';
import PlaceholderPanel from '@/components/common/PlaceholderPanel.vue';
import StatusTag from '@/components/common/StatusTag.vue';
import type { ApiDataSource, DashboardMetric, RunDetail, RunSummary } from '@/types/platform';
import { resolveApiErrorMessage } from '@/utils/apiErrors';
import { getRunStatusInsight, getRunStatusMeta } from '@/utils/runStatus';
import { resolveSuiteRunPreset } from '@/utils/suiteRunPresets';

interface RunDetailField {
  key: string;
  label: string;
  value: string;
}

interface RunRemarkBlock {
  key: string;
  title: string;
  body: string;
  tone: 'info' | 'error' | 'neutral';
}

type UnknownRecord = Record<string, unknown>;

const isRecord = (value: unknown): value is UnknownRecord =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const route = useRoute();
const router = useRouter();

const runs = ref<RunSummary[]>([]);
const loading = ref(false);
const detailLoading = ref(false);
const rerunLoading = ref(false);
const errorMessage = ref('');
const detailErrorMessage = ref('');
const actionMessage = ref('');
const note = ref('');
const source = ref<ApiDataSource>('mock');
const lastLoadedAt = ref('');
const selectedRunId = ref('');
const selectedRunDetail = ref<RunDetail | null>(null);

const sourceLabelMap: Record<ApiDataSource, string> = {
  api: '真实接口',
  compatibility: '兼容聚合',
  mock: 'Mock 兜底',
};

const sourceLabel = computed(() => sourceLabelMap[source.value]);
const routeRunId = computed(() => (typeof route.query.runId === 'string' ? route.query.runId : ''));

let detailRequestToken = 0;

const summaryMetrics = computed<DashboardMetric[]>(() => {
  const successCount = runs.value.filter((item) => item.status === 'success').length;
  const failedCount = runs.value.filter(
    (item) => item.status === 'failed' || item.status === 'warning',
  ).length;
  const inflightCount = runs.value.filter(
    (item) => item.status === 'queued' || item.status === 'running',
  ).length;

  return [
    {
      key: 'runs-total',
      label: '运行总数',
      value: String(runs.value.length),
      description: '当前页已经拿到并展示的运行记录数量',
      trend: source.value === 'api' ? '来自真实后端' : '当前为 mock/兼容数据',
    },
    {
      key: 'runs-success',
      label: '成功数',
      value: String(successCount),
      description: '方便快速判断最近一批运行是否稳定',
      trend: failedCount ? `失败/告警 ${failedCount}` : '暂无失败',
    },
    {
      key: 'runs-inflight',
      label: '排队/执行中',
      value: String(inflightCount),
      description: '排障时先判断是否还在执行或卡在等待调度',
      trend: inflightCount ? '建议关注最新队列' : '当前无积压',
    },
  ];
});

const legendItems = computed(() => [
  {
    key: 'queued',
    ...getRunStatusMeta('queued'),
    description: '后端常见原始值：queued / pending',
  },
  {
    key: 'running',
    ...getRunStatusMeta('running'),
    description: '后端常见原始值：running / in_progress',
  },
  {
    key: 'success',
    ...getRunStatusMeta('success'),
    description: '后端常见原始值：succeeded / passed',
  },
  {
    key: 'failed',
    ...getRunStatusMeta('failed'),
    description: '后端常见原始值：failed / error',
  },
  {
    key: 'warning',
    ...getRunStatusMeta('warning'),
    description: '后端常见原始值：warning / partial_success',
  },
]);

const updateRouteRunId = (runId: string) => {
  const nextQuery = { ...route.query };

  if (runId) {
    nextQuery.runId = runId;
  } else {
    delete nextQuery.runId;
  }

  void router.replace({ query: nextQuery });
};

const applySelectedRunId = (runId: string) => {
  selectedRunId.value = runId;
  if (routeRunId.value !== runId) {
    updateRouteRunId(runId);
  }
};

const selectRun = (runId: string) => {
  applySelectedRunId(runId);
};

/**
 * 详情面板只维护“当前选中的 run id”。
 * 这样列表重新加载后，只需要决定选中谁，不必再维护一份可能过期的详情对象。
 */
const syncSelectedRun = (nextRuns: RunSummary[], preferredRunId = routeRunId.value) => {
  if (!nextRuns.length) {
    selectedRunId.value = '';
    selectedRunDetail.value = null;
    if (routeRunId.value) {
      updateRouteRunId('');
    }
    return;
  }

  if (preferredRunId && nextRuns.some((item) => item.id === preferredRunId)) {
    applySelectedRunId(preferredRunId);
    return;
  }

  if (selectedRunId.value && nextRuns.some((item) => item.id === selectedRunId.value)) {
    if (routeRunId.value !== selectedRunId.value) {
      updateRouteRunId(selectedRunId.value);
    }
    return;
  }

  applySelectedRunId(nextRuns[0].id);
};

const selectedRun = computed(() => runs.value.find((item) => item.id === selectedRunId.value) ?? null);
const selectedRunMeta = computed(() => {
  const run = selectedRun.value;
  return run ? getRunStatusMeta(run.status) : null;
});

/**
 * 状态映射、说明文案和排障建议统一收口在 `runStatus.ts`。
 * RunsPage 只负责“加载数据 + 选中记录 + 组装详情视图”，避免页面里散落一堆状态判断。
 */
const selectedRunInsight = computed(() => {
  const run = selectedRun.value;
  return run ? getRunStatusInsight(run.status) : null;
});

const rerunnableSuiteId = computed(
  () => selectedRunDetail.value?.suiteId || selectedRun.value?.suiteId || '',
);
const canRerunSelected = computed(
  () => !!rerunnableSuiteId.value && resolveSuiteRunPreset(rerunnableSuiteId.value) !== null,
);

/**
 * target 目前仍是松散字符串契约，所以这里只做轻量拆分：
 * - `suite/payment-regression` -> 套件 + payment-regression
 * - 其他未知前缀 -> 自定义目标
 */
const inferTargetContext = (target: string) => {
  const normalizedTarget = target.trim();

  if (!normalizedTarget) {
    return {
      kind: '未标记',
      identifier: '未提供',
    };
  }

  const segments = normalizedTarget.split('/').filter(Boolean);
  const targetKindLabelMap: Record<string, string> = {
    suite: '套件',
    case: '用例',
    schedule: '调度任务',
    env: '环境',
    environment: '环境',
  };

  return {
    kind: targetKindLabelMap[segments[0]?.toLowerCase() ?? ''] ?? '自定义目标',
    identifier: segments.slice(1).join('/') || normalizedTarget,
  };
};

const selectedContextFields = computed<RunDetailField[]>(() => {
  const run = selectedRun.value;
  const detail = selectedRunDetail.value;

  if (!run) {
    return [];
  }

  const targetContext = inferTargetContext(run.target);

  return [
    {
      key: 'target',
      label: '目标',
      value: run.target,
    },
    {
      key: 'target-kind',
      label: '目标类型',
      value: targetContext.kind,
    },
    {
      key: 'target-identifier',
      label: '目标标识',
      value: targetContext.identifier,
    },
    {
      key: 'suite-id',
      label: '套件 ID',
      value: detail?.suiteId || run.suiteId || '未回传',
    },
    {
      key: 'environment',
      label: '环境',
      value: run.environmentLabel || '未绑定',
    },
    {
      key: 'requested-by',
      label: '请求人',
      value: detail?.requestedBy || run.starter,
    },
    {
      key: 'trigger-source',
      label: '触发来源',
      value: detail?.triggerSource || '未回传',
    },
    {
      key: 'started-at',
      label: '开始时间',
      value: run.startedAt,
    },
    {
      key: 'duration',
      label: '耗时',
      value: run.duration,
    },
    {
      key: 'source',
      label: '数据源',
      value: sourceLabel.value,
    },
    {
      key: 'raw-status',
      label: '原始状态',
      value: run.rawStatus || '未回传，按展示状态处理',
    },
  ];
});

const buildStatusRemark = (run: RunSummary) => {
  switch (run.status) {
    case 'queued':
      return '当前运行还在等待调度，优先确认队列是否积压、worker 是否空闲。';
    case 'running':
      return '当前运行仍在进行中，建议先从长耗时步骤和外部依赖入手排查。';
    case 'success':
      return '当前运行已经成功完成，如果业务仍异常，下一步应该继续核对日志和结果数据。';
    case 'failed':
      return '当前运行已经失败，建议优先查看失败步骤、错误摘要以及最近变更。';
    case 'warning':
      return '当前运行处于告警态，代表还有需要人工确认的非阻塞异常。';
    default:
      return '当前运行状态需要进一步确认。';
  }
};

const selectedRemarkBlocks = computed<RunRemarkBlock[]>(() => {
  const run = selectedRun.value;
  const detail = selectedRunDetail.value;

  if (!run) {
    return [];
  }

  const primaryBody = detail?.statusMessage || run.errorSummary || buildStatusRemark(run);
  const blocks: RunRemarkBlock[] = [
    {
      key: 'status-remark',
      title: detail?.statusMessage ? '执行状态说明' : run.status === 'failed' ? '异常提示' : '运行备注',
      body: primaryBody,
      tone: run.status === 'failed' ? 'error' : 'info',
    },
  ];

  if (run.note) {
    blocks.push({
      key: 'run-note',
      title: '执行侧备注',
      body: run.note,
      tone: 'neutral',
    });
  }

  if (note.value) {
    blocks.push({
      key: 'data-source-note',
      title: '数据源备注',
      body: note.value,
      tone: 'info',
    });
  }

  if (run.rawStatus) {
    blocks.push({
      key: 'status-mapping-note',
      title: '状态映射',
      body: `后端原始状态 ${run.rawStatus} 会统一映射为 ${getRunStatusMeta(run.status).label}，这样不同接口枚举也能共用同一套页面判断。`,
      tone: 'neutral',
    });
  }

  return blocks;
});

const selectedEnvironmentSnapshotJson = computed(() => {
  const environment = selectedRunDetail.value?.payload.environment;

  if (!isRecord(environment)) {
    return '';
  }

  return JSON.stringify(environment, null, 2);
});

const selectedPayloadJson = computed(() => {
  if (!selectedRunDetail.value) {
    return '';
  }

  return JSON.stringify(selectedRunDetail.value.payload, null, 2);
});

const loadSelectedRunDetail = async () => {
  if (!selectedRunId.value || source.value !== 'api') {
    detailLoading.value = false;
    detailErrorMessage.value = '';
    selectedRunDetail.value = null;
    return;
  }

  const requestToken = ++detailRequestToken;
  detailLoading.value = true;
  detailErrorMessage.value = '';
  selectedRunDetail.value = null;

  try {
    const detail = await executionApi.getRunDetail(selectedRunId.value);
    if (requestToken !== detailRequestToken) {
      return;
    }

    selectedRunDetail.value = detail;
  } catch (error) {
    if (requestToken !== detailRequestToken) {
      return;
    }

    selectedRunDetail.value = null;
    detailErrorMessage.value = resolveApiErrorMessage(error, '运行详情加载失败，请稍后重试。');
  } finally {
    if (requestToken === detailRequestToken) {
      detailLoading.value = false;
    }
  }
};

const reloadSelectedRunDetail = async () => {
  await loadSelectedRunDetail();
};

const rerunSelectedRun = async () => {
  const suiteId = rerunnableSuiteId.value;
  if (!suiteId) {
    return;
  }

  rerunLoading.value = true;
  detailErrorMessage.value = '';

  try {
    const detail = await executionApi.runSuiteNow(suiteId);
    actionMessage.value = `已基于套件 ${suiteId} 重新发起并执行一条运行。`;
    await loadRuns({ preferredRunId: detail.id });
  } catch (error) {
    detailErrorMessage.value = resolveApiErrorMessage(error, '快速复跑失败，请稍后重试。');
  } finally {
    rerunLoading.value = false;
  }
};

const reloadRuns = async () => {
  await loadRuns();
};

/**
 * 页面只关心“要展示什么状态”：
 * 真实接口、mock 兜底、来源标识、最后更新时间、默认选中项，
 * 都在加载函数里一次性收口，避免模板里再分散处理。
 */
const loadRuns = async (options?: { preferredRunId?: string }) => {
  loading.value = true;
  errorMessage.value = '';

  try {
    const result = await managementApi.listRuns();
    runs.value = result.data;
    source.value = result.source;
    note.value = result.note ?? '';
    syncSelectedRun(result.data, options?.preferredRunId || routeRunId.value);
    lastLoadedAt.value = new Date().toLocaleString('zh-CN', { hour12: false });
  } catch (error) {
    runs.value = [];
    note.value = '';
    selectedRunId.value = '';
    selectedRunDetail.value = null;
    lastLoadedAt.value = '';
    errorMessage.value = resolveApiErrorMessage(error, '运行记录加载失败，请稍后重试。');
  } finally {
    loading.value = false;
  }
};

watch(routeRunId, (runId) => {
  if (!runId) {
    return;
  }

  if (runId !== selectedRunId.value && runs.value.some((item) => item.id === runId)) {
    selectedRunId.value = runId;
  }
});

watch(
  () => [selectedRunId.value, source.value],
  () => {
    void loadSelectedRunDetail();
  },
);

onMounted(() => {
  void loadRuns();
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
    linear-gradient(135deg, rgba(255, 195, 113, 0.16), transparent);
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

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
}

.action-row {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.panel-tip {
  margin: 0;
  color: var(--color-ink-subtle);
  line-height: 1.75;
}

.run-name {
  font-weight: 700;
}

.run-name-row {
  display: flex;
  gap: 0.55rem;
  align-items: center;
  flex-wrap: wrap;
}

.run-current {
  display: inline-flex;
  align-items: center;
  min-height: 1.45rem;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.1);
  color: #1d4ed8;
  font-size: 0.74rem;
  font-weight: 700;
}

.run-subtle {
  margin-top: 0.35rem;
  color: var(--color-ink-subtle);
  font-size: 0.82rem;
}

.run-row {
  cursor: pointer;
  outline: none;
}

.run-row td {
  transition:
    background-color 160ms ease,
    color 160ms ease;
}

.run-row:hover td {
  background: rgba(248, 250, 252, 0.88);
}

.run-row--selected td {
  background: rgba(219, 234, 254, 0.65);
}

.run-row:focus-visible {
  outline: 2px solid rgba(59, 130, 246, 0.38);
  outline-offset: -2px;
}

.side-stack,
.status-legend {
  display: grid;
  gap: 1rem;
}

.detail-snapshot {
  display: grid;
  gap: 0.85rem;
}

.detail-stack {
  display: grid;
  gap: 1rem;
}

.detail-hero,
.detail-section {
  display: grid;
  gap: 0.85rem;
  padding: 1rem;
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.detail-hero {
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(239, 246, 255, 0.88)),
    linear-gradient(135deg, rgba(59, 130, 246, 0.08), transparent);
}

.detail-hero__header,
.detail-section__header {
  display: flex;
  gap: 0.85rem;
  justify-content: space-between;
  align-items: flex-start;
}

.detail-hero__eyebrow {
  margin: 0 0 0.4rem;
  color: var(--color-accent-strong);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.detail-hero__title,
.detail-section__title {
  margin: 0;
  font-size: 1rem;
}

.detail-hero__copy,
.detail-section__copy {
  margin: 0;
  color: var(--color-ink-muted);
  line-height: 1.8;
}

.detail-pill-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.detail-pill {
  display: inline-flex;
  align-items: center;
  min-height: 2rem;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.16);
  color: var(--color-ink-base);
  font-size: 0.82rem;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
  margin: 0;
}

.detail-grid__item {
  padding: 0.85rem 0.9rem;
  border-radius: 0.95rem;
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.detail-grid__item dt {
  margin: 0;
  color: var(--color-ink-subtle);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.detail-grid__item dd {
  margin: 0.45rem 0 0;
  color: var(--color-ink-base);
  line-height: 1.75;
  word-break: break-word;
}

.remark-list {
  display: grid;
  gap: 0.75rem;
}

.remark-card {
  padding: 0.9rem 1rem;
  border-radius: 1rem;
  border: 1px solid transparent;
}

.remark-card h4,
.remark-card p {
  margin: 0;
}

.remark-card h4 {
  font-size: 0.92rem;
}

.remark-card p {
  margin-top: 0.45rem;
  line-height: 1.8;
}

.remark-card--info {
  background: rgba(59, 130, 246, 0.08);
  border-color: rgba(59, 130, 246, 0.12);
  color: #1d4ed8;
}

.remark-card--error {
  background: rgba(244, 63, 94, 0.08);
  border-color: rgba(244, 63, 94, 0.12);
  color: #be123c;
}

.remark-card--neutral {
  background: rgba(15, 23, 42, 0.04);
  border-color: rgba(148, 163, 184, 0.14);
  color: var(--color-ink-base);
}

.snapshot-card {
  display: grid;
  gap: 0.6rem;
  padding: 0.95rem 1rem;
  border-radius: 1rem;
  background: rgba(248, 250, 252, 0.88);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.snapshot-card h4,
.snapshot-card pre {
  margin: 0;
}

.snapshot-card h4 {
  font-size: 0.92rem;
}

.snapshot-card pre {
  padding: 0.85rem 0.95rem;
  border-radius: 0.9rem;
  background: rgba(15, 23, 42, 0.94);
  color: rgba(226, 232, 240, 0.96);
  overflow-x: auto;
  line-height: 1.65;
  font-size: 0.84rem;
}

.status-legend__row {
  display: grid;
  gap: 0.55rem;
  padding: 0.9rem 1rem;
  border-radius: 1rem;
  background: rgba(248, 250, 252, 0.8);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.status-legend__row p {
  margin: 0;
  color: var(--color-ink-muted);
  line-height: 1.75;
}

@media (max-width: 1200px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 960px) {
  .hero-banner {
    grid-template-columns: 1fr;
  }

  .hero-banner__meta {
    justify-content: flex-start;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>

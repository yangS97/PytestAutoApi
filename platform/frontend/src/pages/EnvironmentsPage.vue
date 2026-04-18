<template>
  <section class="page-grid">
    <div class="content-grid">
      <PlaceholderPanel
        title="环境目录"
        description="环境页负责把 base_url、鉴权方式和执行上下文收口到平台主真源里，避免这些配置继续散落在 YAML 和脚本里。"
      >
        <template #actions>
          <div class="action-row">
            <button
              class="action-button action-button--secondary"
              type="button"
              :disabled="saving || deleting || detailLoading"
              @click="startCreateMode"
            >
              新增环境
            </button>
            <button class="action-button" type="button" :disabled="loading" @click="loadEnvironments()">
              {{ loading ? '加载中...' : '重新加载' }}
            </button>
          </div>
        </template>

        <p v-if="note" class="state-banner state-banner--info">{{ note }}</p>
        <p v-if="errorMessage" class="state-banner state-banner--error">{{ errorMessage }}</p>
        <p v-if="environments.length" class="panel-tip">点击任意一行，可在右侧切换到编辑视角。</p>

        <div v-if="loading && !environments.length" class="empty-copy">正在加载环境配置...</div>

        <div v-else-if="!loading && !environments.length" class="empty-copy">
          当前还没有环境目录数据。可先在右侧创建一个新的执行环境。
        </div>

        <div v-else class="table-shell">
          <table>
            <thead>
              <tr>
                <th>环境</th>
                <th>Base URL</th>
                <th>鉴权方式</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in environments"
                :key="item.id"
                class="environment-row"
                :class="{ 'environment-row--selected': item.id === selectedEnvironmentId }"
                tabindex="0"
                role="button"
                :aria-selected="item.id === selectedEnvironmentId"
                @click="startEditMode(item.id)"
                @keydown.enter.prevent="startEditMode(item.id)"
                @keydown.space.prevent="startEditMode(item.id)"
              >
                <td>
                  <div class="environment-name-row">
                    <span class="environment-name">{{ item.name }}</span>
                    <span v-if="item.id === selectedEnvironmentId" class="environment-current">当前编辑</span>
                  </div>
                </td>
                <td>{{ item.baseUrl }}</td>
                <td>{{ item.authMode }}</td>
                <td>
                  <StatusTag
                    :label="environmentStatusLabelMap[item.status]"
                    :tone="item.status === 'online' ? 'success' : 'warning'"
                  />
                </td>
                <td>
                  <button
                    class="action-link"
                    type="button"
                    :disabled="detailLoading && item.id === selectedEnvironmentId"
                    @click.stop="startEditMode(item.id)"
                  >
                    编辑
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </PlaceholderPanel>

      <PlaceholderPanel
        :title="formPanelTitle"
        :description="formPanelDescription"
      >
        <p v-if="detailLoading" class="empty-copy">正在加载环境详情...</p>

        <form class="environment-form" @submit.prevent="submitEnvironment">
          <section v-if="formMode === 'edit' && currentEnvironmentDetail" class="environment-hero">
            <div class="environment-hero__header">
              <div>
                <p class="environment-hero__eyebrow">当前编辑</p>
                <h3 class="environment-hero__title">{{ currentEnvironmentDetail.name }}</h3>
              </div>
              <StatusTag
                :label="environmentStatusLabelMap[currentEnvironmentDetail.status]"
                :tone="currentEnvironmentDetail.status === 'online' ? 'success' : 'warning'"
              />
            </div>

            <div class="detail-pill-row">
              <span class="detail-pill">ID：{{ currentEnvironmentDetail.id }}</span>
              <span class="detail-pill">
                变量数：{{ Object.keys(currentEnvironmentDetail.variables).length }}
              </span>
              <span class="detail-pill">Base URL：{{ currentEnvironmentDetail.baseUrl }}</span>
            </div>

            <p class="form-tip">
              当前还没有变量编辑器；这轮更新基础字段时会保留已有 variables，不会被 patch 覆盖掉。
            </p>
          </section>

          <div class="form-grid">
            <label class="field-stack">
              <span>环境名称</span>
              <input
                v-model.trim="formState.name"
                type="text"
                maxlength="32"
                placeholder="例如：预发联调环境"
                required
              />
            </label>

            <label class="field-stack">
              <span>Base URL</span>
              <input
                v-model.trim="formState.baseUrl"
                type="url"
                placeholder="https://staging.example.com"
                required
              />
            </label>

            <label class="field-stack">
              <span>鉴权方式</span>
              <select v-model="formState.authMode">
                <option v-for="item in authModeOptions" :key="item" :value="item">
                  {{ item }}
                </option>
              </select>
            </label>

            <label class="field-stack">
              <span>状态</span>
              <select v-model="formState.status">
                <option value="draft">待配置</option>
                <option value="online">可用</option>
              </select>
            </label>
          </div>

          <div class="form-actions">
            <button class="action-button" type="submit" :disabled="saving || detailLoading">
              {{ primaryActionLabel }}
            </button>
            <button
              v-if="formMode === 'edit'"
              class="action-button action-button--secondary"
              type="button"
              :disabled="saving || deleting"
              @click="startCreateMode"
            >
              取消编辑
            </button>
            <button
              v-if="formMode === 'edit'"
              class="action-button action-button--danger"
              type="button"
              :disabled="deleting || saving"
              @click="removeEnvironment"
            >
              {{ deleting ? '删除中...' : '删除环境' }}
            </button>
            <p class="form-tip">{{ formTip }}</p>
          </div>
        </form>

        <ul class="hint-list">
          <li>第一阶段先把环境做成平台的一等资源，停止继续依赖仓库硬编码地址。</li>
          <li>这轮已经补到资源完整闭环，后续可以在同一资源上继续长变量、密钥引用和 signer 配置。</li>
          <li>如果后续接入 worker 真执行，环境页会成为 run 创建时的重要输入源。</li>
        </ul>
      </PlaceholderPanel>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { managementApi } from '@/api';
import PlaceholderPanel from '@/components/common/PlaceholderPanel.vue';
import StatusTag from '@/components/common/StatusTag.vue';
import type {
  CreateEnvironmentPayload,
  EnvironmentDetail,
  EnvironmentSummary,
  UpdateEnvironmentPayload,
} from '@/types/platform';
import { resolveApiErrorMessage } from '@/utils/apiErrors';

type EnvironmentFormMode = 'create' | 'edit';

// 环境页先把“平台主真源里的环境资源”做实。
// 真执行接入时，run/schedule 都应该引用这里的环境，而不是继续拼散落配置。
const environments = ref<EnvironmentSummary[]>([]);
const loading = ref(false);
const detailLoading = ref(false);
const saving = ref(false);
const deleting = ref(false);
const note = ref('');
const errorMessage = ref('');
const formMode = ref<EnvironmentFormMode>('create');
const selectedEnvironmentId = ref('');
const currentEnvironmentDetail = ref<EnvironmentDetail | null>(null);

const environmentStatusLabelMap = {
  online: '可用',
  draft: '待配置',
} as const;

const authModeOptions = [
  '账号密码登录 + Token 注入',
  'Cookie + 单点登录',
  '自定义签名插件',
] as const;

const formState = ref<CreateEnvironmentPayload>({
  name: '',
  baseUrl: '',
  authMode: authModeOptions[0],
  status: 'draft',
});

const resetFormState = () => {
  formState.value = {
    name: '',
    baseUrl: '',
    authMode: authModeOptions[0],
    status: 'draft',
  };
};

const applyFormState = (payload: UpdateEnvironmentPayload) => {
  formState.value = {
    name: payload.name ?? '',
    baseUrl: payload.baseUrl ?? '',
    authMode: payload.authMode ?? authModeOptions[0],
    status: payload.status ?? 'draft',
  };
};

const formPanelTitle = computed(() =>
  formMode.value === 'edit' ? '编辑环境' : '新增环境',
);

const formPanelDescription = computed(() =>
  formMode.value === 'edit'
    ? '编辑模式会直接更新平台目录中的真实环境资源，并保留尚未可视化的 variables。'
    : '先把环境资源做成真实平台输入项，而不是继续依赖仓库里的硬编码地址。'
);

const primaryActionLabel = computed(() => {
  if (formMode.value === 'edit') {
    return saving.value ? '保存中...' : '保存修改';
  }
  return saving.value ? '保存中...' : '保存环境';
});

const formTip = computed(() =>
  formMode.value === 'edit'
    ? '保存后会刷新左侧目录，并保持当前环境选中。'
    : '保存成功后会自动切到新环境的编辑态，便于继续补充配置。'
);

const startCreateMode = () => {
  formMode.value = 'create';
  selectedEnvironmentId.value = '';
  currentEnvironmentDetail.value = null;
  detailLoading.value = false;
  resetFormState();
};

const startEditMode = async (environmentId: string, options?: { silent?: boolean }) => {
  detailLoading.value = true;
  selectedEnvironmentId.value = environmentId;
  formMode.value = 'edit';

  if (!options?.silent) {
    note.value = '';
    errorMessage.value = '';
  }

  try {
    const detail = await managementApi.getEnvironmentDetail(environmentId);
    currentEnvironmentDetail.value = detail;
    applyFormState(detail);
  } catch (error) {
    currentEnvironmentDetail.value = null;
    errorMessage.value = resolveApiErrorMessage(error, '环境详情加载失败，请稍后重试。');
  } finally {
    detailLoading.value = false;
  }
};

const loadEnvironments = async (options?: { preferredId?: string; preserveSelection?: boolean }) => {
  loading.value = true;
  errorMessage.value = '';

  try {
    environments.value = await managementApi.listEnvironments();
    const preferredId = options?.preferredId;
    const preservedId =
      options?.preserveSelection && selectedEnvironmentId.value
        ? selectedEnvironmentId.value
        : '';
    const nextSelectedId = preferredId || preservedId;

    if (nextSelectedId && environments.value.some((item) => item.id === nextSelectedId)) {
      await startEditMode(nextSelectedId, { silent: true });
    } else if (formMode.value === 'edit') {
      startCreateMode();
    }
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, '环境目录加载失败，请稍后重试。');
  } finally {
    loading.value = false;
  }
};

const submitEnvironment = async () => {
  saving.value = true;
  note.value = '';
  errorMessage.value = '';

  try {
    if (formMode.value === 'edit' && selectedEnvironmentId.value) {
      const updated = await managementApi.updateEnvironment(selectedEnvironmentId.value, formState.value);
      note.value = `环境已更新：${updated.name}。`;
      await loadEnvironments({ preferredId: updated.id });
      return;
    }

    const created = await managementApi.createEnvironment(formState.value);
      note.value = `环境已创建：${created.name}，当前已回写到平台目录。`;
      await loadEnvironments({ preferredId: created.id });
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, '保存环境失败，请稍后重试。');
  } finally {
    saving.value = false;
  }
};

const removeEnvironment = async () => {
  if (!selectedEnvironmentId.value || !currentEnvironmentDetail.value) {
    return;
  }

  const shouldDelete = window.confirm(`确认删除环境「${currentEnvironmentDetail.value.name}」吗？`);
  if (!shouldDelete) {
    return;
  }

  deleting.value = true;
  note.value = '';
  errorMessage.value = '';

  try {
    const deleted = await managementApi.deleteEnvironment(selectedEnvironmentId.value);
    startCreateMode();
    await loadEnvironments();
    note.value = `环境已删除：${deleted.name}。`;
  } catch (error) {
    errorMessage.value = resolveApiErrorMessage(error, '删除环境失败，请稍后重试。');
  } finally {
    deleting.value = false;
  }
};

onMounted(() => {
  void loadEnvironments();
});
</script>

<style scoped>
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

.environment-row {
  cursor: pointer;
  transition: background 180ms ease, transform 180ms ease;
}

.environment-row:hover {
  background: rgba(95, 124, 255, 0.05);
}

.environment-row--selected {
  background: rgba(95, 124, 255, 0.08);
}

.environment-name-row {
  display: flex;
  gap: 0.55rem;
  align-items: center;
  flex-wrap: wrap;
}

.environment-name {
  font-weight: 700;
}

.environment-current {
  display: inline-flex;
  align-items: center;
  min-height: 1.45rem;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.1);
  color: #1d4ed8;
  font-size: 0.78rem;
}

.action-link {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-accent-strong);
  cursor: pointer;
}

.action-link:disabled {
  opacity: 0.65;
  cursor: wait;
}

.environment-form {
  display: grid;
  gap: 1rem;
}

.environment-hero {
  display: grid;
  gap: 0.85rem;
  padding: 1rem;
  border-radius: 1rem;
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.environment-hero__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.environment-hero__eyebrow {
  margin: 0 0 0.35rem;
  color: var(--color-ink-subtle);
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.environment-hero__title {
  margin: 0;
  font-size: 1.05rem;
}

.detail-pill-row {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.detail-pill {
  display: inline-flex;
  align-items: center;
  min-height: 1.8rem;
  padding: 0.18rem 0.65rem;
  border-radius: 999px;
  background: rgba(95, 124, 255, 0.1);
  color: var(--color-accent-strong);
  font-size: 0.82rem;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
}

.field-stack {
  display: grid;
  gap: 0.45rem;
  color: var(--color-ink-muted);
  font-size: 0.92rem;
}

.field-stack span {
  font-weight: 600;
  color: var(--color-ink-base);
}

.form-actions {
  display: flex;
  gap: 0.9rem;
  align-items: center;
  flex-wrap: wrap;
}

.form-tip {
  margin: 0;
  color: var(--color-ink-subtle);
  line-height: 1.7;
}

@media (max-width: 720px) {
  .action-row,
  .environment-hero__header,
  .detail-pill-row,
  .form-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>

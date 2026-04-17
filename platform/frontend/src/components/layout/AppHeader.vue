<template>
  <header class="app-header">
    <div>
      <p class="app-header__eyebrow">{{ appStore.currentNavigation?.label ?? '平台首页' }}</p>
      <h1 class="app-header__title">{{ route.meta.title }}</h1>
      <p class="app-header__description">{{ route.meta.description }}</p>
    </div>

    <div class="app-header__summary">
      <div class="app-header__summary-card">
        <span>架构</span>
        <strong>FastAPI + Vue 3 + Worker</strong>
      </div>
      <div class="app-header__summary-card">
        <span>团队尺度</span>
        <strong>1-3 人协作优先</strong>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router';

import { useAppStore } from '@/stores/app';

const route = useRoute();
const appStore = useAppStore();
</script>

<style scoped>
.app-header {
  display: flex;
  justify-content: space-between;
  gap: 1.5rem;
  align-items: flex-start;
  padding: 1.75rem 0 1.25rem;
}

.app-header__eyebrow {
  margin: 0 0 0.5rem;
  color: var(--color-accent-strong);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.app-header__title {
  margin: 0;
  font-size: clamp(1.9rem, 2vw, 2.6rem);
  line-height: 1.1;
  letter-spacing: -0.04em;
}

.app-header__description {
  max-width: 50rem;
  margin: 0.75rem 0 0;
  color: var(--color-ink-muted);
  line-height: 1.8;
}

.app-header__summary {
  display: grid;
  gap: 0.85rem;
  min-width: 17rem;
}

.app-header__summary-card {
  display: grid;
  gap: 0.35rem;
  padding: 0.95rem 1rem;
  border-radius: 1rem;
  background: var(--color-surface-strong);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-soft);
}

.app-header__summary-card span {
  color: var(--color-ink-subtle);
  font-size: 0.82rem;
}

.app-header__summary-card strong {
  font-size: 0.95rem;
}

@media (max-width: 960px) {
  .app-header {
    flex-direction: column;
  }

  .app-header__summary {
    min-width: 100%;
    grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
  }
}
</style>


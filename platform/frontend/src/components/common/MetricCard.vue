<template>
  <article class="metric-card">
    <p class="metric-card__label">{{ metric.label }}</p>
    <strong class="metric-card__value">{{ metric.value }}</strong>
    <p class="metric-card__description">{{ metric.description }}</p>
    <p class="metric-card__trend">{{ metric.trend }}</p>
  </article>
</template>

<script setup lang="ts">
import type { DashboardMetric } from '@/types/platform';

defineProps<{
  metric: DashboardMetric;
}>();
</script>

<style scoped>
.metric-card {
  padding: 1.2rem;
  border-radius: 1.2rem;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(250, 252, 255, 0.96));
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-soft);
}

.metric-card__label {
  margin: 0;
  font-size: 0.9rem;
  color: var(--color-ink-muted);
}

.metric-card__value {
  display: block;
  margin-top: 0.65rem;
  font-size: 2rem;
  line-height: 1;
  letter-spacing: -0.05em;
}

.metric-card__description {
  margin: 0.75rem 0 0;
  color: var(--color-ink-subtle);
  line-height: 1.7;
}

.metric-card__trend {
  margin: 0.85rem 0 0;
  color: var(--color-accent-strong);
  font-weight: 700;
  font-size: 0.9rem;
}
</style>


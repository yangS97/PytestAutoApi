<template>
  <span class="status-tag" :class="`status-tag--${tone}`">{{ label }}</span>
</template>

<script setup lang="ts">
import type { StatusTone } from '@/types/platform';

defineProps<{
  label: string;
  tone: StatusTone;
}>();
</script>

<style scoped>
.status-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 4.6rem;
  padding: 0.3rem 0.7rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.status-tag--success {
  background: rgba(22, 163, 74, 0.12);
  color: #166534;
}

.status-tag--warning {
  background: rgba(245, 158, 11, 0.16);
  color: #9a3412;
}

.status-tag--running {
  background: rgba(59, 130, 246, 0.14);
  color: #1d4ed8;
}

.status-tag--neutral {
  background: rgba(100, 116, 139, 0.12);
  color: #334155;
}

.status-tag--attention {
  background: rgba(244, 63, 94, 0.12);
  color: #be123c;
}
</style>

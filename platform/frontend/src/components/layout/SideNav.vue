<template>
  <aside class="side-nav">
    <div class="side-nav__brand">
      <div class="side-nav__mark">TF</div>
      <div>
        <p class="side-nav__title">{{ appStore.platformName }}</p>
        <p class="side-nav__caption">{{ appStore.platformSlogan }}</p>
      </div>
    </div>

    <nav class="side-nav__menu" aria-label="平台主导航">
      <RouterLink
        v-for="item in appStore.navigation"
        :key="item.name"
        :to="{ name: item.name }"
        class="side-nav__item"
        :class="{ 'side-nav__item--active': route.name === item.name }"
      >
        <span class="side-nav__badge">{{ item.shortLabel }}</span>
        <span class="side-nav__content">
          <strong>{{ item.label }}</strong>
          <small>{{ item.description }}</small>
        </span>
      </RouterLink>
    </nav>

    <div class="side-nav__footer">
      <p class="side-nav__footer-title">当前聚焦</p>
      <p class="side-nav__footer-copy">{{ appStore.phaseLabel }}</p>
      <p class="side-nav__footer-copy">先把结构、路由、状态和 API 入口固定下来，再逐步接真实业务。</p>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router';

import { useAppStore } from '@/stores/app';

const route = useRoute();
const appStore = useAppStore();
</script>

<style scoped>
.side-nav {
  display: grid;
  gap: 1.75rem;
  padding: 1.5rem;
  min-height: 100dvh;
  background:
    radial-gradient(circle at top, rgba(92, 141, 255, 0.22), transparent 38%),
    linear-gradient(180deg, rgba(16, 30, 58, 0.96), rgba(9, 19, 40, 0.98));
  color: var(--color-ink-inverse);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
}

.side-nav__brand {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.side-nav__mark {
  display: grid;
  place-items: center;
  width: 3rem;
  height: 3rem;
  border-radius: 1rem;
  background: linear-gradient(135deg, rgba(96, 165, 250, 0.95), rgba(56, 189, 248, 0.8));
  color: #031225;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.side-nav__title {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
}

.side-nav__caption {
  margin: 0.3rem 0 0;
  color: rgba(230, 238, 255, 0.72);
  font-size: 0.875rem;
  line-height: 1.5;
}

.side-nav__menu {
  display: grid;
  gap: 0.75rem;
}

.side-nav__item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.9rem;
  padding: 0.9rem 1rem;
  border-radius: 1rem;
  color: inherit;
  text-decoration: none;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid transparent;
  transition: transform 180ms ease, border-color 180ms ease, background 180ms ease;
}

.side-nav__item:hover {
  transform: translateX(4px);
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(148, 197, 255, 0.24);
}

.side-nav__item--active {
  background: rgba(122, 162, 255, 0.16);
  border-color: rgba(148, 197, 255, 0.4);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.side-nav__badge {
  display: grid;
  place-items: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.8rem;
  background: rgba(255, 255, 255, 0.08);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.side-nav__content {
  display: grid;
  gap: 0.25rem;
}

.side-nav__content strong {
  font-size: 0.96rem;
}

.side-nav__content small {
  color: rgba(230, 238, 255, 0.7);
  line-height: 1.5;
}

.side-nav__footer {
  align-self: end;
  padding: 1rem;
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.side-nav__footer-title {
  margin: 0 0 0.45rem;
  font-size: 0.85rem;
  color: rgba(191, 219, 254, 0.86);
}

.side-nav__footer-copy {
  margin: 0;
  color: rgba(230, 238, 255, 0.76);
  line-height: 1.7;
}

.side-nav__footer-copy + .side-nav__footer-copy {
  margin-top: 0.45rem;
}

@media (max-width: 960px) {
  .side-nav {
    min-height: auto;
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }
}
</style>


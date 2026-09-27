<script setup>
import { RouterLink } from 'vue-router'

// 五个步骤对应五个路由名。步骤条本身不知道页面内容，只负责显示进度与提供跳转。
defineProps({
  current: { type: Number, default: 1 },
})

const steps = [
  { name: 'destination', label: '目的地' },
  { name: 'weather', label: '天气' },
  { name: 'attractions', label: '景点' },
  { name: 'plan', label: '行程' },
  { name: 'result', label: '路线' },
]
</script>

<template>
  <nav class="stepbar">
    <RouterLink
      v-for="(step, index) in steps"
      :key="step.name"
      :to="{ name: step.name }"
      class="stepbar__item"
      :class="{
        'is-current': current === index + 1,
        'is-done': current > index + 1,
      }"
    >
      <span class="stepbar__dot">{{ index + 1 }}</span>
      <span class="stepbar__label">{{ step.label }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.stepbar {
  display: flex;
  gap: 6px;
}

.stepbar__item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 8px 0 10px;
  border-radius: 12px;
  text-decoration: none;
  color: var(--muted);
  font-size: 11px;
  transition: background 0.2s ease, color 0.2s ease;
}

.stepbar__item.is-done {
  color: var(--muted);
}

.stepbar__item.is-current {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}

.stepbar__dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 600;
  background: var(--line);
  color: var(--muted);
}

.stepbar__item.is-done .stepbar__dot {
  background: var(--accent);
  color: #fff;
}

.stepbar__item.is-current .stepbar__dot {
  background: var(--accent);
  color: #fff;
}
</style>

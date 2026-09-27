<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import StepBar from './components/StepBar.vue'
import { fetchHealth } from './api'

const route = useRoute()

// null 表示还没检查完，true / false 是检查结果。
// 用三态而不是布尔值，是为了让界面能区分「检查中」和「真的连不上」。
const backendOk = ref(null)

onMounted(async () => {
  try {
    const data = await fetchHealth()
    backendOk.value = data.ok === true
  } catch {
    backendOk.value = false
  }
})
</script>

<template>
  <div class="app">
    <header class="app__header">
      <p class="app__brand">TravelMate</p>
      <StepBar :current="route.meta.step ?? 1" />
    </header>

    <main class="app__main">
      <RouterView />
    </main>

    <footer class="app__footer">
      后端连接状态：
      <span v-if="backendOk === null" class="app__status">检查中…</span>
      <span v-else-if="backendOk" class="app__status app__status--ok">正常</span>
      <span v-else class="app__status app__status--bad">未连接（确认后端已经启动）</span>
    </footer>
  </div>
</template>

<style scoped>
.app {
  max-width: 430px;
  margin: 0 auto;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--card);
}

.app__header {
  padding: 20px 20px 0;
}

.app__brand {
  margin: 0 0 14px;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.3px;
}

.app__main {
  flex: 1;
  padding: 20px;
}

.app__footer {
  padding: 12px 20px 18px;
  font-size: 12px;
  color: var(--muted);
  border-top: 1px solid var(--line);
}

.app__status--ok {
  color: #12a150;
}

.app__status--bad {
  color: #d9483b;
}
</style>

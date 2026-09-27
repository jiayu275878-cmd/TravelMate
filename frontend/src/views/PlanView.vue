<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { errorMessage, fetchRoute } from '../api'
import { trip } from '../stores/trip'

const router = useRouter()
const route = useRoute()

const generating = ref(false)
const error = ref('')

// 三种交通方式写在数据里，界面只是循环渲染。
// 加一种方式只需要改这个数组，不用动模板。
const MODES = [
  { value: 'driving', label: '驾车', hint: '最快，适合跨区' },
  { value: 'walking', label: '步行', hint: '适合一公里内' },
  { value: 'bicycling', label: '骑行', hint: '适合几公里内' },
]

// 从结果页的守卫跳回来时带的原因
const needRoute = computed(() => route.query.need === 'route')

function move(index, delta) {
  const target = index + delta
  if (target < 0 || target >= trip.selected.length) return

  // 就地移动数组里的元素：数组顺序本身就是路线顺序，
  // 所以"调顺序"不需要额外的字段，改数组就够了。
  const [item] = trip.selected.splice(index, 1)
  trip.selected.splice(target, 0, item)
}

async function generate() {
  generating.value = true
  error.value = ''

  try {
    const result = await fetchRoute({
      mode: trip.transport,
      // 只把后端需要的三个字段发过去，顺序就是列表顺序
      points: trip.selected.map((item) => ({
        name: item.name,
        lng: item.lng,
        lat: item.lat,
      })),
    })

    trip.route = result
    router.push({ name: 'result' })
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    generating.value = false
  }
}
</script>

<template>
  <section class="page">
    <p class="page__step">第 4 步</p>
    <h1 class="page__title">安排行程</h1>
    <p class="page__hint">
      用上下按钮调整景点的先后顺序，再选一种交通方式。顺序就是最终路线顺序，不做自动优化。
    </p>

    <p v-if="needRoute" class="notice">请先生成一次路线，再看路线与美食。</p>

    <ol class="stops">
      <li v-for="(item, index) in trip.selected" :key="item.id" class="stop">
        <span class="stop__index">{{ index + 1 }}</span>
        <span class="stop__name">{{ item.name }}</span>
        <span class="stop__actions">
          <button
            type="button"
            class="stop__move"
            :disabled="index === 0"
            aria-label="上移"
            @click="move(index, -1)"
          >
            ↑
          </button>
          <button
            type="button"
            class="stop__move"
            :disabled="index === trip.selected.length - 1"
            aria-label="下移"
            @click="move(index, 1)"
          >
            ↓
          </button>
        </span>
      </li>
    </ol>

    <h2 class="section__title">交通方式</h2>
    <div class="modes">
      <button
        v-for="item in MODES"
        :key="item.value"
        type="button"
        class="mode"
        :class="{ 'mode--on': trip.transport === item.value }"
        @click="trip.transport = item.value"
      >
        <span class="mode__label">{{ item.label }}</span>
        <span class="mode__hint">{{ item.hint }}</span>
      </button>
    </div>

    <p v-if="error" class="state state--error">{{ error }}</p>

    <div class="actions">
      <button type="button" class="actions__next" :disabled="generating" @click="generate">
        {{ generating ? '正在规划路线…' : '生成路线' }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.notice {
  margin: 0 0 14px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 13px;
}

.stops {
  margin: 0;
  padding: 0;
  list-style: none;
}

.stop {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  margin-bottom: 8px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
}

.stop__index {
  width: 22px;
  height: 22px;
  flex: 0 0 22px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  font-size: 12px;
}

.stop__name {
  flex: 1;
  font-size: 14px;
}

.stop__actions {
  display: flex;
  gap: 6px;
}

.stop__move {
  width: 30px;
  height: 30px;
  font-size: 14px;
  font-family: inherit;
  color: var(--accent);
  background: var(--accent-soft);
  border: 0;
  border-radius: 8px;
  cursor: pointer;
}

.stop__move:disabled {
  color: #b9c2cf;
  background: #f1f3f6;
  cursor: not-allowed;
}

.section__title {
  margin: 22px 0 10px;
  font-size: 14px;
  font-weight: 600;
  color: var(--muted);
}

.modes {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.mode {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 6px;
  font-family: inherit;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
  cursor: pointer;
}

.mode--on {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.mode__label {
  font-size: 15px;
  color: var(--text);
}

.mode--on .mode__label {
  color: var(--accent);
  font-weight: 600;
}

.mode__hint {
  font-size: 11px;
  color: var(--muted);
}

.state {
  margin: 14px 2px;
  font-size: 13px;
}

.state--error {
  color: #d9483b;
}

.actions {
  position: sticky;
  bottom: 0;
  margin: 24px -20px -20px;
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.96);
  border-top: 1px solid var(--line);
  backdrop-filter: blur(6px);
}

.actions__next {
  width: 100%;
  padding: 12px;
  font-size: 15px;
  font-family: inherit;
  color: #fff;
  background: var(--accent);
  border: 0;
  border-radius: 12px;
  cursor: pointer;
}

.actions__next:disabled {
  background: #c9d3e0;
  cursor: not-allowed;
}
</style>

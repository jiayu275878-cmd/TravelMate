<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { errorMessage, fetchAttractions } from '../api'
import { MAX_SELECTED, trip } from '../stores/trip'

const router = useRouter()
const route = useRoute()

const keywords = ref('')
const list = ref([])
const loading = ref(false)
const error = ref('')
const limitHint = ref('')

let timer = null

// 用 id 判断某条是否已被选中，而不是把整条数据比一遍
const selectedIds = computed(() => new Set(trip.selected.map((item) => item.id)))
const canContinue = computed(() => trip.selected.length >= 2)

// 从行程设置页的守卫跳回来时带的原因
const needTwo = computed(() => route.query.need === 'two')

function distanceText(meters) {
  if (meters == null) return ''
  return meters < 1000 ? `约 ${meters} 米` : `约 ${(meters / 1000).toFixed(1)} 公里`
}

async function load(text) {
  loading.value = true
  error.value = ''

  try {
    const data = await fetchAttractions({
      adcode: trip.destination.adcode,
      keywords: text,
      lng: trip.destination.lng,
      lat: trip.destination.lat,
    })

    // 竞态保护：回来的结果不是当前输入对应的，就丢掉
    if (data.keywords !== keywords.value.trim()) return

    list.value = data.list
  } catch (err) {
    error.value = errorMessage(err)
    list.value = []
  } finally {
    if (keywords.value.trim() === text) loading.value = false
  }
}

onMounted(() => {
  // 一进页面就先来一份"这个城市值得去的地方"，用户不用先打字
  load('')
})

watch(keywords, (value) => {
  clearTimeout(timer)
  limitHint.value = ''
  loading.value = true
  timer = setTimeout(() => load(value.trim()), 300)
})

onBeforeUnmount(() => clearTimeout(timer))

function toggle(item) {
  const index = trip.selected.findIndex((picked) => picked.id === item.id)

  // 再点一次是取消选择
  if (index >= 0) {
    trip.selected.splice(index, 1)
    limitHint.value = ''
    return
  }

  if (trip.selected.length >= MAX_SELECTED) {
    limitHint.value = `最多选 ${MAX_SELECTED} 个，想换的话先取消一个`
    return
  }

  // 只存后面几步真正要用到的字段，数组顺序就是路线顺序
  trip.selected.push({
    id: item.id,
    name: item.name,
    address: item.address,
    district: item.district,
    lng: item.lng,
    lat: item.lat,
  })
  limitHint.value = ''
}

function remove(index) {
  trip.selected.splice(index, 1)
  limitHint.value = ''
}
</script>

<template>
  <section class="page">
    <p class="page__step">第 3 步</p>
    <h1 class="page__title">选景点</h1>
    <p class="page__hint">
      在 {{ trip.destination.name }} 周边挑几个想去的地方，最多 {{ MAX_SELECTED }} 个。
      列表按离目的地的距离排列。
    </p>

    <input
      v-model="keywords"
      class="search__input"
      type="search"
      placeholder="想找什么？例如 博物馆、公园"
      autocomplete="off"
    />

    <p v-if="needTwo" class="notice">安排行程至少要选两个景点。</p>
    <p v-if="limitHint" class="notice">{{ limitHint }}</p>

    <!-- 已选区域放在列表上方，选了什么一眼能看到 -->
    <div v-if="trip.selected.length" class="picked">
      <p class="picked__label">已选 {{ trip.selected.length }} / {{ MAX_SELECTED }}</p>
      <!-- 横向标签而不是竖排列表：选满 5 个时能省下大约三分之二屏的高度 -->
      <ul class="chips">
        <li v-for="(item, index) in trip.selected" :key="item.id" class="chip">
          <span class="chip__index">{{ index + 1 }}</span>
          <span class="chip__name">{{ item.name }}</span>
          <button type="button" class="chip__remove" :aria-label="`取消 ${item.name}`" @click="remove(index)">
            ×
          </button>
        </li>
      </ul>
    </div>

    <p v-if="loading" class="state">正在查找…</p>
    <p v-else-if="error" class="state state--error">{{ error }}</p>
    <p v-else-if="!list.length" class="state">没有找到景点，换个词试试</p>

    <ul v-else class="cards">
      <li v-for="item in list" :key="item.id">
        <button
          type="button"
          class="card"
          :class="{ 'card--on': selectedIds.has(item.id) }"
          @click="toggle(item)"
        >
          <span class="card__top">
            <span class="card__name">{{ item.name }}</span>
            <span v-if="selectedIds.has(item.id)" class="card__check">已选</span>
          </span>
          <!-- 区、类型、距离合成一行：手机上一屏能多看两张卡片，选择效率更高 -->
          <span class="card__meta">
            {{ item.district }} · {{ item.typeText }}
            <template v-if="item.distanceMeters != null">
              · 距目的地{{ distanceText(item.distanceMeters) }}
            </template>
          </span>
          <span class="card__address">{{ item.address || '暂无地址信息' }}</span>
        </button>
      </li>
    </ul>

    <!--
      操作栏固定在屏幕底部（sticky），而不是跟着列表滚到最后。
      列表有 20 条时，把"下一步"放在末尾等于逼用户滚到底才能继续。
    -->
    <div class="actions">
      <p class="actions__count">
        已选 <strong>{{ trip.selected.length }}</strong> / {{ MAX_SELECTED }}
      </p>
      <button
        type="button"
        class="actions__next"
        :disabled="!canContinue"
        @click="router.push({ name: 'plan' })"
      >
        {{ canContinue ? '下一步：安排行程' : '至少选择 2 个景点' }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.search__input {
  width: 100%;
  padding: 12px 14px;
  font-size: 15px;
  font-family: inherit;
  color: var(--text);
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
  outline: none;
}

.search__input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.notice {
  margin: 12px 0 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fff5e6;
  color: #a35b00;
  font-size: 13px;
}

.picked {
  margin: 16px 0 0;
  padding: 12px 14px;
  border-radius: var(--radius);
  background: var(--card);
  border: 1px solid var(--line);
}

.picked__label {
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--muted);
}

.chips {
  display: flex;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
  overflow-x: auto;
  scrollbar-width: none;
}

.chips::-webkit-scrollbar {
  display: none;
}

.chip {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  font-size: 13px;
  background: var(--accent-soft);
  border-radius: 999px;
}

.chip__index {
  width: 16px;
  height: 16px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  font-size: 11px;
}

.chip__name {
  white-space: nowrap;
}

.chip__remove {
  padding: 0;
  width: 16px;
  height: 16px;
  line-height: 1;
  font-size: 14px;
  font-family: inherit;
  color: var(--accent);
  background: transparent;
  border: 1px solid var(--accent);
  border-radius: 999px;
  cursor: pointer;
}

.state {
  margin: 16px 2px;
  font-size: 13px;
  color: var(--muted);
}

.state--error {
  color: #d9483b;
}

.cards {
  margin: 16px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.card {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 12px 14px;
  text-align: left;
  font-family: inherit;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
  cursor: pointer;
}

.card--on {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.card__name {
  font-size: 15px;
  color: var(--text);
}

.card__check {
  flex: 0 0 auto;
  font-size: 11px;
  color: #fff;
  background: var(--accent);
  border-radius: 999px;
  padding: 2px 8px;
}

.card__meta {
  font-size: 12px;
  color: var(--muted);
}

.card__address {
  font-size: 12px;
  color: var(--muted);
  /* 地址可能很长，只留一行，超出用省略号 */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actions {
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  /* 用负外边距贴到内容区两侧，做出通栏效果 */
  margin: 20px -20px -20px;
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.96);
  border-top: 1px solid var(--line);
  backdrop-filter: blur(6px);
}

.actions__count {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
}

.actions__count strong {
  font-size: 16px;
  color: var(--text);
}

.actions__next {
  flex: 1;
  padding: 11px;
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

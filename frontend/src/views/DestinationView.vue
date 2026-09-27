<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { errorMessage, fetchDestinations } from '../api'
import { resetPlanning, trip } from '../stores/trip'

const router = useRouter()
const route = useRoute()

const keywords = ref('')
const results = ref([])
const loading = ref(false)
const error = ref('')
const searched = ref(false)

// 从路由守卫跳回来时带的原因，用来告诉用户为什么要重新选一次。
// 刷新 /weather 会丢掉内存里的目的地，守卫把你送回这里，这句话就是解释。
const needHint = computed(() => route.query.need === 'destination')

// 防抖计时器。用户打字时不应该每按一个键就请求一次接口：
// 一是浪费高德配额，二是几次结果乱序回来会让下拉列表闪。
let timer = null

watch(keywords, (value) => {
  clearTimeout(timer)
  error.value = ''

  const text = value.trim()
  if (!text) {
    results.value = []
    searched.value = false
    loading.value = false
    return
  }

  loading.value = true
  timer = setTimeout(() => runSearch(text), 300)
})

onBeforeUnmount(() => clearTimeout(timer))

async function runSearch(text) {
  try {
    const data = await fetchDestinations(text)

    // 竞态保护：请求发出后用户又改了输入，这次结果就已经过期，直接丢掉。
    // 这正是后端要返回 keywords 的原因。
    if (data.keywords !== keywords.value.trim()) return

    results.value = data.list
    searched.value = true
  } catch (err) {
    if (keywords.value.trim() !== text) return
    error.value = errorMessage(err)
    results.value = []
  } finally {
    if (keywords.value.trim() === text) loading.value = false
  }
}

function choose(item) {
  // 换了目的地，之前选的景点、路线、美食都不再适用，先清掉，
  // 否则会出现"在广州市选的目的地，却带着北京选好的景点"这种前后不一致的状态。
  resetPlanning()

  // 只把后面几步真正用得到的字段存进共享状态，而不是把整条候选原样塞进去。
  // adcode 尤其重要：天气接口只认行政区编码，不认经纬度。
  trip.destination = {
    name: item.name,
    district: item.district,
    adcode: item.adcode,
    lng: item.lng,
    lat: item.lat,
  }

  router.push({ name: 'weather' })
}

// 区分「还没搜过」和「搜过但没结果」：只有后者才需要提示换说法。
const showEmpty = computed(
  () => searched.value && !loading.value && !error.value && results.value.length === 0,
)
</script>

<template>
  <section class="page">
    <p class="page__step">第 1 步</p>
    <h1 class="page__title">目的地</h1>
    <p class="page__hint">输入城市或地点，从建议里选一个。城市编码会留给下一步查天气用。</p>

    <p v-if="needHint" class="notice">请先选择一个目的地，后面几步都需要它。</p>

    <input
      v-model="keywords"
      class="search__input"
      type="search"
      placeholder="例如：广州、广州塔"
      autocomplete="off"
      @keyup.enter="results.length && choose(results[0])"
    />

    <p v-if="loading" class="search__state">正在查找…</p>
    <p v-else-if="error" class="search__state search__state--error">{{ error }}</p>
    <p v-else-if="showEmpty" class="search__state">没有找到这个地方，换个说法试试</p>

    <ul v-if="results.length" class="search__list">
      <li v-for="item in results" :key="`${item.id}-${item.name}`">
        <button type="button" class="search__item" @click="choose(item)">
          <span class="search__name">{{ item.name }}</span>
          <span class="search__district">{{ item.district || '暂无地区信息' }}</span>
        </button>
      </li>
    </ul>

    <!-- 从后面的页面返回时，把已经选过的目的地显示出来，不用重新搜一遍 -->
    <div v-if="trip.destination" class="current">
      <p class="current__label">当前已选择</p>
      <p class="current__name">{{ trip.destination.name }}</p>
      <p class="current__meta">
        {{ trip.destination.district || '暂无地区信息' }} · 城市编码 {{ trip.destination.adcode }}
      </p>
      <button type="button" class="current__button" @click="router.push({ name: 'weather' })">
        继续下一步
      </button>
    </div>
  </section>
</template>

<style scoped>
/* 这个页面的样式写在组件里（scoped），只作用于本页面。
   全局的设计变量与通用页面样式放在 styles/main.css。 */
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

.search__state {
  margin: 12px 2px;
  font-size: 13px;
  color: var(--muted);
}

.search__state--error {
  color: #d9483b;
}

.search__list {
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
}

.search__item {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 14px;
  text-align: left;
  font-family: inherit;
  background: var(--card);
  border: 0;
  border-bottom: 1px solid var(--line);
  cursor: pointer;
}

.search__list li:last-child .search__item {
  border-bottom: 0;
}

.search__item:hover {
  background: var(--accent-soft);
}

.search__name {
  font-size: 15px;
  color: var(--text);
}

.search__district {
  font-size: 12px;
  color: var(--muted);
}

.notice {
  margin: 0 0 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 13px;
}

.current {
  margin-top: 22px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
}

.current__label {
  margin: 0 0 4px;
  font-size: 12px;
  color: var(--muted);
}

.current__name {
  margin: 0 0 2px;
  font-size: 17px;
  font-weight: 600;
}

.current__meta {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--muted);
}

.current__button {
  width: 100%;
  padding: 10px;
  font-size: 14px;
  font-family: inherit;
  color: #fff;
  background: var(--accent);
  border: 0;
  border-radius: 10px;
  cursor: pointer;
}
</style>

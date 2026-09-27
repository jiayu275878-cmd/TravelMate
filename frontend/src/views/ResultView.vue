<script setup>
import { computed, onMounted, ref } from 'vue'

import TravelMap from '../components/TravelMap.vue'
import { errorMessage, fetchFood } from '../api'
import { trip } from '../stores/trip'

const stops = computed(() => trip.selected)
const route = computed(() => trip.route)

const food = ref(null)
const foodLoading = ref(false)
const foodError = ref('')

const MODE_LABELS = { walking: '步行', driving: '驾车', bicycling: '骑行' }

function formatDistance(meters) {
  if (meters == null) return '—'
  return meters < 1000 ? `${meters} 米` : `${(meters / 1000).toFixed(1)} 公里`
}

function formatDuration(seconds) {
  if (seconds == null) return '—'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} 分钟`
  return `${Math.floor(minutes / 60)} 小时 ${minutes % 60} 分`
}

onMounted(async () => {
  if (!route.value?.path?.length) return

  foodLoading.value = true
  try {
    food.value = await fetchFood({
      stops: trip.selected.map((item) => ({
        name: item.name,
        lng: item.lng,
        lat: item.lat,
      })),
      path: route.value.path,
    })
  } catch (err) {
    foodError.value = errorMessage(err)
  } finally {
    foodLoading.value = false
  }
})
</script>

<template>
  <section class="page">
    <p class="page__step">第 5 步</p>
    <h1 class="page__title">路线与美食</h1>
    <p class="page__hint">
      蓝线是按所选交通方式真实规划出来的路线，编号和你在上一步排的顺序一致。
    </p>

    <!-- 地图组件只接收它需要的东西：一串点和一条折线。它不知道这些数据是怎么来的。 -->
    <TravelMap :stops="stops" :path="route?.path || []" />

    <template v-if="route">
      <h2 class="section__title">路线摘要</h2>
      <div class="summary">
        <div class="summary__item">
          <p class="summary__label">交通方式</p>
          <p class="summary__value">{{ MODE_LABELS[route.mode] || route.mode }}</p>
        </div>
        <div class="summary__item">
          <p class="summary__label">总距离</p>
          <p class="summary__value">{{ formatDistance(route.distance) }}</p>
        </div>
        <div class="summary__item">
          <p class="summary__label">预计耗时</p>
          <p class="summary__value">{{ formatDuration(route.duration) }}</p>
        </div>
      </div>

      <h2 class="section__title">每一段</h2>
      <ol class="legs">
        <li v-for="(leg, index) in route.legs" :key="index" class="leg">
          <span class="leg__index">{{ index + 1 }}</span>
          <span class="leg__route">{{ leg.from }} → {{ leg.to }}</span>
          <span class="leg__meta">{{ formatDistance(leg.distance) }} · {{ formatDuration(leg.duration) }}</span>
        </li>
      </ol>

      <h2 class="section__title">沿途美食</h2>

      <p v-if="foodLoading" class="state">正在沿路线找餐厅…</p>
      <p v-else-if="foodError" class="state state--error">{{ foodError }}</p>

      <template v-else-if="food">
        <!--
          如实说明搜索范围：所谓"沿途"是沿路线取若干个点各搜一圈，
          路很长时点与点之间会有没覆盖到的路段，不假装搜遍了全程。
        -->
        <p class="food__note">
          沿路线搜索了 {{ food.centerCount }} 个位置，每个
          {{ food.radiusMeters / 1000 }} 公里范围，按离路线由近到远排列。
        </p>
        <ul class="foods">
          <li v-for="item in food.list" :key="item.id" class="food">
            <p class="food__name">{{ item.name }}</p>
            <p class="food__meta">
              {{ item.type || '餐厅' }} · 距路线约
              {{ formatDistance(item.distanceMeters) }}
            </p>
            <p class="food__address">{{ item.district }} {{ item.address }}</p>
          </li>
        </ul>
      </template>
    </template>
  </section>
</template>

<style scoped>
.section__title {
  margin: 22px 0 10px;
  font-size: 14px;
  font-weight: 600;
  color: var(--muted);
}

.summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.summary__item {
  padding: 12px 10px;
  text-align: center;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
}

.summary__label {
  margin: 0 0 4px;
  font-size: 11px;
  color: var(--muted);
}

.summary__value {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.legs {
  margin: 0;
  padding: 0;
  list-style: none;
}

.leg {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  margin-bottom: 8px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
}

.leg__index {
  width: 20px;
  height: 20px;
  flex: 0 0 20px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 11px;
}

.leg__route {
  flex: 1;
  font-size: 13px;
}

.leg__meta {
  flex: 0 0 auto;
  font-size: 12px;
  color: var(--muted);
}

.state {
  margin: 12px 2px;
  font-size: 13px;
  color: var(--muted);
}

.state--error {
  color: #d9483b;
}

.food__note {
  margin: 0 0 10px;
  font-size: 12px;
  color: var(--muted);
}

.foods {
  margin: 0;
  padding: 0;
  list-style: none;
}

.food {
  padding: 10px 12px;
  margin-bottom: 8px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
}

.food__name {
  margin: 0 0 2px;
  font-size: 14px;
}

.food__meta {
  margin: 0 0 2px;
  font-size: 12px;
  color: var(--accent);
}

.food__address {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

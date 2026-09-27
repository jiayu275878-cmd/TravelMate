<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { errorMessage, fetchWeather } from '../api'
import { trip } from '../stores/trip'

const router = useRouter()

const weather = ref(null)
const loading = ref(true)
const error = ref('')

// 星期几不从接口的 week 字段取，而是用日期自己算。
// 实测高德返回的 week 是 1 到 7，但"1 代表周一还是周日"很容易记错，
// 用日期算出来的结果任何情况下都对得上，也不怕它以后换含义。
const WEEK_LABELS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

function dayLabel(dateText) {
  const target = new Date(`${dateText}T00:00:00`)
  if (Number.isNaN(target.getTime())) return ''

  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diffDays = Math.round((target - today) / 86400000)

  // 最近两天用户更习惯听"今天""明天"，再往后才关心是周几
  if (diffDays === 0) return '今天'
  if (diffDays === 1) return '明天'
  return WEEK_LABELS[target.getDay()]
}

// 日期显示成 月-日，手机上比完整年份更好读
function monthDay(dateText) {
  return dateText ? dateText.slice(5) : ''
}

onMounted(async () => {
  try {
    // 只把 adcode 传给后端，让后端去决定怎么问高德。
    // 前端负责"要哪些数据"，后端负责"怎么拿到"，这条边界后面每一步都一样。
    weather.value = await fetchWeather(trip.destination.adcode)
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="page">
    <p class="page__step">第 2 步</p>
    <h1 class="page__title">天气</h1>
    <p class="page__hint">
      这里是 {{ trip.destination.name }} 的天气。天气按行政区查询，所以用的是上一步存下来的城市编码
      {{ trip.destination.adcode }}。
    </p>

    <p v-if="loading" class="state">正在查询天气…</p>
    <p v-else-if="error" class="state state--error">{{ error }}</p>

    <template v-else-if="weather">
      <div v-if="weather.live" class="live">
        <p class="live__city">{{ weather.province }} {{ weather.city }}</p>
        <p class="live__temp">{{ weather.live.temperature }}<span class="live__unit">℃</span></p>
        <p class="live__weather">{{ weather.live.weather }}</p>
        <ul class="live__meta">
          <li>{{ weather.live.winddirection }}风 {{ weather.live.windpower }} 级</li>
          <li>湿度 {{ weather.live.humidity }}%</li>
          <li>更新于 {{ weather.live.reporttime }}</li>
        </ul>
      </div>
      <p v-else class="state">暂时拿不到实时天气，下面是未来几天的预报。</p>

      <h2 class="forecast__title">接下来几天</h2>
      <ul class="forecast">
        <li v-for="day in weather.forecast" :key="day.date" class="forecast__item">
          <p class="forecast__date">{{ monthDay(day.date) }}</p>
          <p class="forecast__week">{{ dayLabel(day.date) }}</p>
          <p class="forecast__weather">{{ day.dayweather }}</p>
          <p class="forecast__temp">{{ day.nighttemp }} ~ {{ day.daytemp }}℃</p>
        </li>
      </ul>

      <button type="button" class="next" @click="router.push({ name: 'attractions' })">
        下一步：选景点
      </button>
    </template>
  </section>
</template>

<style scoped>
.state {
  margin: 12px 2px;
  font-size: 13px;
  color: var(--muted);
}

.state--error {
  color: #d9483b;
}

.live {
  padding: 18px;
  border-radius: var(--radius);
  /* 用一条很淡的渐变给"当前天气"一点重量，避免整页都是白卡片 */
  background: linear-gradient(160deg, #eaf3ff 0%, #f7fbff 100%);
  border: 1px solid var(--line);
}

.live__city {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--muted);
}

.live__temp {
  margin: 0;
  font-size: 46px;
  line-height: 1.1;
  font-weight: 600;
}

.live__unit {
  font-size: 20px;
  font-weight: 400;
  margin-left: 2px;
}

.live__weather {
  margin: 4px 0 12px;
  font-size: 16px;
}

.live__meta {
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 12px;
  color: var(--muted);
}

.forecast__title {
  margin: 22px 0 10px;
  font-size: 14px;
  color: var(--muted);
  font-weight: 600;
}

.forecast {
  /* 高德会返回含今天在内的四天，四列在手机宽度下太挤，
     改成横向滚动：一屏能看到三张半，看到半张就知道右边还有。 */
  display: flex;
  gap: 10px;
  margin: 0;
  padding: 0 0 4px;
  list-style: none;
  overflow-x: auto;
  /* 手机上这条滚动条本来就不显示，桌面浏览器会画出来。
     藏掉它，让"第四张被切掉一半"这个视觉线索告诉用户可以横向滑。 */
  scrollbar-width: none;
}

.forecast::-webkit-scrollbar {
  display: none;
}

.forecast__item {
  flex: 0 0 104px;
  padding: 12px 10px;
  text-align: center;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
}

.forecast__date {
  margin: 0;
  font-size: 13px;
}

.forecast__week {
  margin: 2px 0 8px;
  font-size: 11px;
  color: var(--muted);
}

.forecast__weather {
  margin: 0 0 6px;
  font-size: 13px;
}

.forecast__temp {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
}

.next {
  width: 100%;
  margin-top: 24px;
  padding: 12px;
  font-size: 15px;
  font-family: inherit;
  color: #fff;
  background: var(--accent);
  border: 0;
  border-radius: 12px;
  cursor: pointer;
}
</style>

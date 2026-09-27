<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { loadAMap } from '../map/amap'

const props = defineProps({
  // [{ name, lng, lat }]，数组顺序就是编号顺序
  stops: { type: Array, default: () => [] },
  // [[lng, lat], ...]，路线折线的坐标数组，由后端把高德每一段路拼好
  path: { type: Array, default: () => [] },
})

const container = ref(null)
const loading = ref(true)
const error = ref('')

let AMapCtor = null
let map = null
let markers = []
let polyline = null

/**
 * 画编号标记。
 *
 * 编号用一段 HTML 实现，而不是地图自带的默认图标 —— 因为默认图标都长一样，
 * 看不出先后顺序。样式写在全局样式表里（styles/main.css 的 .tm-marker），
 * 因为这段 HTML 是高德插进页面的，组件的 scoped 样式管不到它。
 */
function drawStops() {
  if (!map || !AMapCtor) return

  // 重新画之前先清掉上一批，否则改顺序后会新旧重叠
  if (markers.length) {
    map.remove(markers)
    markers = []
  }

  markers = props.stops
    .filter((stop) => stop.lng != null && stop.lat != null)
    .map(
      (stop, index) =>
        new AMapCtor.Marker({
          position: [stop.lng, stop.lat],
          content: `<div class="tm-marker">${index + 1}</div>`,
          // 让圆圈的中心对准坐标点，否则标记会"挂在"坐标点的右下角
          offset: new AMapCtor.Pixel(-14, -14),
          title: stop.name,
        }),
    )

  if (!markers.length) return

  map.add(markers)

  // setFitView 接收的是"要框住哪些覆盖物"，所以把折线也算进去 ——
  // 只按标记算的话，绕出去的高速路段可能被切在屏幕外。
  const overlays = polyline ? [...markers, polyline] : markers
  map.setFitView(overlays, false, [60, 60, 60, 60])
}

/**
 * 画路线折线。
 *
 * 坐标数组来自后端（它已经把高德每一段路的折线拼成了一条），
 * 前端只负责把它交给地图的折线对象 —— 不做任何坐标解析。
 */
function drawPath() {
  if (!map || !AMapCtor) return

  if (polyline) {
    map.remove(polyline)
    polyline = null
  }

  if (!props.path.length) return

  polyline = new AMapCtor.Polyline({
    path: props.path,
    strokeColor: '#0a84ff',
    strokeWeight: 5,
    strokeOpacity: 0.85,
    // 折线要一直看得见：路线可能穿过标记，压在下面就会被挡住
    zIndex: 50,
    lineJoin: 'round',
    lineCap: 'round',
  })

  map.add(polyline)
}

onMounted(async () => {
  try {
    AMapCtor = await loadAMap()

    map = new AMapCtor.Map(container.value, {
      zoom: 12,
      // 默认中心先放在广州，真正的视野由上一步的 setFitView 决定
      center: [113.324521, 23.106428],
    })

    drawPath()
    drawStops()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})

// 顺序被调整、或者用户重新规划之后，重画标记
watch(
  () => props.stops,
  () => drawStops(),
  { deep: true },
)

watch(
  () => props.path,
  () => {
    drawPath()
    drawStops()
  },
  { deep: true },
)

onBeforeUnmount(() => {
  // 组件卸载时销毁地图。不销毁的话，来回切页面会在后台留下地图实例与事件监听，
  // 反复进出若干次之后就会出现"地图容器已被初始化"的报错。
  if (map) {
    map.destroy()
    map = null
  }
  markers = []
  polyline = null
})
</script>

<template>
  <div class="map">
    <div ref="container" class="map__canvas"></div>
    <p v-if="loading" class="map__state">地图加载中…</p>
    <p v-else-if="error" class="map__state map__state--error">{{ error }}</p>
  </div>
</template>

<style scoped>
.map {
  position: relative;
}

.map__canvas {
  height: 320px;
  border-radius: var(--radius);
  overflow: hidden;
  background: #e9eef4;
}

.map__state {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  margin: 0;
  font-size: 13px;
  color: var(--muted);
  background: rgba(233, 238, 244, 0.9);
  border-radius: var(--radius);
}

.map__state--error {
  padding: 0 24px;
  text-align: center;
  color: #d9483b;
}
</style>

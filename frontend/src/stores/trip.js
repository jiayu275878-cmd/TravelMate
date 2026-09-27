import { reactive } from 'vue'

// 景点数量上限。写在一个地方，界面提示和保存逻辑都读它，避免两处写死不一致。
export const MAX_SELECTED = 5

// 五个页面共享的行程数据。
// 它定义在组件外面，所以每个页面 import 到的都是同一个对象 —— 这就是多页面之间传递数据的方式，
// 也是不引入 Pinia 的全部理由。
export const trip = reactive({
  destination: null, // { name, adcode, lng, lat }
  weather: null, // 实时天气与三日预报
  attractions: [], // 候选景点列表
  selected: [], // 已选景点，数组顺序就是路线顺序
  transport: 'driving', // walking / driving / bicycling
  route: null, // { distance, duration, path, legs }
  foods: [], // 沿途美食
})

// 重新规划时清空数据：只保留目的地，其余从零开始。
export function resetPlanning() {
  trip.attractions = []
  trip.selected = []
  trip.transport = 'driving'
  trip.route = null
  trip.foods = []
}

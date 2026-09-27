import axios from 'axios'

// 所有请求都打向自己的后端，路径统一以 /api 开头。
// 开发阶段由 Vite 代理转发到 127.0.0.1:5000，所以这里看不到 Flask 的地址。
const http = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// 骨架阶段的健康检查，用来确认后端确实活着。
export async function fetchHealth() {
  const { data } = await http.get('/health')
  return data
}

// 目的地搜索。用 params 传参数而不是自己拼字符串，Axios 会负责把中文编码成
// 合法的查询字符串（例如「广州」变成 %E5%B9%BF%E5%B7%9E），不需要手写编码。
//
// 返回的是后端原样的 { keywords, list }。为什么带着 keywords：
// 输入框有防抖，可能连着发出几次请求，回来的顺序不保证和发出的顺序一致，
// 页面需要靠它判断"这次结果是不是当前输入对应的"。
export async function fetchDestinations(keywords) {
  const { data } = await http.get('/destination/search', { params: { keywords } })
  return data
}

// 天气查询。参数是 6 位行政区编码（adcode），不是经纬度 ——
// 高德的天气接口只认行政区，这也是目的地那一步必须存 adcode 的原因。
export async function fetchWeather(adcode) {
  const { data } = await http.get('/weather', { params: { adcode } })
  return data
}

// 景点搜索。keywords 留空表示"给我这个城市值得去的地方"，
// 后端会自动改用兴趣点类型码去要一份默认榜单。
// lng / lat 是出发地（也就是上一步选的目的地）的坐标，用来算距离并让近的排在前面。
export async function fetchAttractions({ adcode, keywords = '', page = 1, lng, lat }) {
  const params = { adcode, page }
  if (keywords) params.keywords = keywords
  if (lng != null && lat != null) {
    params.lng = lng
    params.lat = lat
  }
  const { data } = await http.get('/attractions', { params })
  return data
}

// 路线规划。用 POST 而不是 GET：要传的是一串点，每个点有名字和两个坐标，
// 塞进查询字符串又长又难读，POST 的请求体天生适合放结构化数据。
export async function fetchRoute({ mode, points }) {
  const { data } = await http.post('/route', { mode, points })
  return data
}

// 沿途美食。要把已经规划好的路线折线一起发回去 ——
// 后端是无状态的，它不记得上一次请求算出的路线。
// 把折线带回去比让后端重新规划一遍便宜：重新规划要多发好几次请求。
export async function fetchFood({ stops, path }) {
  // 单独放宽超时：这个接口会在后端并发查询多个位置（最多 10 次高德请求），
  // 耗时约 15 到 20 秒，而全局超时是 15 秒 —— 不放宽就会稳定超时。
  // 教训是：给别人留的等待时间，要按它真实需要的时间来定，而不是照抄别处的默认值。
  const { data } = await http.post('/food', { stops, path }, { timeout: 60000 })
  return data
}

// 把各种失败整理成一句可以直接显示的中文。
// 后端主动失败时返回 {"error": {"code", "message"}}；
// 网络层失败（后端没启动、超时）没有这个结构，所以这里兜一层，
// 页面就不必到处判断错误长什么样。
export function errorMessage(error) {
  // 后端有明确说明时优先用它
  if (error?.response?.data?.error?.message) return error.response.data.error.message

  // 超时和"后端没启动"是两回事，分开提示，否则会把用户引到错误的方向去排查。
  // Axios 在超时时会把 code 设成 ECONNABORTED。
  if (error?.code === 'ECONNABORTED') {
    return '这一步要查询的内容比较多，等待时间过长。稍后重试，或减少景点数量'
  }

  return '请求失败，请确认后端已经启动'
}

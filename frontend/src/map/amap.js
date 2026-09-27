/**
 * 高德 JavaScript API 2.0 的加载器。
 *
 * 为什么需要单独一个文件：地图脚本有两个硬性顺序要求 ——
 * 必须先设置安全密钥，再加载脚本；而且全站只应该加载一次。
 * 如果每个页面各写一遍，迟早会出现重复插入脚本、或者晚设密钥导致白屏。
 *
 * 这里的做法是「只加载一次」：第一次调用时把 Promise 存起来，后续调用直接复用同一个 Promise。
 * 模块在同一个页面里只会被求值一次，所以这个变量天然就是全局唯一的 —— 这一点和共享状态模块是同一个道理。
 */

const KEY = import.meta.env.VITE_AMAP_JS_KEY
const SECURITY_CODE = import.meta.env.VITE_AMAP_SECURITY_CODE

let loading = null

export function loadAMap() {
  // 脚本已经加载好了（例如第二次进入结果页），直接用现成的
  if (window.AMap) return Promise.resolve(window.AMap)

  // 正在加载中就复用同一个 Promise，避免插入两个 script 标签
  if (loading) return loading

  loading = new Promise((resolve, reject) => {
    if (!KEY || !SECURITY_CODE) {
      reject(new Error('没有读到高德 Key，请检查 frontend/.env.local 后重启前端'))
      return
    }

    // 必须在加载脚本之前设置。高德在脚本加载时就会读取它，
    // 晚一步设置的话脚本已经按「没有安全密钥」初始化完了，再补也没用。
    window._AMapSecurityConfig = { securityJsCode: SECURITY_CODE }

    const script = document.createElement('script')
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${KEY}`
    script.onload = () => {
      if (window.AMap) resolve(window.AMap)
      else reject(new Error('地图脚本加载了，但地图对象不存在：多半是 Key 与安全密钥不匹配'))
    }
    script.onerror = () => reject(new Error('地图脚本没能加载，检查网络后重试'))
    document.head.appendChild(script)
  }).catch((error) => {
    // 失败时把缓存的 Promise 清掉，这样用户修好配置后重试还有机会成功，
    // 而不是永远拿到同一个失败的 Promise。
    loading = null
    throw error
  })

  return loading
}

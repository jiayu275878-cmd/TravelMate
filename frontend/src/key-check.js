/**
 * 地图 Key 自检页面（排查工具，不是业务代码）。
 *
 * 它只做一件事：用 .env.local 里的 Key 与安全密钥加载高德 JavaScript API 2.0，然后把地图画出来。
 *
 * 为什么要单独做一个页面：地图类问题（白屏、Key 无效、安全密钥没配、平台类型不对）
 * 如果混在业务代码里排查，你很难判断到底是 Key 的问题还是自己代码的问题。
 * 先让这一个页面跑通，这些可能性就全部被排除了。
 */

const panel = document.querySelector('#panel')

const show = (text, kind = 'info') => {
  panel.className = `panel panel--${kind}`
  panel.textContent = text
}

const key = import.meta.env.VITE_AMAP_JS_KEY
const securityCode = import.meta.env.VITE_AMAP_SECURITY_CODE

// 第一步：确认变量真的被读到了。
// 前端环境变量必须以 VITE_ 开头，否则 Vite 不会注入，这里读到的就是 undefined。
if (!key || !securityCode) {
  show(
    '没读到 Key 或安全密钥。请检查 frontend/.env.local 是否已经填好 ' +
      'VITE_AMAP_JS_KEY 与 VITE_AMAP_SECURITY_CODE，填完保存后重启前端（Ctrl+C 再 npm run dev）。',
    'bad',
  )
} else {
  show(`已读到 Key（${key.slice(0, 4)}…${key.slice(-4)}），正在加载地图…`)

  // 第二步：必须先设置安全密钥，再加载 JS API。
  // 2021 年 12 月之后申请的 Key 都要配对安全密钥，否则地图不显示，浏览器里还看不到明显报错。
  window._AMapSecurityConfig = { securityJsCode: securityCode }

  // 第三步：动态插入 script 标签加载 JS API 2.0。
  // 用动态插入而不是直接写在 HTML 里，是为了保证上面那行配置一定先生效。
  const script = document.createElement('script')
  script.src = `https://webapi.amap.com/maps?v=2.0&key=${key}`

  script.onerror = () => {
    show('高德脚本没能加载。先检查网络，再确认这个 Key 没有被限制。', 'bad')
  }

  script.onload = () => {
    // 第四步：脚本加载成功不等于 Key 有效，真正能创建出地图才算通过。
    const AMap = window.AMap
    if (!AMap) {
      show('脚本加载了，但地图对象不存在。多半是 Key 无效，或安全密钥与 Key 不匹配。', 'bad')
      return
    }

    try {
      const map = new AMap.Map('container', {
        zoom: 13,
        // 广州塔。顺便验证经纬度能正常落到地图上：高德是「经度在前、纬度在后」。
        center: [113.3245, 23.1063],
      })
      new AMap.Marker({ position: [113.3245, 23.1063], map })
      show('地图加载成功，Key 与安全密钥配对正确。前端这一类 Key 可以用了。', 'ok')
    } catch (error) {
      show(`创建地图时出错：${error.message}`, 'bad')
    }
  }

  document.head.appendChild(script)
}

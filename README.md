# TravelMate 智能旅行伴侣

一个基于高德地图 API 的轻量旅行路线规划工具：

目的地 → 天气 → 景点 → 选景点 → 选交通方式 → 多景点路线 → 地图显示 → 沿途美食

手机尺寸优先，只在本机运行，不涉及服务器部署。本项目是学习项目，代码以简单、可运行为第一目标。

## 目录结构

    TravelMate/
    ├── backend/      Flask 后端：接收前端请求，代理高德 Web 服务接口
    ├── frontend/     Vue 3 前端：五个页面、路由、共享状态与地图展示
    └── README.md

## 运行前准备

- Node.js 24 与 npm
- Python 3.13
- 两个终端窗口（一个跑后端，一个跑前端）

## 一键启动

双击项目根目录的 `start.bat`：它会打开两个窗口分别启动后端与前端，等待 10 秒后自动打开浏览器。

`start.bat` 内部只写英文，这是刻意的。cmd 读取批处理文件时用的是系统的 ANSI 代码页
（简体中文 Windows 是 GBK），不是 UTF-8。文件里一旦出现中文，编码不匹配会让字节被错误解析，
轻则显示乱码，重则把后面的行当成命令去执行，报出「'xxx' 不是内部或外部命令」这类错误。
所以规则是：`.bat` 只写 ASCII 字符，需要中文就让程序自己输出，或者改用 PowerShell 脚本。

## 启动后端

在第一个终端里执行（PowerShell）：

    cd D:\Projects\TravelMate\backend
    python -m venv .venv              # 只需第一次
    .\.venv\Scripts\Activate.ps1      # 每次启动前先激活
    pip install -r requirements.txt   # 只需第一次
    python app.py

后端启动后访问 <http://127.0.0.1:5000/api/health>，看到 `{"ok": true, "hasKey": false}` 说明后端正常。
`hasKey` 会在你把自己的高德 Web 服务 Key 填进 `backend/.env` 之后变成 `true`。

如果 PowerShell 提示不允许运行脚本，先执行一次：

    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

## 启动前端

在第二个终端里执行：

    cd D:\Projects\TravelMate\frontend
    npm install                       # 只需第一次
    npm run dev

前端启动后访问 <http://127.0.0.1:5173>。页面顶部是五步进度条，底部显示后端连接状态。

前端开发服务器会把 `/api` 开头的请求转发到本机 5000 端口，所以前端代码里只写 `/api/xxx`，
既不会遇到浏览器跨域限制，也不需要在后端安装跨域中间件。

## 配置高德 Key

需要两类 Key，位置不同，不能混用：

| 文件 | 变量名 | 填哪一种 Key |
| --- | --- | --- |
| `backend/.env` | `AMAP_WEB_SERVICE_KEY` | 平台类型为「Web服务」的 Key |
| `frontend/.env.local` | `VITE_AMAP_JS_KEY` | 平台类型为「Web端(JS API)」的 Key |
| `frontend/.env.local` | `VITE_AMAP_SECURITY_CODE` | 上面那个 JS Key 的安全密钥 |

两个文件都不进版本库，仓库里只有对应的 `.env.example` 模板。

改完后端 `.env` 要手动重启后端（`.env` 的改动不会触发 Python 热重载）；
改完前端 `.env.local`，Vite 会自动重启。

## 密钥自检

后端 Key 自检：

    cd D:\Projects\TravelMate\backend
    .\.venv\Scripts\python.exe check_key.py

能打印出广州的实时天气，就说明后端这类 Key 可用。

前端 Key 自检：前端启动后打开 <http://localhost:5173/key-check.html>，
地图上出现广州塔的标记并显示「地图加载成功」，就说明 Key 与安全密钥配对正确。

`backend/check_key.py`、`frontend/key-check.html`、`frontend/src/key-check.js`
都是排查工具，验证通过后可以删除，不影响项目运行。

## 前端地图

地图由 `frontend/src/map/amap.js` 统一加载，它保证两件事：安全密钥一定在加载脚本之前设置，
而且全站只插入一次脚本（第一次调用时把 Promise 存起来，后续复用）。

`frontend/src/components/TravelMap.vue` 是地图组件，只接收一个 `stops` 数组，
以及一条 `path` 折线（坐标数组，由后端拼好）。它按数组顺序画编号标记、画出路线、
并把两者一起框进视野。三个容易踩的点：

- 标记的样式必须写在全局样式表（`styles/main.css` 的 `.tm-marker`），不能写在组件的 scoped 样式里 ——
  标记的 HTML 是地图库自己插入页面的，scoped 样式加的选择器属性它拿不到。
- 折线要设置较高的 `zIndex`，否则路线穿过标记时会被标记压住看不见。
- 组件卸载时要 `map.destroy()`。不销毁的话，来回切换页面会在后台留下地图实例，
  反复进出若干次之后就会报"地图容器已被初始化"。

地图瓦片与脚本都来自高德服务器，所以页面需要联网才能显示地图（接口本身也一样）。

## 后端接口

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/health` | GET | 自检：后端是否活着、是否读到 Key |
| `/api/destination/search` | GET | 目的地搜索：输入城市或地点名，返回可在地图上定位的候选 |
| `/api/weather` | GET | 天气查询：按行政区编码取实时天气与未来几天预报 |
| `/api/attractions` | GET | 景点搜索：在指定城市里找景点，可按关键词细化、可按距离排序 |
| `/api/route` | POST | 路线规划：按顺序把多个景点连成一条路线（步行 / 驾车 / 骑行） |
| `/api/food` | POST | 沿途美食：沿已规划路线找餐厅 |

目的地搜索的用法（后端要在运行中，浏览器直接打开就能看到 JSON）：

    http://127.0.0.1:5000/api/destination/search?keywords=广州

返回结构：

    {
      "keywords": "广州",
      "list": [
        {
          "id": "440104",
          "name": "广州市",
          "district": "广东省广州市",
          "adcode": "440104",
          "lng": 113.264499,
          "lat": 23.130061,
          "address": "",
          "source": "tips"
        }
      ]
    }

- `adcode` 是行政区编码，后面的天气查询只认它，不认经纬度。
- `source` 说明这条数据是从哪来的：`tips` 来自输入提示，`geocode` 来自地理编码，
  `tips+geocode` 表示坐标是用地理编码补出来的。
- 查不到结果时返回 200 与空的 `list` —— 这不算错误，前端提示「换个说法试试」即可。
- 参数缺失或过长返回 400，错误结构统一为 `{"error": {"code", "message"}}`。

天气接口的用法：

    http://127.0.0.1:5000/api/weather?adcode=440105

返回 `{adcode, city, province, live: {...} 或 null, forecast: [{...}]}`。

这个接口有两个容易踩的点，都是实测出来的：

- 高德把天气拆成两个扩展参数：`extensions=base` 给实时天气（`lives`），
  `extensions=all` 给未来几天预报（`forecasts`）。想要两者就要请求两次，
  不是文档印象里的"一次全给"。
- 预报返回的字段名是 `forecasts`（复数），每条里是 `casts` 数组；
  同一个接口在不同版本里出现过 `forecast` 与 `forecasts` 两种写法，
  所以代码里两种都认。

后端对天气做了十分钟内存缓存（`amap_client.WEATHER_TTL`），
同一城市十分钟内只花两次高德配额。实测第一次请求约 2.8 秒，命中缓存后约 2 毫秒。

景点搜索的用法：

    http://127.0.0.1:5000/api/attractions?adcode=440100&lng=113.264499&lat=23.130061
    http://127.0.0.1:5000/api/attractions?adcode=440100&keywords=博物馆

参数：`adcode` 必填；`keywords`、`page`、`lng`/`lat` 可选。给了坐标就按距离从近到远排序，
并在每条结果里带上 `distanceMeters`。

这一天的三个决定都来自实测对比，不是照文档抄的：

- 不带关键词时用 `types=110000|110100` 拿"必去榜"。只给 `110000` 时，高德返回的是
  冼星海纪念馆、北帝古庙、苏氏宗祠这类冷门条目；把公园广场（`110100`）一起给，
  返回的才是广州塔、长隆、白云山、沙面岛。
- `citylimit=true` 把搜索限制在目的地城市内，这才解决了「搜北京路返回北京店铺」的问题。
- 带关键词时**不带** `types`，拿到结果后再自己按类型码过滤。因为实测同时给
  `keywords` 与 `types` 时，类型会把排序压过去 —— 搜「广州塔」第一条返回的是越秀公园。

过滤规则是「保留类型码里带 11（风景名胜）或 14（科教文化服务）的条目」。
第一版只留了 11，结果搜「博物馆」只剩 2 条：南越王博物院的类型码是 140100，被误伤掉了。

路线规划的用法（POST，请求体是 JSON）：

    POST /api/route
    {"mode": "driving", "points": [{"name": "广州塔", "lng": 113.324521, "lat": 23.106428}, ...]}

返回 `{mode, distance, duration, legs: [{from, to, distance, duration}], path: [[lng, lat], ...]}`。

这里最重要的一个决定是**逐段请求**而不是一次传途经点，理由是实测出来的：

- 只有驾车接口支持 `waypoints`。步行与骑行会**静默忽略**这个参数 ——
  带与不带途经点返回的距离完全一样（步行 11030 米、骑行 22822 米），
  用户选的中间景点被跳过，而且不报任何错。这比报错更危险。
- 逐段请求让三种交通方式走同一条代码路径，还顺带多出每段的距离与耗时。
- 代价：一次规划发出「点数减一」次请求（最多 4 次）。规划是用户点一次才发生的动作，
  不是每次进页面都跑，这个代价可以接受。

另外两种接口的报文格式不同，都收在 `amap_client._get()` 里统一处理：
v3 用 `status`（字符串 `"1"`）表示成功，距离是字符串；v4 用 `errcode`（数字 `0`）表示成功，距离是数字。

沿途美食的用法（POST，需要把路线折线一起发回去）：

    POST /api/food
    {"stops": [...], "path": [[113.32, 23.10], ...]}

返回 `{centerCount, radiusMeters, list: [{id, name, type, address, distanceMeters}, ...]}`。

高德没有"这条线沿途的餐厅"这种接口，只有"某个坐标周围的餐厅"。所以「沿途」是我们自己定义的：
沿路线每隔约三公里取一个中心点（最少 3 个、最多 10 个），再加上每个景点本身，
每个中心搜两公里半径，最后按店铺 id 合并去重。返回值里的 `centerCount` 与 `radiusMeters`
就是让前端如实告诉用户搜索范围的 —— 路很长时采样点之间会有没覆盖到的路段，不假装搜遍了全程。

这里踩过一个坑值得记下来：第一版按「离路线由近到远」全局排序后只取前 24 家，
结果 24 家全部落在某个景点的 107 米以内，后面九个搜索点等于白搜。
**"全局取前 N"会和"沿途要铺开"这个目标直接冲突**，改成每个搜索点各取前 4 家再合并，
结果才散到三个区。

一个代价要清楚：一次美食搜索最多发出 10 次高德请求，是整个项目最贵的接口。

并发与超时（都是实测数字，也是踩过的坑）：

- 这一步最多要查 10 个位置，串行时每个约 1.6 秒，一共 15 秒以上；
  而前端全局超时是 15 秒，于是它**稳定超时**，页面上显示"请求失败"。
  更糟的是当时的错误提示只有一句兜底文案"请确认后端已经启动"，把排查方向指错了 ——
  后端其实是好的，只是客户端先放弃了。
- 改成 3 个线程并发后，实测 6 个中心从 9.36 秒降到 3.64 秒，10 个中心约 6.3 秒，
  结果数量与覆盖的区县都没变。
- 前端对这一个接口单独把超时放宽到 60 秒，并且把「超时」与「后端没启动」分成两种提示。
- 并发数选 3 而不是 10：高德个人 Key 有 QPS 限制，3 个并发的实际速率约 2 次/秒，留有余量。
  如果出现 `CUQPS_HAS_EXCEEDED_THE_LIMIT`，把 `amap_client.FOOD_WORKERS` 调小即可。

## 当前进度

- [x] 项目骨架：五个页面、路由、共享状态模块、后端健康检查
- [x] Day 1：两类高德 Key 的验证
- [x] Day 2：目的地搜索接口
- [x] Day 3：目的地页（输入、建议下拉、写入共享状态、跳转）
- [x] Day 4：天气页
- [x] Day 5：景点页
- [x] Day 6：行程设置页与路线规划接口
- [x] Day 7：结果页地图、编号标记与路线折线
- [ ] Day 8：沿途美食（代码已完成并验证，等你在浏览器里确认后再打勾）
- [ ] Day 9：README 与截图
- [ ] Day 10：缓冲与整理提交历史

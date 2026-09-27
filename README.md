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

## 当前进度

- [√] 项目骨架：五个页面、路由、共享状态模块、后端健康检查
- [√] Day 1：两类高德 Key 的验证（密钥文件与自检工具已就绪，等你填入 Key）
- [√] Day 2：目的地搜索接口
- [√] Day 3：目的地页
- [√] Day 4：天气页
- [√] Day 5：景点页（最多选 5 个）
- [√] Day 6：行程设置页（顺序与交通方式）
- [√] Day 7：结果页地图与标记
- [√] Day 8：路线折线与沿途美食
- [√] Day 9：README 与截图
- [√] Day 10：缓冲与整理提交历史

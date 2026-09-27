import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import './styles/main.css'

// 整个前端从这里进入：注册路由，再挂载到 index.html 里的 #app。
createApp(App).use(router).mount('#app')

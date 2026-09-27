import { createRouter, createWebHistory } from 'vue-router'

import DestinationView from '../views/DestinationView.vue'
import WeatherView from '../views/WeatherView.vue'
import AttractionsView from '../views/AttractionsView.vue'
import PlanView from '../views/PlanView.vue'
import ResultView from '../views/ResultView.vue'
import { trip } from '../stores/trip'

// 路由守卫：进入页面之前先检查前置条件。
// 返回 true 表示放行；返回一个路由位置表示改成去那里。
// 这里顺便把"为什么被送回来"放进查询参数，目的地页就能给用户一句解释，
// 而不是让人莫名其妙地回到首页。
const requireDestination = () =>
  trip.destination ? true : { name: 'destination', query: { need: 'destination' } }

// 行程设置页要至少两个景点才能排顺序，路线结果页要有路线才能看。
// 同样把原因带回去，页面才能给用户一句解释。
const requireTwoAttractions = () =>
  trip.selected.length >= 2 ? true : { name: 'attractions', query: { need: 'two' } }

const requireRoute = () => (trip.route ? true : { name: 'plan', query: { need: 'route' } })

// 五个页面各对应主线上的一个环节，顺序与策划书第 7 节一致。
// meta.step 让顶部步骤条知道当前在第几步，不用在每个页面里各写一遍。
const routes = [
  { path: '/', name: 'destination', component: DestinationView, meta: { step: 1, title: '目的地' } },
  {
    path: '/weather',
    name: 'weather',
    component: WeatherView,
    meta: { step: 2, title: '天气' },
    beforeEnter: requireDestination,
  },
  {
    path: '/attractions',
    name: 'attractions',
    component: AttractionsView,
    meta: { step: 3, title: '景点' },
    beforeEnter: requireDestination,
  },
  {
    path: '/plan',
    name: 'plan',
    component: PlanView,
    meta: { step: 4, title: '行程设置' },
    beforeEnter: requireTwoAttractions,
  },
  {
    path: '/result',
    name: 'result',
    component: ResultView,
    meta: { step: 5, title: '路线与美食' },
    beforeEnter: requireRoute,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router

import { createRouter, createWebHistory } from 'vue-router'
import RawLogsView from '@/views/RawLogsView.vue'
import DailySummaryView from '@/views/DailySummaryView.vue'
import DeviceListView from '@/views/DeviceListView.vue'
import DeviceDetailView from '@/views/DeviceDetailView.vue'

const routes = [
  {
    path: '/',
    redirect: '/raw-logs'
  },
  {
    path: '/raw-logs',
    name: 'raw-logs',
    component: RawLogsView
  },
  {
    path: '/summary',
    name: 'summary',
    component: DailySummaryView
  },
  {
    path: '/devices',
    name: 'devices',
    component: DeviceListView
  },
  {
    path: '/devices/:ip',
    name: 'device-detail',
    component: DeviceDetailView,
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

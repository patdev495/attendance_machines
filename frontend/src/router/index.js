import { createRouter, createWebHistory } from 'vue-router'
import AttendanceView from '@/views/AttendanceView.vue'
import DeviceListView from '@/views/DeviceListView.vue'
import DeviceDetailView from '@/views/DeviceDetailView.vue'

const routes = [
  {
    path: '/',
    name: 'attendance',
    component: AttendanceView
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

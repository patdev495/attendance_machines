import { createRouter, createWebHistory } from 'vue-router'

// v2.0 Feature Views
import LogsFeature from '@/features/logs/index.vue'
import SummaryFeature from '@/features/daily_summary/index.vue'
import EmployeesFeature from '@/features/employees/index.vue'
import MachinesFeature from '@/features/machines/index.vue'
import MachineListView from '@/features/machines/views/MachineListView.vue'
import MachineDetailView from '@/features/machines/views/MachineDetailView.vue'
import ShiftManagementView from '@/features/admin/ShiftManagementView.vue'
import MealKiosk from '@/features/meal_tracking/MealKiosk.vue'


const routes = [
  {
    path: '/',
    redirect: '/logs'
  },
  {
    path: '/logs',
    name: 'logs',
    component: LogsFeature
  },
  {
    path: '/summary',
    name: 'summary',
    component: SummaryFeature
  },
  {
    path: '/employees',
    name: 'employees',
    component: EmployeesFeature
  },
  {
    path: '/machines',
    component: MachinesFeature,
    children: [
      {
        path: '',
        name: 'machines-list',
        component: MachineListView
      },
      {
        path: ':ip',
        name: 'machines-detail',
        component: MachineDetailView,
        props: true
      }
    ]
  },
  {
    path: '/shifts',
    name: 'shifts',
    component: ShiftManagementView
  },
  {
    path: '/meal-kiosk',
    name: 'meal-kiosk',
    component: MealKiosk
  },

  // Legacy Routes Disabled
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

<template>
  <div class="table-wrap card">
    <table>
      <thead>
        <tr>
          <th>{{ $t('device.table.emp_id') }}</th>
          <th>{{ $t('device.table.name_device') }}</th>
          <th>{{ $t('device.table.name_db') }}</th>
          <th>{{ $t('device.table.status') }}</th>
          <th>{{ $t('device.table.department') }}</th>
          <th style="text-align:right">{{ $t('device.table.action') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="employees.length === 0">
          <td colspan="6" class="empty-state">{{ $t('device.table.no_records') }}</td>
        </tr>
        <tr v-for="u in employees" :key="u.user_id">
          <td style="font-weight:600;color:#fff;">{{ u.user_id }}</td>
          <td>{{ u.name || '-' }}</td>
          <td style="color:#fff;">
            <span v-if="u.db_name">{{ u.db_name }}</span>
            <small v-else style="color:var(--text-muted)">{{ $t('device.table.not_synced') }}</small>
          </td>
          <td>
            <span v-if="u.status === 'TV'" class="badge-status-tv">{{ $t('device.table.resigned') }}</span>
            <span v-else-if="u.status === 'Unknown'" style="color:var(--text-muted);font-size:0.83rem;">{{ $t('device.table.unknown') }}</span>
            <span v-else class="badge-status-active">{{ $t('device.table.active') }}</span>
          </td>
          <td>{{ u.department || '-' }}</td>
          <td style="text-align:right;">
            <button class="btn-delete" title="Delete from this machine" @click="$emit('delete', u.user_id)">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps({ employees: { type: Array, default: () => [] } })
defineEmits(['delete'])
</script>

<style scoped>
.table-wrap { overflow-x: auto; }
</style>

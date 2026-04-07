<template>
  <div>
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-text-primary mb-2">Queues</h1>
      <p class="text-text-secondary">Pending task counts per broker queue</p>
    </div>

    <div v-if="error" class="text-red-500 mb-4">{{ error }}</div>

    <div v-if="isLoading && queues.length === 0" class="text-text-secondary">
      Loading...
    </div>

    <div v-else-if="queues.length === 0" class="text-text-secondary">
      No active queues found
    </div>

    <table v-else class="w-full">
      <thead>
        <tr class="text-left text-text-secondary border-b border-border">
          <th class="py-2 px-4">Queue</th>
          <th class="py-2 px-4 text-right">Pending</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="queue in queues"
          :key="queue.name"
          class="border-b border-border-subtle hover:bg-background-hover"
        >
          <td class="py-2 px-4 font-mono text-text-primary">{{ queue.name }}</td>
          <td class="py-2 px-4 text-right font-mono text-text-primary">{{ queue.pending }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useApiService } from '~/services/apiClient'

interface QueueInfo {
  name: string
  pending: number
}

const apiService = useApiService()
const queues = ref<QueueInfo[]>([])
const isLoading = ref(false)
const error = ref<string | null>(null)
let pollInterval: ReturnType<typeof setInterval> | null = null

async function fetchQueues() {
  try {
    isLoading.value = true
    error.value = null
    queues.value = await apiService.getQueues()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to fetch queues'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchQueues()
  pollInterval = setInterval(fetchQueues, 5000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

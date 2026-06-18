<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { projectsApi } from '@/api/projects'

const props = defineProps<{
  projectId: string
  modelValue: string
}>()

const emit = defineEmits<{
  'update:modelValue': [id: string]
}>()

const credentials = ref<any[]>([])

onMounted(async () => {
  try {
    const { data } = await projectsApi.listCredentials(props.projectId)
    credentials.value = data ?? []
  } catch {
    credentials.value = []
  }
})
</script>

<template>
  <div>
    <label class="block text-xs font-medium text-gray-600 mb-1">
      Credential <span class="text-red-500">*</span>
    </label>
    <select
      :value="modelValue"
      @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
      class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400 bg-white"
    >
      <option value="">— select credential —</option>
      <option v-for="c in credentials" :key="c.id" :value="c.id">
        {{ c.name }} <span v-if="c.credential_type_name">({{ c.credential_type_name }})</span>
      </option>
    </select>
    <p v-if="!credentials.length" class="text-[11px] text-gray-400 mt-0.5">
      No credentials configured. Add one under Project → Credentials.
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { projectsApi } from '@/api/projects'

const props = defineProps<{
  projectId: string
  modelValue: string        // cache ID
  tagValue?: string         // artifact name (text, not a dropdown)
  tagLabel?: string
  tagPlaceholder?: string
  tagFilter?: (name: string) => boolean   // kept for API compat, unused
  required?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [id: string]
  'update:tagValue': [tag: string]
}>()

const caches = ref<any[]>([])

onMounted(async () => {
  try {
    const { data } = await projectsApi.listArtifactCaches(props.projectId)
    caches.value = Array.isArray(data) ? data : (data?.items ?? [])
  } catch {
    caches.value = []
  }
})
</script>

<template>
  <div class="space-y-2">
    <div>
      <label class="block text-xs font-medium text-gray-600 mb-1">
        Artifact Cache<span v-if="required" class="text-red-500 ml-0.5">*</span>
      </label>
      <select
        :value="modelValue"
        @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400 bg-white"
      >
        <option value="">— select cache —</option>
        <option v-for="c in caches" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
    </div>

    <div v-if="tagValue !== undefined">
      <label class="block text-xs font-medium text-gray-600 mb-1">
        {{ tagLabel ?? 'Artifact name' }}<span v-if="required" class="text-red-500 ml-0.5">*</span>
      </label>
      <input
        :value="tagValue"
        @input="emit('update:tagValue', ($event.target as HTMLInputElement).value)"
        type="text"
        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-violet-400"
        :placeholder="tagPlaceholder ?? 'e.g. report.pdf'"
      />
      <p class="text-[11px] text-gray-400 mt-0.5">
        Enter the exact name used when the artifact was uploaded in the previous task.
      </p>
    </div>
  </div>
</template>

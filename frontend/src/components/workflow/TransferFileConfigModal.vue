<script setup lang="ts">
import { reactive, computed } from 'vue'
import { X } from 'lucide-vue-next'
import CredentialPicker from './CredentialPicker.vue'

const props = defineProps<{
  projectId: string
  initial?: Record<string, any>
}>()

const emit = defineEmits<{
  confirm: [config: Record<string, any>]
  cancel: []
}>()

const cfg = reactive({
  credential_id: props.initial?.credential_id ?? '',
  protocol: (props.initial?.protocol ?? 'sftp') as 'sftp' | 'smb',
  remote_path: props.initial?.remote_path ?? '/{date}/',
  source_artifact_tag: props.initial?.source_artifact_tag ?? '',
})

const PATH_TOKENS = ['{date}', '{datetime}', '{year}', '{month}', '{day}', '{workflow_run_id}', '{workflow_name}', '{node_name}']

const previewPath = computed(() => {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  const ctx: Record<string, string> = {
    date: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`,
    datetime: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`,
    year: String(now.getFullYear()),
    month: pad(now.getMonth() + 1),
    day: pad(now.getDate()),
    workflow_run_id: '64a1b2c3d4e5f60001234567',
    workflow_name: 'my-workflow',
    node_name: 'transfer-file',
  }
  return cfg.remote_path.replace(/\{(\w+)\}/g, (_, k) => ctx[k] ?? `{${k}}`)
})

function insertToken(token: string) {
  cfg.remote_path += token
}

function confirm() {
  if (!cfg.credential_id || !cfg.remote_path) return
  emit('confirm', { ...cfg })
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h3 class="font-semibold text-gray-900">Configure Transfer File</h3>
      <button type="button" @click="emit('cancel')" class="text-gray-400 hover:text-gray-600"><X class="w-5 h-5" /></button>
    </div>

    <!-- Protocol -->
    <div>
      <label class="block text-xs font-medium text-gray-600 mb-2">Protocol</label>
      <div class="flex gap-2">
        <button
          v-for="p in (['sftp', 'smb'] as const)" :key="p"
          type="button"
          @click="cfg.protocol = p"
          class="flex-1 py-1.5 rounded-lg text-xs font-medium border transition-colors"
          :class="cfg.protocol === p
            ? 'bg-violet-600 border-violet-600 text-white'
            : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'"
        >{{ p.toUpperCase() }}</button>
      </div>
    </div>

    <!-- Credential -->
    <CredentialPicker :project-id="projectId" v-model="cfg.credential_id" />

    <!-- Remote path -->
    <div>
      <label class="block text-xs font-medium text-gray-600 mb-1">
        Remote Path <span class="text-red-500">*</span>
      </label>
      <input
        v-model="cfg.remote_path"
        type="text"
        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-violet-400"
        placeholder="e.g. /backups/{date}/"
      />
      <!-- Token chips -->
      <div class="flex flex-wrap gap-1 mt-1.5">
        <button
          v-for="token in PATH_TOKENS" :key="token"
          type="button"
          @click="insertToken(token)"
          class="text-[10px] font-mono bg-violet-50 hover:bg-violet-100 border border-violet-200 text-violet-600 px-1.5 py-0.5 rounded transition-colors"
        >{{ token }}</button>
      </div>
      <!-- Live preview -->
      <div v-if="cfg.remote_path" class="mt-1.5 bg-gray-50 border border-gray-200 rounded px-2 py-1">
        <span class="text-[10px] text-gray-400">Preview: </span>
        <span class="text-[10px] font-mono text-gray-700">{{ previewPath }}</span>
      </div>
    </div>

    <div class="flex gap-3 pt-2">
      <button type="button"
        @click="confirm"
        :disabled="!cfg.credential_id || !cfg.remote_path"
        class="flex-1 bg-violet-600 hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
      >Save</button>
      <button type="button" @click="emit('cancel')"
        class="text-sm text-gray-500 hover:text-gray-700 px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
      >Cancel</button>
    </div>
  </div>
</template>

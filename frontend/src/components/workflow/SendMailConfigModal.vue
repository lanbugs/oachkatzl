<script setup lang="ts">
import { reactive, ref } from 'vue'
import { X, Plus, Trash2 } from 'lucide-vue-next'

const props = defineProps<{
  projectId: string
  initial?: Record<string, any>
}>()

const emit = defineEmits<{
  confirm: [config: Record<string, any>]
  cancel: []
}>()

const cfg = reactive({
  to: (props.initial?.to ?? []) as string[],
  subject: props.initial?.subject ?? '',
  body: props.initial?.body ?? '',
  attachment_artifact_tag: props.initial?.attachment_artifact_tag ?? '',
})

const newEmail = ref('')

function addEmail() {
  const e = newEmail.value.trim()
  if (e && !cfg.to.includes(e)) cfg.to.push(e)
  newEmail.value = ''
}

function removeEmail(i: number) { cfg.to.splice(i, 1) }

function confirm() {
  if (!cfg.to.length || !cfg.subject) return
  emit('confirm', {
    ...cfg,
    attachment_artifact_tag: cfg.attachment_artifact_tag || undefined,
  })
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h3 class="font-semibold text-gray-900">Configure Send Mail</h3>
      <button type="button" @click="emit('cancel')" class="text-gray-400 hover:text-gray-600"><X class="w-5 h-5" /></button>
    </div>

    <p class="text-xs text-gray-500">SMTP settings are taken from global server configuration.</p>

    <!-- Recipients -->
    <div>
      <label class="block text-xs font-medium text-gray-600 mb-1">To <span class="text-red-500">*</span></label>
      <div class="flex gap-2 mb-1">
        <input
          v-model="newEmail"
          type="email"
          class="flex-1 border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
          placeholder="user@example.com"
          @keydown.enter.prevent="addEmail"
        />
        <button type="button" @click="addEmail"
          class="w-8 h-8 rounded-lg bg-violet-600 hover:bg-violet-700 text-white flex items-center justify-center transition-colors"
        ><Plus class="w-4 h-4" /></button>
      </div>
      <div class="flex flex-wrap gap-1">
        <span v-for="(e, i) in cfg.to" :key="i"
          class="flex items-center gap-1 bg-violet-50 border border-violet-200 text-violet-700 text-xs px-2 py-0.5 rounded-full"
        >
          {{ e }}
          <button type="button" @click="removeEmail(i)" class="text-violet-400 hover:text-violet-700"><X class="w-3 h-3" /></button>
        </span>
      </div>
    </div>

    <div>
      <label class="block text-xs font-medium text-gray-600 mb-1">Subject <span class="text-red-500">*</span></label>
      <input
        v-model="cfg.subject"
        type="text"
        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
        placeholder="Report for {date}"
      />
    </div>

    <div>
      <label class="block text-xs font-medium text-gray-600 mb-1">Body</label>
      <textarea
        v-model="cfg.body"
        rows="4"
        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400 resize-y"
        placeholder="Please find the report attached."
      />
    </div>

    <div class="flex gap-3 pt-2">
      <button type="button"
        @click="confirm"
        :disabled="!cfg.to.length || !cfg.subject"
        class="flex-1 bg-violet-600 hover:bg-violet-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
      >Save</button>
      <button type="button" @click="emit('cancel')"
        class="text-sm text-gray-500 hover:text-gray-700 px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
      >Cancel</button>
    </div>
  </div>
</template>

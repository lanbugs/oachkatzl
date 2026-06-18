<script setup lang="ts">
import { reactive, ref } from 'vue'
import { X, MailCheck, Plus, Trash2 } from 'lucide-vue-next'

const props = defineProps<{
  initial?: Record<string, any>
}>()

const emit = defineEmits<{
  confirm: [config: Record<string, any>]
  cancel: []
}>()

const cfg = reactive({
  slug: props.initial?.slug ?? '',
  emails: (props.initial?.emails ?? []) as string[],
})

const newEmail = ref('')

function addEmail() {
  const e = newEmail.value.trim().toLowerCase()
  if (!e || cfg.emails.includes(e)) return
  cfg.emails.push(e)
  newEmail.value = ''
}

function removeEmail(i: number) {
  cfg.emails.splice(i, 1)
}

function confirm() {
  if (!cfg.emails.length) return
  emit('confirm', { slug: cfg.slug, emails: [...cfg.emails] })
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <MailCheck class="w-5 h-5 text-indigo-600" />
        <h3 class="font-semibold text-gray-900">Configure Remote Approval</h3>
      </div>
      <button type="button" @click="emit('cancel')" class="text-gray-400 hover:text-gray-600">
        <X class="w-5 h-5" />
      </button>
    </div>

    <!-- Slug -->
    <div>
      <label class="block text-xs font-medium text-gray-600 mb-1">Artifact slug <span class="text-gray-400">(optional)</span></label>
      <input
        v-model="cfg.slug"
        type="text"
        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-400"
        placeholder="e.g. deploy-approval"
      />
      <p class="text-[11px] text-gray-400 mt-1">
        Name of the JSON artifact uploaded by the preceding task.
        The <code>title</code> and <code>text</code> fields from that artifact will be included in the email.
      </p>
    </div>

    <!-- Email list -->
    <div>
      <label class="block text-xs font-medium text-gray-600 mb-1">
        Recipients <span class="text-red-500">*</span>
      </label>
      <div class="flex gap-2 mb-2">
        <input
          v-model="newEmail"
          type="email"
          class="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          placeholder="user@example.com"
          @keydown.enter.prevent="addEmail"
        />
        <button
          type="button"
          @click="addEmail"
          :disabled="!newEmail.trim()"
          class="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white px-3 py-2 rounded-lg transition-colors"
        >
          <Plus class="w-4 h-4" />
        </button>
      </div>

      <div v-if="cfg.emails.length" class="space-y-1">
        <div
          v-for="(email, i) in cfg.emails" :key="email"
          class="flex items-center justify-between bg-indigo-50 border border-indigo-100 rounded-lg px-3 py-1.5"
        >
          <span class="text-sm font-mono text-indigo-800">{{ email }}</span>
          <button type="button" @click="removeEmail(i)" class="text-gray-400 hover:text-red-500 transition-colors">
            <Trash2 class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      <p v-else class="text-xs text-gray-400">Add at least one recipient.</p>
    </div>

    <p class="text-[11px] text-gray-400">
      Each recipient receives a personal email with unique approve / reject links that work without login.
      Once one person decides, all other links are automatically invalidated.
    </p>

    <div class="flex gap-3 pt-2">
      <button
        type="button"
        @click="confirm"
        :disabled="!cfg.emails.length"
        class="flex-1 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
      >Save</button>
      <button type="button" @click="emit('cancel')"
        class="text-sm text-gray-500 hover:text-gray-700 px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
      >Cancel</button>
    </div>
  </div>
</template>

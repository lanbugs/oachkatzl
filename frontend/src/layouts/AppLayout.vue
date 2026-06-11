<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { LayoutDashboard, FolderKanban, Users, Puzzle, LogOut, BookOpen, HelpCircle, Settings, Github, UserCircle, ShieldCheck } from 'lucide-vue-next'

declare const __APP_VERSION__: string
const appVersion = __APP_VERSION__

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const nav = computed(() => [
  { name: 'Dashboard', to: '/',        icon: LayoutDashboard },
  { name: 'Projects',  to: '/projects', icon: FolderKanban  },
  { name: 'Help',      to: '/help',     icon: HelpCircle    },
  ...(auth.isAdmin ? [
    { name: 'Users',             to: '/admin/users',             icon: Users       },
    { name: 'Custom Apps',       to: '/admin/custom-apps',       icon: Puzzle      },
    { name: 'Credential Types',  to: '/admin/credential-types',  icon: ShieldCheck },
    { name: 'Settings',          to: '/admin/settings',          icon: Settings    },
  ] : []),
])

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="flex h-screen bg-gray-50">
    <!-- Sidebar -->
    <aside class="w-56 flex flex-col bg-gray-900 text-gray-100">
      <div class="px-4 py-5 border-b border-gray-700">
        <div class="flex items-center gap-2.5">
          <img src="@/assets/logo.svg" alt="Oachkatzl" class="w-8 h-8 rounded-lg flex-shrink-0" />
          <span class="text-xl font-bold text-white tracking-tight">Oachkatzl</span>
        </div>
      </div>

      <nav class="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        <RouterLink
          v-for="item in nav"
          :key="item.name"
          :to="item.to"
          class="flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors"
          :class="route.path === item.to
            ? 'bg-brand-600 text-white'
            : 'text-gray-300 hover:bg-gray-700 hover:text-white'"
        >
          <component :is="item.icon" class="w-4 h-4 shrink-0" />
          {{ item.name }}
        </RouterLink>
      </nav>

      <div class="px-4 py-4 border-t border-gray-700 space-y-3">
        <!-- API Docs link -->
        <a href="/api/docs" target="_blank" rel="noopener"
          class="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors">
          <BookOpen class="w-4 h-4 shrink-0" />
          API Docs
        </a>

        <div class="border-t border-gray-700 pt-3">
          <RouterLink to="/profile"
            class="flex items-center gap-2 text-xs text-gray-400 hover:text-white transition-colors truncate mb-2">
            <UserCircle class="w-4 h-4 shrink-0" />
            <span class="truncate">{{ auth.user?.username }}</span>
            <span v-if="auth.user?.totp_enabled" class="text-green-400 text-[10px] shrink-0">2FA</span>
          </RouterLink>
          <button @click="logout"
            class="flex items-center gap-2 text-sm text-gray-300 hover:text-white transition-colors">
            <LogOut class="w-4 h-4" /> Sign out
          </button>
        </div>

        <!-- Version + GitHub -->
        <div class="border-t border-gray-700 pt-3 flex items-center justify-between">
          <span class="text-xs text-gray-500">v{{ appVersion }}</span>
          <a href="https://github.com/lanbugs/oachkatzl" target="_blank" rel="noopener"
            class="text-gray-500 hover:text-white transition-colors" title="GitHub">
            <Github class="w-4 h-4" />
          </a>
        </div>
      </div>
    </aside>

    <!-- Main -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <main class="flex-1 overflow-y-auto p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>

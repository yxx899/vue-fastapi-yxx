<template>
  <el-container class="app-shell">
    <el-aside width="248px" class="app-sidebar">
      <div class="sidebar-brand">
        <div class="sidebar-brand__mark sidebar-brand__mark--mascot" aria-hidden="true">
          <svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
            <circle cx="24" cy="26" r="14" fill="#e0f2fe" />
            <path d="M10 22c-2-8 4-14 9-7" fill="#7dd3fc" />
            <path d="M38 22c2-8-4-14-9-7" fill="#7dd3fc" />
            <circle cx="19" cy="25" r="2.2" fill="#0f2744" />
            <circle cx="29" cy="25" r="2.2" fill="#0f2744" />
            <path d="M20 31c2.2 2.4 5.8 2.4 8 0" fill="none" stroke="#0369a1" stroke-width="1.6" stroke-linecap="round" />
          </svg>
        </div>
        <div>
          <h1 class="sidebar-brand__title">智能知识库</h1>
          <p class="sidebar-brand__sub">企业内部文档与问答</p>
        </div>
      </div>
      <el-menu router :default-active="$route.path" class="sidebar-menu">
        <el-menu-item v-if="feat('chat')" index="/app/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI 问答</span>
        </el-menu-item>
        <el-menu-item v-if="feat('chat')" index="/app/history">
          <el-icon><Clock /></el-icon>
          <span>历史问答</span>
        </el-menu-item>
        <el-menu-item v-if="feat('knowledge_base')" index="/app/kbs">
          <el-icon><Collection /></el-icon>
          <span>知识库</span>
        </el-menu-item>
        <el-menu-item index="/app/profile">
          <el-icon><User /></el-icon>
          <span>个人设置</span>
        </el-menu-item>
        <template v-if="me?.role === 'tenant_admin'">
          <div class="sidebar-section">管理</div>
          <el-menu-item v-if="feat('statistics_dashboard')" index="/app/admin/dashboard">
            <el-icon><DataAnalysis /></el-icon>
            <span>统计看板</span>
          </el-menu-item>
          <el-menu-item v-if="feat('user_management')" index="/app/admin/users">
            <el-icon><UserFilled /></el-icon>
            <span>用户管理</span>
          </el-menu-item>
          <el-menu-item v-if="feat('department_management')" index="/app/admin/depts">
            <el-icon><OfficeBuilding /></el-icon>
            <span>部门管理</span>
          </el-menu-item>
          <el-menu-item v-if="feat('statistics_dashboard')" index="/app/admin/failed-docs">
            <el-icon><WarningFilled /></el-icon>
            <span>解析失败</span>
          </el-menu-item>
          <el-menu-item v-if="feat('audit')" index="/app/admin/audit">
            <el-icon><Document /></el-icon>
            <span>问答审计</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="app-header">
        <div class="app-header__context">
          <span class="app-header__pill">{{ me?.tenant_name || '…' }}</span>
          <span class="app-header__role">{{ me?.display_name || me?.username || '' }}</span>
        </div>
        <div class="app-header__actions">
          <el-button class="logout-btn" @click="logout">退出登录</el-button>
        </div>
      </el-header>
      <el-main class="app-main">
        <el-alert
          v-if="policyHint"
          type="warning"
          :closable="false"
          show-icon
          :title="policyHint"
          style="margin-bottom: 16px"
        />
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ChatDotRound,
  Clock,
  Collection,
  User,
  DataAnalysis,
  UserFilled,
  OfficeBuilding,
  WarningFilled,
  Document,
} from '@element-plus/icons-vue'
import http, { clearAuth } from '../api/http'
import { featureEnabled } from '../constants/tenantFeatures'
import { confirmLogout } from '../utils/confirmLogout'

const router = useRouter()
const me = ref(null)

const policy = computed(() => me.value?.tenant_policy)

function feat(key) {
  return featureEnabled(policy.value, key)
}

const policyHint = computed(() => {
  const p = policy.value
  if (!p) return ''
  if (!p.is_active) return '本企业已被平台停用，部分功能不可用。'
  if (p.expires_at && new Date(p.expires_at) < new Date()) return '本企业已过期，请联系平台续期。'
  return ''
})

onMounted(async () => {
  const { data } = await http.get('/auth/me')
  me.value = data
})

async function logout() {
  if (!(await confirmLogout())) return
  clearAuth()
  router.push('/login')
}
</script>

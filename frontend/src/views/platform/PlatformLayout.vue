<template>
  <el-container class="app-shell">
    <el-aside width="248px" class="app-sidebar app-sidebar--platform">
      <div class="sidebar-brand">
        <div class="sidebar-brand__mark sidebar-brand__mark--mascot" aria-hidden="true">
          <svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
            <circle cx="24" cy="26" r="14" fill="#ccfbf1" />
            <path d="M10 22c-2-8 4-14 9-7" fill="#5eead4" />
            <path d="M38 22c2-8-4-14-9-7" fill="#5eead4" />
            <circle cx="19" cy="25" r="2.2" fill="#134e4a" />
            <circle cx="29" cy="25" r="2.2" fill="#134e4a" />
            <path d="M20 31c2.2 2.4 5.8 2.4 8 0" fill="none" stroke="#0f766e" stroke-width="1.6" stroke-linecap="round" />
          </svg>
        </div>
        <div>
          <h1 class="sidebar-brand__title">平台控制台</h1>
          <p class="sidebar-brand__sub">租户开通与策略</p>
        </div>
      </div>
      <el-menu router :default-active="$route.path" class="sidebar-menu">
        <el-menu-item index="/platform/overview">
          <el-icon><DataBoard /></el-icon>
          <span>平台概览</span>
        </el-menu-item>
        <el-menu-item index="/platform/tenants">
          <el-icon><OfficeBuilding /></el-icon>
          <span>租户管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="app-header">
        <div class="app-header__context">
          <span class="app-header__pill">多租户知识库</span>
          <span class="app-header__role">超级管理员</span>
        </div>
        <div class="app-header__actions">
          <el-button class="logout-btn" @click="$router.push('/login')">租户入口</el-button>
          <el-button class="logout-btn" @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { DataBoard, OfficeBuilding } from '@element-plus/icons-vue'
import { clearAuth } from '../../api/http'
import { confirmLogout } from '../../utils/confirmLogout'

const router = useRouter()

async function logout() {
  if (!(await confirmLogout())) return
  clearAuth()
  router.push('/platform/login')
}
</script>

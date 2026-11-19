<template>
  <div class="auth-page auth-page--platform">
    <aside class="auth-hero">
      <span class="auth-hero__badge">Platform</span>
      <h1 class="auth-hero__title">租户、配额与功能策略</h1>
      <p class="auth-hero__desc">
        开通企业、设置用量上限与各模块开关；不介入租户内部文档与对话内容。
      </p>
    </aside>
    <main class="auth-main">
      <div class="auth-card">
        <h2 class="auth-card__title">平台超管</h2>
        <p class="auth-card__hint">
          独立账号，与租户体系分离（勿用 admin 租户账号）。默认：<code>platform</code> / <code>platform123</code>
        </p>
        <el-form @submit.prevent="onLogin" label-position="top">
          <el-form-item label="用户名">
            <el-input v-model="form.username" size="large" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" show-password size="large" />
          </el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading">进入控制台</el-button>
        </el-form>
        <div class="auth-links">
          <router-link to="/login">← 返回租户登录</router-link>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http, { clearAuth, formatApiError, setAuth } from '../api/http'

const router = useRouter()
const loading = ref(false)
const form = reactive({ username: 'platform', password: 'platform123' })

async function onLogin() {
  loading.value = true
  clearAuth()
  try {
    const { data } = await http.post('/platform/auth/login', form)
    setAuth(data.access_token, 'platform')
    ElMessage.success('登录成功')
    router.push('/platform/overview')
  } catch (e) {
    const msg = formatApiError(e, '登录失败')
    ElMessage.error(
      msg.includes('Network') || msg.includes('网络') || !e.response
        ? '无法连接后端，请确认 backend 已在 8000 端口启动'
        : msg,
    )
  } finally {
    loading.value = false
  }
}
</script>

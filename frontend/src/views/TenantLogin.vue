<template>
  <div class="auth-page auth-page--tenant">
    <aside class="auth-hero">
      <span class="auth-hero__badge">Tenant</span>
      <h1 class="auth-hero__title">把文档变成可检索、可问答的知识aaaaa</h1>
      <p class="auth-hero__desc">
        上传手册与资料，按权限共享；成员在统一入口提问，回答带来源引用。
      </p>
    </aside>
    <main class="auth-main">
      <div class="auth-card">
        <h2 class="auth-card__title">租户登录</h2>
        <p class="auth-card__hint">使用企业管理员或员工账号</p>
        <el-form @submit.prevent="onLogin" label-position="top">
          <el-form-item label="用户名">
            <el-input v-model="form.username" size="large" placeholder="admin" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" show-password size="large" />
          </el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">
            进入工作台
          </el-button>
        </el-form>
        <div class="auth-links">
          <router-link to="/platform/login">平台超管入口 →</router-link>
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
const form = reactive({ username: 'admin', password: 'admin123' })

async function onLogin() {
  loading.value = true
  clearAuth()
  try {
    const { data } = await http.post('/auth/login', form)
    setAuth(data.access_token, 'tenant')
    ElMessage.success('登录成功')
    router.push('/app/chat')
  } catch (e) {
    ElMessage.error(formatApiError(e, '登录失败'))
  } finally {
    loading.value = false
  }
}
</script>

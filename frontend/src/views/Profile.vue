<template>
  <div class="profile-page">
    <section class="profile-hero">
      <div class="profile-hero__avatar" aria-hidden="true">
        <svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" class="mascot">
          <defs>
            <linearGradient id="profileBody" x1="20" y1="20" x2="100" y2="110" gradientUnits="userSpaceOnUse">
              <stop stop-color="#7dd3fc" />
              <stop offset="1" stop-color="#0284c7" />
            </linearGradient>
            <linearGradient id="profileCheek" x1="0" y1="0" x2="1" y2="1">
              <stop stop-color="#fda4af" />
              <stop offset="1" stop-color="#fb7185" />
            </linearGradient>
          </defs>
          <ellipse cx="60" cy="108" rx="34" ry="6" fill="rgba(2,132,199,0.18)" />
          <circle cx="60" cy="62" r="38" fill="url(#profileBody)" />
          <path d="M28 48c-6-18 8-30 18-18" fill="#38bdf8" />
          <path d="M92 48c6-18-8-30-18-18" fill="#38bdf8" />
          <path d="M31 47c-3-10 4-16 10-9" fill="#e0f2fe" />
          <path d="M89 47c3-10-4-16-10-9" fill="#e0f2fe" />
          <ellipse cx="60" cy="66" rx="28" ry="24" fill="#f0f9ff" />
          <circle cx="48" cy="62" r="5.5" fill="#0f2744" />
          <circle cx="72" cy="62" r="5.5" fill="#0f2744" />
          <circle cx="49.8" cy="60.2" r="1.8" fill="#fff" />
          <circle cx="73.8" cy="60.2" r="1.8" fill="#fff" />
          <circle cx="40" cy="72" r="4.5" fill="url(#profileCheek)" opacity="0.75" />
          <circle cx="80" cy="72" r="4.5" fill="url(#profileCheek)" opacity="0.75" />
          <path d="M50 76c4 5 16 5 20 0" fill="none" stroke="#0369a1" stroke-width="2.4" stroke-linecap="round" />
        </svg>
      </div>
      <div class="profile-hero__text">
        <p class="eyebrow">个人中心</p>
        <h2>{{ me?.display_name || me?.username || '加载中…' }}</h2>
        <p class="profile-hero__sub">
          {{ roleLabel }} · {{ me?.tenant_name || '—' }}
        </p>
        <div class="profile-hero__tags">
          <span>账号 {{ me?.username || '—' }}</span>
          <span>{{ roleLabel }}</span>
        </div>
      </div>
    </section>

    <div class="profile-grid">
      <el-card class="profile-card" shadow="never">
        <template #header>
          <div class="card-head">
            <el-icon><User /></el-icon>
            <span>账号信息</span>
          </div>
        </template>
        <ul class="info-list">
          <li>
            <span class="label">用户名</span>
            <strong>{{ me?.username || '—' }}</strong>
          </li>
          <li>
            <span class="label">姓名</span>
            <strong>{{ me?.display_name || '—' }}</strong>
          </li>
          <li>
            <span class="label">角色</span>
            <strong>{{ roleLabel }}</strong>
          </li>
          <li>
            <span class="label">所属企业</span>
            <strong>{{ me?.tenant_name || '—' }}</strong>
          </li>
        </ul>
        <p class="card-note">账号信息由管理员维护，如需修改请联系本企业管理员。</p>
      </el-card>

      <el-card class="profile-card" shadow="never">
        <template #header>
          <div class="card-head">
            <el-icon><Lock /></el-icon>
            <span>修改密码</span>
          </div>
        </template>
        <p class="card-lead">定期更换密码，保护企业知识库访问安全。</p>
        <el-form :model="pwd" label-position="top" class="pwd-form" @submit.prevent="changePwd">
          <el-form-item label="原密码">
            <el-input v-model="pwd.old_password" type="password" show-password placeholder="请输入当前密码" />
          </el-form-item>
          <el-form-item label="新密码">
            <el-input v-model="pwd.new_password" type="password" show-password placeholder="至少 6 位" />
          </el-form-item>
          <el-button type="primary" :loading="saving" native-type="submit" class="pwd-submit">
            保存新密码
          </el-button>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import http, { formatApiError } from '../api/http'

const me = ref(null)
const saving = ref(false)
const pwd = reactive({ old_password: '', new_password: '' })

const roleLabel = computed(() =>
  me.value?.role === 'tenant_admin' ? '租户管理员' : me.value ? '普通员工' : '—',
)

onMounted(async () => {
  const { data } = await http.get('/auth/me')
  me.value = data
})

async function changePwd() {
  if (!pwd.old_password || !pwd.new_password) {
    ElMessage.warning('请填写原密码和新密码')
    return
  }
  if (pwd.new_password.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  saving.value = true
  try {
    await http.post('/auth/change-password', pwd)
    ElMessage.success('密码已更新')
    pwd.old_password = ''
    pwd.new_password = ''
  } catch (e) {
    ElMessage.error(formatApiError(e, '修改失败'))
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.profile-page {
  max-width: 980px;
}

.profile-hero {
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 22px 24px;
  margin-bottom: 16px;
  border-radius: var(--radius-lg);
  background:
    radial-gradient(ellipse 60% 80% at 0% 50%, rgba(125, 211, 252, 0.35), transparent 60%),
    linear-gradient(120deg, #0f2744 0%, #143356 55%, #0369a1 140%);
  color: #f8fafc;
  box-shadow: var(--shadow-md);
  overflow: hidden;
}

.profile-hero__avatar {
  flex-shrink: 0;
  width: 96px;
  height: 96px;
  animation: float-soft 3.2s ease-in-out infinite;
}

.mascot {
  width: 96px;
  height: 96px;
  filter: drop-shadow(0 10px 18px rgba(2, 132, 199, 0.35));
}

.eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(224, 242, 254, 0.72);
}

.profile-hero__text h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.03em;
}

.profile-hero__sub {
  margin: 6px 0 12px;
  font-size: 14px;
  color: rgba(226, 232, 240, 0.78);
}

.profile-hero__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.profile-hero__tags span {
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.16);
  font-size: 12px;
  font-weight: 600;
}

.profile-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 860px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }
  .profile-hero {
    flex-direction: column;
    text-align: center;
  }
  .profile-hero__tags {
    justify-content: center;
  }
}

.profile-card {
  border-radius: var(--radius-lg) !important;
  min-height: 100%;
}

.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
}

.card-lead {
  margin: 0 0 14px;
  font-size: 13px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.info-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.info-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border);
}

.info-list li:last-child {
  border-bottom: none;
}

.info-list .label {
  font-size: 13px;
  color: var(--color-text-soft);
}

.info-list strong {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  text-align: right;
}

.card-note {
  margin: 14px 0 0;
  padding: 10px 12px;
  border-radius: 12px;
  background: var(--color-accent-soft);
  color: var(--color-accent-deep);
  font-size: 12px;
  line-height: 1.5;
}

.pwd-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: var(--color-text-muted);
}

.pwd-submit {
  width: 100%;
  height: 40px;
  margin-top: 4px;
  font-weight: 600;
}

@keyframes float-soft {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-5px);
  }
}
</style>

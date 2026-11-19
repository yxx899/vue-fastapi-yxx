<template>
  <div>
    <el-alert
      type="info"
      show-icon
      :closable="false"
      title="平台超管负责开通租户、配额与功能开关；租户登录后菜单与接口会随您在「租户管理」中的配置生效（无法查看各租户文档/对话正文）。"
      style="margin-bottom: 16px"
    />
    <el-row :gutter="16">
      <el-col :span="8" v-for="item in cards" :key="item.key">
        <el-card class="stat-tile" shadow="hover" @click="openDetail(item)">
          <div class="num">{{ item.value ?? 0 }}</div>
          <div class="label">{{ item.label }}</div>
          <div class="hint">点击查看详情</div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="820px" destroy-on-close>
      <el-table v-loading="loading" :data="detailRows" max-height="440">
        <el-table-column
          v-for="col in detailColumns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          :width="col.width"
          :show-overflow-tooltip="col.tooltip"
        />
        <el-table-column label="管理" width="110" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goEditTenant(row.tenant_id)">配额与功能</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button type="primary" link @click="goTenants">前往租户管理</el-button>
        <el-button @click="dialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-card header="说明" style="margin-top: 16px">
      <ul class="tips">
        <li>在左侧「租户管理」中开通企业；右侧表单或列表展开行可直接改配额与功能开关。</li>
        <li>各租户业务数据（知识库、文档、问答）请在对应企业租户管理员账号下管理。</li>
        <li>默认超管账号：<code>platform / platform123</code></li>
      </ul>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../../api/http'

const router = useRouter()
const stats = ref({})
const dialogVisible = ref(false)
const dialogTitle = ref('')
const detailRows = ref([])
const detailColumns = ref([])
const loading = ref(false)

const baseColumns = [
  { prop: 'tenant_id', label: '租户ID', width: 80 },
  { prop: 'tenant_name', label: '企业名称', tooltip: true },
  { prop: 'is_active', label: '状态', width: 80 },
  { prop: 'user_count', label: '用户数', width: 80 },
  { prop: 'kb_count', label: '知识库', width: 80 },
  { prop: 'document_count', label: '文档数', width: 80 },
  { prop: 'qa_count', label: '问答次数', width: 90 },
  { prop: 'contact_name', label: '联系人', width: 100 },
  { prop: 'expires_at', label: '过期时间', width: 170, tooltip: true },
]

const cards = computed(() => [
  { key: 'tenants_all', label: '租户总数', value: stats.value.tenant_count },
  { key: 'tenants_active', label: '启用中租户', value: stats.value.active_tenant_count },
  { key: 'users', label: '平台用户总数', value: stats.value.user_count },
  { key: 'kb', label: '知识库总数', value: stats.value.kb_count },
  { key: 'doc', label: '文档总数', value: stats.value.document_count },
  { key: 'qa', label: '问答总次数', value: stats.value.qa_count },
])

function mapRows(items) {
  return items.map((r) => ({
    ...r,
    is_active: r.is_active ? '启用' : '停用',
    expires_at: r.expires_at ? r.expires_at.slice(0, 10) : '—',
  }))
}

async function openDetail(item) {
  dialogVisible.value = true
  loading.value = true
  detailRows.value = []
  detailColumns.value = baseColumns

  const titles = {
    tenants_all: '全部租户明细',
    tenants_active: '启用中租户明细',
    users: '各租户用户数量明细',
    kb: '各租户知识库数量明细',
    doc: '各租户文档数量明细',
    qa: '各租户问答次数明细',
  }
  dialogTitle.value = titles[item.key] || '详情'

  try {
    let activeOnly = null
    if (item.key === 'tenants_active') activeOnly = true
    const { data } = await http.get('/platform/stats/by-tenant', {
      params: activeOnly === null ? {} : { active_only: activeOnly },
    })
    let rows = data.items
    if (item.key === 'users') rows = [...rows].sort((a, b) => b.user_count - a.user_count)
    if (item.key === 'kb') rows = [...rows].sort((a, b) => b.kb_count - a.kb_count)
    if (item.key === 'doc') rows = [...rows].sort((a, b) => b.document_count - a.document_count)
    if (item.key === 'qa') rows = [...rows].sort((a, b) => b.qa_count - a.qa_count)
    detailRows.value = mapRows(rows)
  } finally {
    loading.value = false
  }
}

function goTenants() {
  dialogVisible.value = false
  router.push('/platform/tenants')
}

function goEditTenant(tenantId) {
  dialogVisible.value = false
  router.push({ path: '/platform/tenants', query: { id: String(tenantId) } })
}

onMounted(async () => {
  const { data } = await http.get('/platform/stats/overview')
  stats.value = data
})
</script>

<style scoped>
.tips {
  margin: 0;
  padding-left: 20px;
  line-height: 1.8;
  color: var(--color-text-muted);
}
.tips code {
  font-size: 12px;
  padding: 2px 6px;
  background: var(--color-bg-elevated);
  border-radius: 4px;
}
</style>

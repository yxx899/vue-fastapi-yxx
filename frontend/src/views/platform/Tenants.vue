<template>
  <div class="tenant-page">
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card header="租户列表">
          <div class="toolbar">
            <el-input v-model="keyword" placeholder="搜索企业名称" clearable style="width: 220px" @keyup.enter="load" />
            <el-button @click="load">查询</el-button>
            <el-button type="primary" @click="startCreate">开通租户</el-button>
          </div>

          <el-table
            ref="tableRef"
            v-loading="loading"
            :data="items"
            style="margin-top: 12px"
            highlight-current-row
            row-key="id"
            :current-row-key="selectedId"
            @current-change="onSelectRow"
          >
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="expand-features">
                  <p class="expand-title">功能开关（改后立即生效，租户重新登录或刷新后菜单同步）</p>
                  <div class="feat-grid">
                    <div v-for="f in featureMeta" :key="f.key" class="feat-cell">
                      <span>{{ f.label }}</span>
                      <el-switch
                        :model-value="row.features?.[f.key] !== false"
                        :loading="featureSaving === `${row.id}-${f.key}`"
                        @change="(v) => toggleFeature(row, f.key, v)"
                      />
                    </div>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="id" label="ID" width="56" />
            <el-table-column prop="name" label="企业名称" min-width="110" />
            <el-table-column label="状态" width="76">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
                  {{ row.is_active ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="user_count" label="用户" width="56" />
            <el-table-column label="功能" min-width="120">
              <template #default="{ row }">
                <span class="feat-tags">{{ featureSummary(row.features) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="168" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="selectTenant(row)">编辑</el-button>
                <el-button link :type="row.is_active ? 'warning' : 'success'" @click="toggleActive(row)">
                  {{ row.is_active ? '停用' : '启用' }}
                </el-button>
                <el-button link type="danger" @click="removeTenant(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-if="total > pageSize"
            style="margin-top: 12px"
            layout="total, prev, pager, next"
            :total="total"
            :page-size="pageSize"
            v-model:current-page="page"
            @current-change="load"
          />
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card ref="panelRef" class="edit-panel" :class="{ 'is-creating': !editingId }">
          <template #header>
            <div class="panel-head">
              <span>{{ panelTitle }}</span>
              <el-tag v-if="!editingId" type="success" size="small" effect="plain">新建模式</el-tag>
            </div>
          </template>
          <el-alert
            v-if="!editingId"
            type="success"
            :closable="false"
            show-icon
            title="正在开通新租户：填写下方信息后点击「保存」"
            style="margin-bottom: 12px"
          />
          <el-form :model="form" label-width="108px" label-position="top" class="edit-form">
            <el-divider content-position="left">基本信息</el-divider>
            <el-form-item label="企业名称" required>
              <el-input ref="nameInputRef" v-model="form.name" placeholder="企业全称" />
            </el-form-item>
            <el-form-item label="联系人">
              <el-input v-model="form.contact_name" />
            </el-form-item>
            <el-form-item label="联系电话">
              <el-input v-model="form.contact_phone" />
            </el-form-item>
            <el-form-item label="启用状态" v-if="editingId">
              <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
            </el-form-item>

            <el-divider content-position="left">配额限制</el-divider>
            <el-form-item label="知识库数量上限">
              <el-input-number v-model="form.max_knowledge_bases" :min="1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="文档数量上限">
              <el-input-number v-model="form.max_documents" :min="1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="单文件大小 (MB)">
              <el-input-number v-model="form.max_file_size_mb" :min="1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="用户数量上限">
              <el-input-number v-model="form.max_users" :min="1" style="width: 100%" />
            </el-form-item>
            <el-form-item label="过期时间">
              <el-date-picker v-model="form.expires_at" type="datetime" placeholder="不填则永不过期" style="width: 100%" />
            </el-form-item>

            <el-divider content-position="left">租户功能（平台控制）</el-divider>
            <div class="feat-grid panel-grid">
              <div v-for="f in featureMeta" :key="f.key" class="feat-cell">
                <span>{{ f.label }}</span>
                <el-switch v-model="form.features[f.key]" />
              </div>
            </div>

            <template v-if="!editingId">
              <el-divider content-position="left">首任租户管理员</el-divider>
              <el-form-item label="管理员用户名">
                <el-input v-model="form.admin_username" />
              </el-form-item>
              <el-form-item label="管理员密码">
                <el-input v-model="form.admin_password" type="password" show-password placeholder="至少 6 位" />
              </el-form-item>
            </template>

            <div class="panel-actions">
              <el-button
                v-if="editingId"
                type="danger"
                plain
                :loading="deleting"
                @click="removeTenantById(editingId)"
              >
                删除租户
              </el-button>
              <el-button v-if="editingId" @click="startCreate">新建租户</el-button>
              <el-button type="primary" :loading="saving" @click="save">保存</el-button>
            </div>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http, { formatApiError } from '../../api/http'
import { TENANT_FEATURE_META } from '../../constants/tenantFeatures'

const featureMeta = TENANT_FEATURE_META
const route = useRoute()
const router = useRouter()
const tableRef = ref(null)
const nameInputRef = ref(null)
const panelRef = ref(null)
let ignoreTableSelect = false

function defaultFeatures() {
  return Object.fromEntries(featureMeta.map((f) => [f.key, true]))
}

function featureSummary(features) {
  if (!features) return '全部开启'
  const off = featureMeta.filter((f) => features[f.key] === false).map((f) => f.label)
  return off.length ? `已关 ${off.length} 项` : '全部开启'
}

const items = ref([])
const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const featureSaving = ref('')
const editingId = ref(null)
const selectedId = ref(null)
const keyword = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)

const defaultForm = () => ({
  name: '',
  contact_name: '',
  contact_phone: '',
  is_active: true,
  max_knowledge_bases: 10,
  max_documents: 1000,
  max_file_size_mb: 50,
  max_users: 100,
  features: defaultFeatures(),
  expires_at: null,
  admin_username: 'admin',
  admin_password: 'admin123',
})

const form = reactive(defaultForm())

const panelTitle = computed(() => (editingId.value ? `编辑租户 #${editingId.value}` : '开通新租户'))

function fillFormFromRow(row) {
  editingId.value = row.id
  selectedId.value = row.id
  Object.assign(form, {
    name: row.name,
    contact_name: row.contact_name || '',
    contact_phone: row.contact_phone || '',
    is_active: row.is_active,
    max_knowledge_bases: row.max_knowledge_bases,
    max_documents: row.max_documents,
    max_file_size_mb: row.max_file_size_mb,
    max_users: row.max_users ?? 100,
    features: { ...defaultFeatures(), ...(row.features || {}) },
    expires_at: row.expires_at ? new Date(row.expires_at) : null,
  })
}

function startCreate() {
  ignoreTableSelect = true
  editingId.value = null
  selectedId.value = null
  Object.assign(form, defaultForm())
  tableRef.value?.setCurrentRow?.(null)
  router.replace({ path: '/platform/tenants' })
  ElMessage.success('已切换到开通新租户，请在右侧填写并保存')
  nextTick(() => {
    ignoreTableSelect = false
    const panelEl = panelRef.value?.$el || panelRef.value
    panelEl?.scrollIntoView?.({ behavior: 'smooth', block: 'nearest' })
    const input = nameInputRef.value
    input?.focus?.()
    input?.input?.focus?.()
  })
}

function selectTenant(row) {
  if (!row) return
  fillFormFromRow(row)
  router.replace({ path: '/platform/tenants', query: { id: String(row.id) } })
}

function onSelectRow(row) {
  if (ignoreTableSelect || !row) return
  selectTenant(row)
}

async function load() {
  loading.value = true
  try {
    const { data } = await http.get('/platform/tenants', {
      params: { page: page.value, page_size: pageSize, keyword: keyword.value || undefined },
    })
    items.value = data.items
    total.value = data.total
    const qid = route.query.id
    if (qid) {
      const row = items.value.find((x) => String(x.id) === String(qid))
      if (row) fillFormFromRow(row)
    }
  } finally {
    loading.value = false
  }
}

function payloadFromForm() {
  return {
    name: form.name.trim(),
    contact_name: form.contact_name || null,
    contact_phone: form.contact_phone || null,
    is_active: form.is_active,
    max_knowledge_bases: form.max_knowledge_bases,
    max_documents: form.max_documents,
    max_file_size_mb: form.max_file_size_mb,
    max_users: form.max_users,
    features: { ...form.features },
    expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null,
  }
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写企业名称')
    return
  }
  if (!editingId.value && (!form.admin_password || form.admin_password.length < 6)) {
    ElMessage.warning('管理员密码至少 6 位')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await http.put(`/platform/tenants/${editingId.value}`, payloadFromForm())
      ElMessage.success('租户配置已保存')
    } else {
      const { data } = await http.post('/platform/tenants', {
        ...payloadFromForm(),
        admin_username: form.admin_username,
        admin_password: form.admin_password,
      })
      ElMessage.success('租户已开通')
      editingId.value = data.id
      selectedId.value = data.id
      router.replace({ path: '/platform/tenants', query: { id: String(data.id) } })
    }
    await load()
  } catch (e) {
    ElMessage.error(formatApiError(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function toggleActive(row) {
  try {
    await http.put(`/platform/tenants/${row.id}`, { is_active: !row.is_active })
    ElMessage.success(row.is_active ? '已停用' : '已启用')
    await load()
    if (editingId.value === row.id) form.is_active = !row.is_active
  } catch (e) {
    ElMessage.error(formatApiError(e, '操作失败'))
  }
}

async function removeTenant(row) {
  await removeTenantById(row.id, row.name)
}

async function removeTenantById(id, nameHint) {
  const row = items.value.find((x) => x.id === id)
  const name = nameHint || row?.name || `租户 #${id}`
  try {
    await ElMessageBox.confirm(
      `将永久删除「${name}」及其全部用户、知识库、文档与问答记录，且不可恢复。确定删除？`,
      '删除租户',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' },
    )
  } catch {
    return
  }
  deleting.value = true
  try {
    await http.delete(`/platform/tenants/${id}`)
    ElMessage.success('租户已删除')
    if (editingId.value === id) startCreate()
    await load()
  } catch (e) {
    ElMessage.error(formatApiError(e, '删除失败'))
  } finally {
    deleting.value = false
  }
}

async function toggleFeature(row, key, enabled) {
  const mark = `${row.id}-${key}`
  featureSaving.value = mark
  const next = { ...(row.features || defaultFeatures()), [key]: enabled }
  try {
    const { data } = await http.patch(`/platform/tenants/${row.id}/features`, { features: next })
    row.features = data.features
    if (editingId.value === row.id) {
      form.features[key] = enabled
    }
    ElMessage.success('功能已更新')
  } catch (e) {
    ElMessage.error(formatApiError(e, '更新失败'))
  } finally {
    featureSaving.value = ''
  }
}

watch(
  () => route.query.id,
  () => {
    const qid = route.query.id
    if (!qid) return
    const row = items.value.find((x) => String(x.id) === String(qid))
    if (row) fillFormFromRow(row)
  },
)

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; flex-wrap: wrap; }
.feat-tags { font-size: 12px; color: #606266; }
.edit-panel { position: sticky; top: 12px; }
.edit-panel.is-creating {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 0 0 1px var(--el-color-primary-light-7);
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.edit-form { max-height: calc(100vh - 160px); overflow-y: auto; padding-right: 4px; }
.feat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
}
.panel-grid { margin-bottom: 16px; }
.feat-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  padding: 8px 10px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}
.edit-panel {
  border-radius: var(--radius-lg);
}
.expand-features { padding: 8px 12px 12px; }
.expand-title { margin: 0 0 10px; font-size: 13px; color: #606266; }
.panel-actions {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #eee;
}
.panel-actions .el-button--danger.is-plain {
  margin-right: auto;
}
</style>

<template>
  <div class="page-shell">
    <PageBanner
      title="知识库"
      subtitle="管理企业文档容器。公开库全员可见，私有库需按用户/部门授权。"
      eyebrow="内容"
      :icon="Collection"
    >
      <template #actions>
        <el-button v-if="isAdmin" type="primary" round @click="openCreate">新建知识库</el-button>
      </template>
    </PageBanner>

    <el-empty
      v-if="!items.length"
      class="page-panel"
      description="暂无知识库。租户管理员可新建；员工需授权或租户内公开。"
    />

    <div v-else class="kb-grid">
      <article v-for="row in items" :key="row.id" class="kb-tile">
        <div class="kb-tile__top">
          <h3 class="kb-tile__name">{{ row.name }}</h3>
          <el-tag size="small" :type="row.is_active ? 'success' : 'info'">
            {{ row.is_active ? '启用' : '停用' }}
          </el-tag>
        </div>
        <p class="kb-tile__desc">{{ row.description || '暂无描述' }}</p>
        <div class="kb-tile__meta">
          <el-tag size="small" effect="plain">{{ row.is_public_in_tenant ? '租户内公开' : '需授权' }}</el-tag>
          <el-tag v-if="row.can_manage || isAdmin" size="small" type="warning" effect="plain">可管理</el-tag>
        </div>
        <div class="kb-tile__actions">
          <el-button link type="primary" @click="$router.push(`/app/docs/${row.id}`)">文档</el-button>
          <el-button v-if="row.can_manage || isAdmin" link @click="openPerm(row)">权限</el-button>
          <el-button v-if="isAdmin" link @click="openEdit(row)">编辑</el-button>
          <el-button v-if="isAdmin" link @click="toggleKb(row)">{{ row.is_active ? '停用' : '启用' }}</el-button>
          <el-button v-if="isAdmin" link type="danger" @click="removeKb(row)">删除</el-button>
        </div>
      </article>
    </div>

    <el-pagination
      v-if="total > pageSize"
      layout="total, prev, pager, next"
      :total="total"
      :page-size="pageSize"
      v-model:current-page="page"
      @current-change="load"
    />

    <el-dialog v-model="dialog" :title="editingId ? '编辑知识库' : '新建知识库'">
      <el-form :model="form" label-position="top">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" /></el-form-item>
        <el-form-item label="租户内公开"><el-switch v-model="form.is_public_in_tenant" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="saveKb">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="permDialog" title="权限分配（只读 / 管理）">
      <el-form :model="perm" inline>
        <el-form-item label="用户">
          <el-select v-model="perm.user_id" clearable placeholder="选择用户" style="width:160px">
            <el-option v-for="u in users" :key="u.id" :label="u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="perm.department_id" clearable placeholder="选择部门" style="width:160px">
            <el-option v-for="d in depts" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="权限">
          <el-select v-model="perm.permission" style="width:120px">
            <el-option label="只读" value="read" />
            <el-option label="管理" value="manage" />
          </el-select>
        </el-form-item>
        <el-button type="primary" @click="addPerm">添加</el-button>
      </el-form>
      <el-table :data="permList">
        <el-table-column prop="user_id" label="用户ID" />
        <el-table-column prop="department_id" label="部门ID" />
        <el-table-column prop="permission" label="权限" />
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button link type="danger" @click="delPerm(row.id)">删</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Collection } from '@element-plus/icons-vue'
import PageBanner from '../components/PageBanner.vue'
import http, { formatApiError } from '../api/http'

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const isAdmin = ref(false)
const dialog = ref(false)
const editingId = ref(null)
const form = reactive({ name: '', description: '', is_public_in_tenant: false })
const permDialog = ref(false)
const currentKb = ref(null)
const perm = reactive({ user_id: null, department_id: null, permission: 'read' })
const permList = ref([])
const users = ref([])
const depts = ref([])

async function load() {
  const me = await http.get('/auth/me')
  isAdmin.value = me.data.role === 'tenant_admin'
  const { data } = await http.get('/knowledge-bases', { params: { page: page.value, page_size: pageSize } })
  items.value = data.items
  total.value = data.total
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { name: '', description: '', is_public_in_tenant: false })
  dialog.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, { name: row.name, description: row.description, is_public_in_tenant: row.is_public_in_tenant })
  dialog.value = true
}

async function saveKb() {
  if (editingId.value) {
    await http.put(`/knowledge-bases/${editingId.value}`, form)
  } else {
    await http.post('/knowledge-bases', form)
  }
  dialog.value = false
  ElMessage.success('已保存')
  load()
}

async function toggleKb(row) {
  const next = !row.is_active
  try {
    await http.post(`/knowledge-bases/${row.id}/toggle`, null, { params: { active: next } })
    ElMessage.success(next ? '已启用' : '已停用（仍保留在列表中，员工不可见）')
    load()
  } catch (e) {
    ElMessage.error(formatApiError(e, '操作失败'))
  }
}

async function removeKb(row) {
  await ElMessageBox.confirm(`确定删除知识库「${row.name}」及全部文档与向量？`, '确认')
  await http.delete(`/knowledge-bases/${row.id}`)
  ElMessage.success('已删除')
  load()
}

async function openPerm(row) {
  currentKb.value = row
  try {
    const { data } = await http.get(`/knowledge-bases/${row.id}/permissions`)
    permList.value = data
    if (isAdmin.value) {
      const [u, d] = await Promise.all([
        http.get('/users', { params: { page: 1, page_size: 100 } }),
        http.get('/departments'),
      ])
      users.value = u.data.items
      depts.value = Array.isArray(d.data) ? d.data : d.data.items || []
    }
    permDialog.value = true
  } catch (e) {
    ElMessage.error(formatApiError(e, '无法打开权限设置'))
  }
}

async function addPerm() {
  if (!perm.user_id && !perm.department_id) {
    ElMessage.warning('请选择用户或部门')
    return
  }
  await http.post(`/knowledge-bases/${currentKb.value.id}/permissions`, perm)
  openPerm(currentKb.value)
}

async function delPerm(id) {
  await http.delete(`/knowledge-bases/permissions/${id}`)
  openPerm(currentKb.value)
}

onMounted(load)
</script>

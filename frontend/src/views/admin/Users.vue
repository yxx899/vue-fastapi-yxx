<template>
  <div class="page-shell">
    <PageBanner
      title="用户管理"
      subtitle="维护本企业账号、角色与部门归属，支持重置密码。"
      eyebrow="管理"
      :icon="UserFilled"
    >
      <template #actions>
        <el-button type="primary" round @click="openCreate">新增用户</el-button>
      </template>
    </PageBanner>

    <el-card class="page-panel" shadow="never">
    <el-table :data="items">
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="display_name" label="姓名" />
      <el-table-column prop="role" label="角色">
        <template #default="{ row }">{{ row.role === 'tenant_admin' ? '管理员' : '员工' }}</template>
      </el-table-column>
      <el-table-column prop="department_id" label="部门ID" width="90" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">{{ row.is_active ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button link @click="openEdit(row)">编辑</el-button>
          <el-button link @click="resetPwd(row)">重置密码</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      v-if="total > pageSize"
      layout="total, prev, pager, next"
      :total="total"
      :page-size="pageSize"
      v-model:current-page="page"
      @current-change="load"
      style="margin-top:12px"
    />

    <el-dialog v-model="dialog" :title="editingId ? '编辑用户' : '新增用户'">
      <el-form :model="form" label-width="90px">
        <el-form-item v-if="!editingId" label="用户名"><el-input v-model="form.username" /></el-form-item>
        <el-form-item v-if="!editingId" label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="姓名"><el-input v-model="form.display_name" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role"><el-option label="员工" value="employee" /><el-option label="管理员" value="tenant_admin" /></el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="form.department_id" clearable filterable placeholder="可选" style="width: 100%">
            <el-option v-for="d in deptOptions" :key="d.id" :label="d.label" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="editingId" label="启用"><el-switch v-model="form.is_active" /></el-form-item>
      </el-form>
      <template #footer><el-button type="primary" @click="save">保存</el-button></template>
    </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UserFilled } from '@element-plus/icons-vue'
import PageBanner from '../../components/PageBanner.vue'
import http, { formatApiError } from '../../api/http'

const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const dialog = ref(false)
const editingId = ref(null)
const deptOptions = ref([])

const form = reactive({
  username: '',
  password: '',
  display_name: '',
  role: 'employee',
  department_id: null,
  is_active: true,
})

function flattenDepts(nodes, prefix = '') {
  const out = []
  for (const n of nodes || []) {
    const label = prefix ? `${prefix} / ${n.name}` : n.name
    out.push({ id: n.id, label })
    out.push(...flattenDepts(n.children, label))
  }
  return out
}

async function loadDepartments() {
  try {
    const { data } = await http.get('/departments/tree')
    deptOptions.value = flattenDepts(data.items || [])
  } catch {
    deptOptions.value = []
  }
}

function buildUserBody(forCreate) {
  const department_id =
    form.department_id === '' || form.department_id === undefined || Number.isNaN(form.department_id)
      ? null
      : form.department_id
  if (forCreate) {
    return {
      username: form.username?.trim(),
      password: form.password,
      display_name: form.display_name?.trim() || null,
      role: form.role,
      department_id,
    }
  }
  return {
    display_name: form.display_name?.trim() || null,
    role: form.role,
    department_id,
    is_active: form.is_active,
  }
}

async function load() {
  const { data } = await http.get('/users', { params: { page: page.value, page_size: pageSize } })
  items.value = data.items
  total.value = data.total
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    username: '',
    password: '',
    display_name: '',
    role: 'employee',
    department_id: null,
    is_active: true,
  })
  loadDepartments()
  dialog.value = true
}

function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, {
    display_name: row.display_name,
    role: row.role,
    department_id: row.department_id,
    is_active: row.is_active,
  })
  loadDepartments()
  dialog.value = true
}

async function save() {
  if (!editingId.value) {
    if (!form.username?.trim()) {
      ElMessage.warning('请填写用户名')
      return
    }
    if (!form.password || form.password.length < 6) {
      ElMessage.warning('密码至少 6 位')
      return
    }
  }
  try {
    if (editingId.value) {
      await http.put(`/users/${editingId.value}`, buildUserBody(false))
    } else {
      await http.post('/users', buildUserBody(true))
    }
    dialog.value = false
    ElMessage.success('已保存')
    load()
  } catch (e) {
    ElMessage.error(formatApiError(e, '保存失败'))
  }
}

async function resetPwd(row) {
  try {
    const { value } = await ElMessageBox.prompt('新密码（至少6位）', `重置 ${row.username}`)
    if (!value || value.length < 6) {
      if (value) ElMessage.warning('密码至少 6 位')
      return
    }
    await http.post(`/users/${row.id}/reset-password`, { password: value })
    ElMessage.success('密码已重置')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(formatApiError(e, '重置失败'))
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`删除用户 ${row.username}？`)
    await http.delete(`/users/${row.id}`)
    ElMessage.success('已删除')
    load()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(formatApiError(e, '删除失败'))
  }
}

onMounted(load)
</script>

<template>
  <div class="page-shell">
    <PageBanner
      title="部门管理"
      subtitle="树形组织：顶级 / 中级 / 低级。用于用户归属与知识库按部门授权。"
      eyebrow="管理"
      :icon="OfficeBuilding"
    >
      <template #actions>
        <el-button type="primary" round @click="openCreate(null)">新增顶级部门</el-button>
      </template>
    </PageBanner>

    <el-card class="page-panel" shadow="never">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="层级说明"
      description="顶级 = 公司根部门，没有上级；中级 = 挂在某个顶级部门下；低级 = 挂在某个中级部门下。列表里「上级部门」一列：顶级显示「无」，有上级的显示上级名称。"
      style="margin-bottom: 12px"
    />
    <el-table :data="flatList" row-key="id" default-expand-all style="margin-top:12px">
      <el-table-column prop="name" label="部门名称" />
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column label="层级" width="90">
        <template #default="{ row }">{{ levelLabel(row) }}</template>
      </el-table-column>
      <el-table-column label="上级部门" min-width="180">
        <template #default="{ row }">{{ parentDisplay(row) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link @click="openCreate(row.id)">子部门</el-button>
          <el-button link @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="remove(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialog" :title="editingId ? '编辑部门' : '新增部门'" width="520px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="部门名称" />
        </el-form-item>
        <el-form-item label="部门层级" required>
          <el-select v-model="form.level" placeholder="请选择层级" style="width: 100%" @change="onLevelChange">
            <el-option label="顶级（无上级）" value="top" />
            <el-option label="中级（挂在顶级下）" value="mid" :disabled="!canSelectMid">
              <span>中级（挂在顶级下）</span>
              <span v-if="!canSelectMid" class="opt-muted"> — 需先有其他顶级部门</span>
            </el-option>
            <el-option label="低级（挂在中级下）" value="low" :disabled="!canSelectLow">
              <span>低级（挂在中级下）</span>
              <span v-if="!canSelectLow" class="opt-muted"> — 需先有中级部门</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.level === 'mid'" label="上级部门" required>
          <el-select
            v-if="topDeptOptions.length"
            v-model="form.parent_id"
            filterable
            placeholder="请选择作为上级的顶级部门"
            style="width: 100%"
          >
            <el-option v-for="d in topDeptOptions" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
          <el-alert v-else type="warning" :closable="false" show-icon title="无法设为中级">
            当前没有可选的顶级上级（不能选自己）。请保持「顶级」，或先「新增顶级部门」再建中级。
          </el-alert>
        </el-form-item>
        <el-form-item v-if="form.level === 'low'" label="上级部门" required>
          <el-select
            v-if="midDeptOptions.length"
            v-model="form.parent_id"
            filterable
            placeholder="请选择作为上级的中级部门"
            style="width: 100%"
          >
            <el-option v-for="d in midDeptOptions" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
          <el-alert v-else type="warning" :closable="false" show-icon title="无法设为低级">
            还没有中级部门。请在某顶级部门行点「子部门」建中级，或把本部门设为中级后再建下级。
          </el-alert>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { OfficeBuilding } from '@element-plus/icons-vue'
import PageBanner from '../../components/PageBanner.vue'
import http, { formatApiError } from '../../api/http'

const tree = ref([])
const dialog = ref(false)
const editingId = ref(null)
const form = reactive({ name: '', level: 'top', parent_id: null })

function flatten(nodes, out = []) {
  for (const n of nodes) {
    out.push({ id: n.id, name: n.name, parent_id: n.parent_id })
    if (n.children?.length) flatten(n.children, out)
  }
  return out
}

const flatList = computed(() => flatten(tree.value))

const nameById = computed(() => {
  const m = new Map()
  for (const d of flatList.value) m.set(d.id, d.name)
  return m
})

function deptById(id) {
  return flatList.value.find((d) => d.id === id)
}

function inferLevel(row) {
  if (row.parent_id == null) return 'top'
  const parent = deptById(row.parent_id)
  if (!parent || parent.parent_id == null) return 'mid'
  return 'low'
}

function levelLabel(row) {
  const map = { top: '顶级', mid: '中级', low: '低级' }
  return map[inferLevel(row)] || '—'
}

/** 列表：上级部门列 */
function parentDisplay(row) {
  if (row.parent_id == null) {
    return '无（顶级根部门）'
  }
  const name = nameById.value.get(row.parent_id)
  return name ? `隶属于：${name}` : `上级 ID ${row.parent_id}`
}

function descendantIds(rootId) {
  const ids = new Set()
  const walk = (pid) => {
    for (const d of flatList.value) {
      if (d.parent_id === pid) {
        ids.add(d.id)
        walk(d.id)
      }
    }
  }
  walk(rootId)
  return ids
}

const excludedParentIds = computed(() => {
  const excluded = new Set()
  if (editingId.value != null) {
    excluded.add(editingId.value)
    for (const id of descendantIds(editingId.value)) excluded.add(id)
  }
  return excluded
})

/** 可选的上级：顶级部门（给「中级」选） */
const topDeptOptions = computed(() =>
  flatList.value.filter((d) => d.parent_id == null && !excludedParentIds.value.has(d.id)),
)

/** 可选的上级：中级部门（给「低级」选） */
const midDeptOptions = computed(() =>
  flatList.value.filter((d) => {
    if (excludedParentIds.value.has(d.id)) return false
    const parent = deptById(d.parent_id)
    return parent && parent.parent_id == null
  }),
)

const canSelectMid = computed(() => topDeptOptions.value.length > 0)
const canSelectLow = computed(() => midDeptOptions.value.length > 0)

function onLevelChange() {
  if (form.level === 'top') {
    form.parent_id = null
    return
  }
  if (form.level === 'mid') {
    if (!canSelectMid.value) {
      form.level = 'top'
      form.parent_id = null
      ElMessage.warning('当前无法设为中级，已改回顶级')
      return
    }
    if (!topDeptOptions.value.some((d) => d.id === form.parent_id)) {
      form.parent_id = topDeptOptions.value[0]?.id ?? null
    }
    return
  }
  if (form.level === 'low') {
    if (!canSelectLow.value) {
      form.level = 'top'
      form.parent_id = null
      ElMessage.warning('当前无法设为低级，已改回顶级')
      return
    }
    if (!midDeptOptions.value.some((d) => d.id === form.parent_id)) {
      form.parent_id = midDeptOptions.value[0]?.id ?? null
    }
  }
}

async function load() {
  const { data } = await http.get('/departments/tree')
  tree.value = data.items
}

function applyRowToForm(row, presetParentId = null) {
  if (presetParentId != null) {
    form.level = 'mid'
    form.parent_id = presetParentId
    const parent = deptById(presetParentId)
    if (parent && parent.parent_id != null) {
      form.level = 'low'
    }
    return
  }
  if (!row) {
    form.level = 'top'
    form.parent_id = null
    return
  }
  form.level = inferLevel(row)
  form.parent_id = row.parent_id ?? null
  if (form.level === 'mid' && !canSelectMid.value) form.level = 'top'
  if (form.level === 'low' && !canSelectLow.value) form.level = 'top'
  if (form.level === 'top') form.parent_id = null
}

async function openCreate(parentId) {
  await load()
  editingId.value = null
  form.name = ''
  applyRowToForm(null, parentId ?? undefined)
  if (parentId == null) {
    form.level = 'top'
    form.parent_id = null
  }
  dialog.value = true
}

async function openEdit(row) {
  await load()
  editingId.value = row.id
  form.name = row.name
  applyRowToForm(row)
  dialog.value = true
}

async function save() {
  const name = form.name?.trim()
  if (!name) {
    ElMessage.warning('请填写部门名称')
    return
  }
  if (form.level === 'mid' && (!canSelectMid.value || !form.parent_id)) {
    ElMessage.warning('中级必须选择上级顶级部门')
    return
  }
  if (form.level === 'low' && (!canSelectLow.value || !form.parent_id)) {
    ElMessage.warning('低级必须选择上级中级部门')
    return
  }
  const parent_id =
    form.level === 'top' ? null : form.parent_id === '' || form.parent_id === undefined ? null : form.parent_id
  if (form.level !== 'top' && parent_id == null) {
    ElMessage.warning('请选择上级部门')
    return
  }
  const body = { name, parent_id }
  try {
    if (editingId.value) {
      await http.put(`/departments/${editingId.value}`, body)
    } else {
      await http.post('/departments', body)
    }
    dialog.value = false
    ElMessage.success('已保存')
    load()
  } catch (e) {
    ElMessage.error(formatApiError(e, '保存失败'))
  }
}

async function remove(id) {
  await ElMessageBox.confirm('确定删除该部门？')
  try {
    await http.delete(`/departments/${id}`)
    ElMessage.success('已删除')
    load()
  } catch (e) {
    ElMessage.error(formatApiError(e, '删除失败'))
  }
}

onMounted(load)
</script>

<style scoped>
.hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}
.opt-muted {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>

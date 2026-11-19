<template>
  <div class="page-shell">
    <PageBanner
      title="问答审计"
      subtitle="查看本企业问答留痕，支持筛选、详情、批量删除与 CSV 导出。"
      eyebrow="管理"
      :icon="Document"
    >
      <template #actions>
        <el-button v-if="canExport" round @click="exportCsv">导出 CSV</el-button>
        <el-button type="danger" plain round :disabled="!total" @click="removeAllFiltered">一键删除</el-button>
      </template>
    </PageBanner>

    <el-card class="page-panel" shadow="never">
    <div class="toolbar">
      <el-checkbox v-model="todayOnly" @change="load">仅今日</el-checkbox>
      <el-select v-model="feedbackFilter" placeholder="反馈筛选" clearable style="width:140px" @change="load">
        <el-option label="好评" :value="1" />
        <el-option label="差评" :value="-1" />
      </el-select>
      <el-input v-model.number="filterUserId" placeholder="用户ID" clearable style="width:100px" @change="load" />
      <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始" end-placeholder="结束" @change="load" />
    </div>

    <el-table :data="items" style="margin-top:12px">
      <el-table-column prop="user_id" label="用户" width="80" />
      <el-table-column prop="question" label="问题" min-width="140" show-overflow-tooltip />
      <el-table-column label="回答" min-width="220">
        <template #default="{ row }">
          <span class="answer-preview">{{ row.answer_preview || preview(row.answer) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="feedback" label="反馈" width="80">
        <template #default="{ row }">
          {{ feedbackText(row.feedback) }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" width="180" />
      <el-table-column label="操作" width="130" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click.stop="openDetail(row)">详情</el-button>
          <el-button link type="danger" @click.stop="removeLog(row)">删除</el-button>
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

    <el-dialog v-model="detailVisible" title="问答详情" width="760px" destroy-on-close>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户 ID">{{ current.user_id }}</el-descriptions-item>
        <el-descriptions-item label="知识库 ID">{{ current.kb_ids || '—' }}</el-descriptions-item>
        <el-descriptions-item label="提问时间">{{ current.created_at }}</el-descriptions-item>
        <el-descriptions-item label="用户问题">{{ current.question }}</el-descriptions-item>
      </el-descriptions>
      <div class="block-title">AI 回答</div>
      <div class="answer-box">{{ current.answer || '（无回答内容）' }}</div>
      <div v-if="sources.length" class="block-title">引用溯源</div>
      <ul v-if="sources.length" class="sources">
        <li v-for="(s, i) in sources" :key="i">
          <strong>《{{ s.document_name }}》</strong>：{{ s.snippet }}
        </li>
      </ul>
      <template #footer>
        <el-button type="danger" @click="removeLog(current)">删除此记录</el-button>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import PageBanner from '../../components/PageBanner.vue'
import http, { formatApiError } from '../../api/http'
import { featureEnabled } from '../../constants/tenantFeatures'

const route = useRoute()
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const todayOnly = ref(false)
const feedbackFilter = ref(null)
const filterUserId = ref(null)
const dateRange = ref(null)
const detailVisible = ref(false)
const current = ref({})
const sources = ref([])
const canExport = ref(true)

function preview(text) {
  return (text || '').replace(/\s+/g, ' ').slice(0, 80)
}

function feedbackText(v) {
  if (v === 1) return '好评'
  if (v === -1) return '差评'
  return '—'
}

function openDetail(row) {
  current.value = row
  try {
    sources.value = row.sources_json ? JSON.parse(row.sources_json) : []
  } catch {
    sources.value = []
  }
  detailVisible.value = true
}

function listParams() {
  const params = { page: page.value, page_size: pageSize }
  if (todayOnly.value) params.today_only = true
  if (feedbackFilter.value !== null && feedbackFilter.value !== '') {
    params.feedback = feedbackFilter.value
  }
  if (filterUserId.value) params.user_id = filterUserId.value
  if (dateRange.value?.length === 2) {
    params.start_date = dateRange.value[0].toISOString().slice(0, 10)
    params.end_date = dateRange.value[1].toISOString().slice(0, 10)
  }
  return params
}

function batchDeleteParams() {
  const params = {}
  if (todayOnly.value) params.today_only = true
  if (feedbackFilter.value !== null && feedbackFilter.value !== '') {
    params.feedback = feedbackFilter.value
  }
  if (filterUserId.value) params.user_id = filterUserId.value
  if (dateRange.value?.length === 2) {
    params.start_date = dateRange.value[0].toISOString().slice(0, 10)
    params.end_date = dateRange.value[1].toISOString().slice(0, 10)
  }
  return params
}

async function load() {
  const { data } = await http.get('/audit/logs', { params: listParams() })
  items.value = data.items
  total.value = data.total
}

async function deleteLogApi(id) {
  try {
    await http.delete(`/audit/logs/${id}`)
  } catch (err) {
    if (err.response?.status === 405 || err.response?.status === 404) {
      await http.post(`/audit/logs/${id}/delete`)
    } else {
      throw err
    }
  }
}

async function batchDeleteApi() {
  const config = { params: batchDeleteParams() }
  for (const url of ['/audit/logs/actions/batch-delete', '/audit/logs/delete-batch']) {
    try {
      return await http.post(url, null, config)
    } catch (err) {
      const st = err.response?.status
      if (st !== 404 && st !== 405) throw err
    }
  }
  return null
}

/** 旧版后端无批量接口时，按当前筛选逐页删第一条列表直至清空 */
async function deleteAllFilteredByPages() {
  const params = { ...batchDeleteParams(), page: 1, page_size: 100 }
  let deleted = 0
  for (;;) {
    const { data } = await http.get('/audit/logs', { params })
    const batch = data.items || []
    if (!batch.length) break
    for (const row of batch) {
      await deleteLogApi(row.id)
      deleted += 1
    }
  }
  return deleted
}

async function removeAllFiltered() {
  if (!total.value) return
  const scope =
    todayOnly.value || feedbackFilter.value != null || filterUserId.value || dateRange.value?.length
      ? '当前筛选条件下的'
      : '本租户全部'
  try {
    await ElMessageBox.confirm(
      `确定删除${scope} ${total.value} 条问答审计记录？删除后不可恢复。（不会自动删除 AI 对话页中的聊天记录。）`,
      '一键删除确认',
      { type: 'warning', confirmButtonText: '全部删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const resp = await batchDeleteApi()
    let deleted
    if (resp) {
      deleted = resp.data.deleted ?? total.value
    } else {
      ElMessage.info('正在逐条删除（请重启后端后可一键批量）…')
      deleted = await deleteAllFilteredByPages()
    }
    ElMessage.success(`已删除 ${deleted} 条`)
    detailVisible.value = false
    page.value = 1
    await load()
  } catch (err) {
    if (err.response?.status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      return
    }
    ElMessage.error(formatApiError(err, '批量删除失败'))
  }
}

async function removeLog(row) {
  if (row?.id == null) {
    ElMessage.error('记录 ID 无效，请刷新页面')
    return
  }
  try {
    await ElMessageBox.confirm(
      '确定删除该条问答审计记录？删除后不可恢复。（AI 对话页中的聊天记录不会自动删除。）',
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteLogApi(row.id)
    ElMessage.success('已删除')
    if (detailVisible.value && current.value?.id === row.id) detailVisible.value = false
    await load()
  } catch (err) {
    const detail = err.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail[0]?.msg : '删除失败'
    if (err.response?.status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      return
    }
    if (err.response?.status === 403) {
      ElMessage.error('需要租户管理员权限')
      return
    }
    ElMessage.error(msg || '删除失败，请确认已用租户管理员登录并重启后端')
    await load()
  }
}

async function exportCsv() {
  const resp = await fetch('/api/audit/logs/export', {
    headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
  })
  const blob = await resp.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'qa_logs.csv'
  a.click()
  URL.revokeObjectURL(url)
}

function applyRouteQuery() {
  todayOnly.value = route.query.today === '1'
  if (route.query.feedback !== undefined && route.query.feedback !== '') {
    feedbackFilter.value = Number(route.query.feedback)
  }
}

onMounted(async () => {
  applyRouteQuery()
  try {
    const { data } = await http.get('/auth/me')
    canExport.value = featureEnabled(data.tenant_policy, 'audit_export')
  } catch {
    canExport.value = false
  }
  load()
})

watch(() => route.query, () => {
  applyRouteQuery()
  load()
})
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.block-title { margin: 16px 0 8px; font-weight: 600; }
.answer-box {
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 360px;
  overflow: auto;
  padding: 12px;
  background: #f0f9ff;
  border-radius: 12px;
  line-height: 1.6;
}
.sources { margin: 0; padding-left: 20px; color: var(--color-text-muted); }
.sources li { margin-bottom: 8px; }
.answer-preview { color: var(--color-text-muted); }
</style>

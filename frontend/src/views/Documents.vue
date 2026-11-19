<template>
  <div class="page-shell">
    <PageBanner
      :title="`文档 · ${kbName || ('KB #' + kbId)}`"
      subtitle="上传 PDF / Word / Markdown 等文档，系统将异步解析并写入向量库。"
      eyebrow="知识库"
      :icon="FolderOpened"
    >
      <template #actions>
        <el-button round @click="goBack">返回知识库</el-button>
        <template v-if="canManage">
          <el-input-number v-model="chunkSize" :min="100" :max="2000" size="small" />
          <el-input-number v-model="chunkOverlap" :min="0" :max="500" size="small" title="重叠" />
          <el-upload :http-request="upload" :show-file-list="false">
            <el-button type="primary" round>上传文档</el-button>
          </el-upload>
        </template>
      </template>
    </PageBanner>

    <el-card class="page-panel" shadow="never">
    <el-alert v-if="polling" type="info" :closable="false" show-icon title="有文档正在解析，列表将自动刷新" style="margin-bottom:8px" />
    <el-table :data="items" v-loading="loading">
      <el-table-column prop="filename" label="文件名" show-overflow-tooltip />
      <el-table-column label="大小" width="100">
        <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="上传时间" width="180" />
      <el-table-column prop="error_message" label="失败原因" show-overflow-tooltip />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-upload v-if="canManage" :show-file-list="false" :http-request="(o) => replaceDoc(row.id, o)">
            <el-button link>更新</el-button>
          </el-upload>
          <el-button v-if="canDelete(row)" link type="danger" @click="remove(row.id)">删除</el-button>
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
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { FolderOpened } from '@element-plus/icons-vue'
import PageBanner from '../components/PageBanner.vue'
import http from '../api/http'

const router = useRouter()

function goBack() {
  router.push('/app/kbs')
}

const props = defineProps({ kbId: String })
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const canManage = ref(false)
const myUserId = ref(null)
const kbName = ref('')
const loading = ref(false)
const polling = ref(false)
const chunkSize = ref(500)
const chunkOverlap = ref(50)
let timer = null

function statusLabel(s) {
  return { pending: '待解析', success: '解析成功', failed: '解析失败' }[s] || s
}
function statusType(s) {
  return { pending: 'warning', success: 'success', failed: 'danger' }[s] || 'info'
}
function formatSize(n) {
  if (n < 1024) return n + ' B'
  if (n < 1048576) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1048576).toFixed(1) + ' MB'
}

async function load() {
  loading.value = true
  try {
    const { data } = await http.get('/documents', {
      params: { kb_id: props.kbId, page: page.value, page_size: pageSize },
    })
    items.value = data.items
    total.value = data.total
    canManage.value = data.can_manage
    polling.value = data.items.some((x) => x.status === 'pending')
  } finally {
    loading.value = false
  }
}

async function loadKbName() {
  const { data } = await http.get('/knowledge-bases', { params: { page: 1, page_size: 100 } })
  kbName.value = data.items.find((x) => String(x.id) === String(props.kbId))?.name || ''
}

function uploadParams() {
  return `kb_id=${props.kbId}&chunk_size=${chunkSize.value}&chunk_overlap=${chunkOverlap.value}`
}

async function upload(option) {
  const fd = new FormData()
  fd.append('file', option.file)
  await http.post(`/documents/upload?${uploadParams()}`, fd)
  ElMessage.success('已上传，后台异步解析中')
  load()
  startPoll()
}

async function replaceDoc(docId, option) {
  const fd = new FormData()
  fd.append('file', option.file)
  await http.put(`/documents/${docId}/replace?chunk_size=${chunkSize.value}&chunk_overlap=${chunkOverlap.value}`, fd)
  ElMessage.success('已更新，正在重新解析')
  load()
  startPoll()
}

async function remove(id) {
  await http.delete(`/documents/${id}`)
  ElMessage.success('已删除')
  load()
}

function canDelete(row) {
  return canManage.value || row.uploader_id === myUserId.value
}

function startPoll() {
  if (timer) return
  timer = setInterval(() => {
    if (polling.value) load()
    else {
      clearInterval(timer)
      timer = null
    }
  }, 3000)
}

onMounted(async () => {
  const me = await http.get('/auth/me')
  myUserId.value = me.data.id
  loadKbName()
  load().then(() => {
    if (polling.value) startPoll()
  })
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
watch(() => props.kbId, () => {
  page.value = 1
  loadKbName()
  load()
})
</script>

<style scoped>
.row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.title-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.title { font-weight: 600; }
.actions { display: flex; align-items: center; gap: 8px; }
</style>

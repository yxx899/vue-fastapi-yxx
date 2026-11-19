<template>
  <div class="page-shell">
    <PageBanner
      title="统计看板"
      subtitle="一眼查看本企业知识库、文档与问答健康度，点击卡片可查看明细。"
      eyebrow="管理"
      :icon="DataAnalysis"
    />

    <el-row :gutter="16">
      <el-col :span="6" v-for="item in cards" :key="item.key" style="margin-bottom: 16px">
        <el-card class="stat-tile" shadow="hover" @click="openDetail(item)">
          <div class="num">{{ item.value ?? 0 }}</div>
          <div class="label">{{ item.label }}</div>
          <div class="hint">点击查看详情</div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="720px" destroy-on-close>
      <el-table v-loading="loading" :data="detailRows" max-height="420">
        <el-table-column
          v-for="col in detailColumns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          :width="col.width"
          :show-overflow-tooltip="col.tooltip"
        />
      </el-table>
      <template #footer>
        <el-button v-if="dialogLink" type="primary" link @click="goManage">前往管理页</el-button>
        <el-button @click="dialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { DataAnalysis } from '@element-plus/icons-vue'
import PageBanner from '../../components/PageBanner.vue'
import http from '../../api/http'

const router = useRouter()
const stats = ref({})
const dialogVisible = ref(false)
const dialogTitle = ref('')
const dialogLink = ref('')
const detailRows = ref([])
const detailColumns = ref([])
const loading = ref(false)
const activeKey = ref('')

const cards = computed(() => [
  { key: 'kb', label: '知识库', value: stats.value.kb_count },
  { key: 'doc', label: '文档', value: stats.value.doc_count },
  { key: 'qa_today', label: '今日提问', value: stats.value.qa_today },
  { key: 'qa_total', label: '历史提问', value: stats.value.qa_total },
  { key: 'good', label: '好评', value: stats.value.feedback_good },
  { key: 'bad', label: '差评', value: stats.value.feedback_bad },
  { key: 'failed', label: '解析失败', value: stats.value.failed_documents },
])

async function openDetail(item) {
  activeKey.value = item.key
  dialogVisible.value = true
  loading.value = true
  detailRows.value = []
  detailColumns.value = []
  dialogLink.value = ''

  try {
    if (item.key === 'kb') {
      dialogTitle.value = '知识库明细'
      dialogLink.value = '/app/kbs'
      detailColumns.value = [
        { prop: 'id', label: 'ID', width: 60 },
        { prop: 'name', label: '名称', tooltip: true },
        { prop: 'is_active', label: '启用' },
        { prop: 'is_public_in_tenant', label: '租户公开' },
      ]
      const { data } = await http.get('/audit/knowledge-bases')
      detailRows.value = data.items.map((r) => ({
        ...r,
        is_active: r.is_active ? '是' : '否',
        is_public_in_tenant: r.is_public_in_tenant ? '是' : '否',
      }))
    } else if (item.key === 'doc') {
      dialogTitle.value = '文档明细'
      dialogLink.value = '/app/kbs'
      detailColumns.value = [
        { prop: 'filename', label: '文件名', tooltip: true },
        { prop: 'kb_name', label: '所属知识库' },
        { prop: 'status', label: '状态', width: 90 },
        { prop: 'created_at', label: '上传时间', width: 180 },
      ]
      const { data } = await http.get('/audit/documents')
      detailRows.value = data.items
    } else if (item.key === 'failed') {
      dialogTitle.value = '解析失败文档'
      dialogLink.value = '/app/admin/failed-docs'
      detailColumns.value = [
        { prop: 'filename', label: '文件名', tooltip: true },
        { prop: 'kb_name', label: '知识库' },
        { prop: 'error_message', label: '失败原因', tooltip: true },
      ]
      const { data } = await http.get('/audit/documents/failed')
      detailRows.value = data.items
    } else if (item.key === 'qa_today') {
      dialogTitle.value = '今日提问记录'
      dialogLink.value = '/app/admin/audit?today=1'
      await loadQaLogs({ today_only: true })
    } else if (item.key === 'qa_total') {
      dialogTitle.value = '历史提问记录'
      dialogLink.value = '/app/admin/audit'
      await loadQaLogs({})
    } else if (item.key === 'good') {
      dialogTitle.value = '好评记录'
      dialogLink.value = '/app/admin/audit?feedback=1'
      await loadQaLogs({ feedback: 1 })
    } else if (item.key === 'bad') {
      dialogTitle.value = '差评记录'
      dialogLink.value = '/app/admin/audit?feedback=-1'
      await loadQaLogs({ feedback: -1 })
    }
  } finally {
    loading.value = false
  }
}

async function loadQaLogs(params) {
  detailColumns.value = [
    { prop: 'user_id', label: '用户', width: 70 },
    { prop: 'question', label: '问题', tooltip: true },
    { prop: 'answer_preview', label: '回答摘要', tooltip: true },
    { prop: 'created_at', label: '时间', width: 180 },
  ]
  const { data } = await http.get('/audit/logs', { params: { page: 1, page_size: 50, ...params } })
  detailRows.value = data.items
}

function goManage() {
  if (dialogLink.value) router.push(dialogLink.value)
  dialogVisible.value = false
}

onMounted(async () => {
  const { data } = await http.get('/audit/dashboard')
  stats.value = data
})
</script>

<template>
  <div class="page-shell">
    <PageBanner
      title="历史问答"
      subtitle="查找自己问过的问题与回答，点击可回到原对话继续查看。"
      eyebrow="个人"
      :icon="Clock"
    >
      <template #actions>
        <el-button type="primary" round @click="$router.push('/app/chat')">去提问</el-button>
      </template>
    </PageBanner>

    <el-card class="page-panel" shadow="never">
      <div class="toolbar">
        <el-input
          v-model="keyword"
          clearable
          placeholder="搜索问题关键词"
          style="width: 280px"
          @keyup.enter="search"
          @clear="search"
        />
        <el-button type="primary" @click="search">查询</el-button>
      </div>

      <el-table v-loading="loading" :data="items" style="margin-top: 12px" empty-text="暂无历史问答">
        <el-table-column prop="question" label="问题" min-width="180" />
        <el-table-column label="回答摘要" min-width="280">
          <template #default="{ row }">
            <span class="answer-preview">{{ row.answer_preview || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="反馈" width="80">
          <template #default="{ row }">
            {{ feedbackText(row.feedback) }}
          </template>
        </el-table-column>
        <el-table-column prop="session_title" label="所属会话" width="120" />
        <el-table-column prop="created_at" label="时间" width="180" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button link type="primary" @click="openChat(row)">打开对话</el-button>
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

    <el-dialog v-model="detailVisible" title="问答详情" width="720px" destroy-on-close>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="所属会话">{{ current.session_title || '—' }}</el-descriptions-item>
        <el-descriptions-item label="提问时间">{{ current.created_at }}</el-descriptions-item>
        <el-descriptions-item label="反馈">{{ feedbackText(current.feedback) }}</el-descriptions-item>
        <el-descriptions-item label="问题">{{ current.question }}</el-descriptions-item>
      </el-descriptions>
      <div class="block-title">回答</div>
      <div class="answer-box">{{ current.answer || '（无回答）' }}</div>
      <template #footer>
        <el-button type="primary" @click="openChat(current)">打开对话</el-button>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Clock } from '@element-plus/icons-vue'
import PageBanner from '../components/PageBanner.vue'
import http, { formatApiError } from '../api/http'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const keyword = ref('')
const detailVisible = ref(false)
const current = ref({})

function feedbackText(v) {
  if (v === 1) return '有用'
  if (v === -1) return '无用'
  return '—'
}

async function load() {
  loading.value = true
  try {
    const { data } = await http.get('/chat/history', {
      params: {
        page: page.value,
        page_size: pageSize,
        keyword: keyword.value.trim() || undefined,
      },
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    ElMessage.error(formatApiError(e, '加载失败'))
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  load()
}

function openDetail(row) {
  current.value = row
  detailVisible.value = true
}

function openChat(row) {
  if (!row?.session_id) {
    ElMessage.warning('无法定位原对话')
    return
  }
  detailVisible.value = false
  router.push({ path: '/app/chat', query: { session: String(row.session_id) } })
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.answer-preview {
  color: #64748b;
  font-size: 13px;
}
.block-title {
  margin: 16px 0 8px;
  font-weight: 600;
}
.answer-box {
  white-space: pre-wrap;
  line-height: 1.6;
  padding: 12px;
  background: var(--color-bg-elevated, #f8fafc);
  border-radius: 8px;
  max-height: 360px;
  overflow: auto;
}
</style>

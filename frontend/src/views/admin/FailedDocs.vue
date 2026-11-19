<template>
  <div class="page-shell">
    <PageBanner
      title="解析失败"
      subtitle="集中查看未能入库的文档，可一键重新触发解析。"
      eyebrow="管理"
      :icon="WarningFilled"
    >
      <template #actions>
        <el-button round @click="load" :loading="loading">刷新</el-button>
      </template>
    </PageBanner>

    <el-card class="page-panel" shadow="never">
      <el-empty v-if="!loading && !items.length" description="暂无解析失败记录，状态良好" />
      <el-table v-else :data="items" v-loading="loading">
        <el-table-column prop="filename" label="文件名" show-overflow-tooltip />
        <el-table-column prop="kb_id" label="知识库ID" width="100" />
        <el-table-column prop="error_message" label="失败原因" show-overflow-tooltip />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link type="primary" @click="reparse(row.id)">重新解析</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { WarningFilled } from '@element-plus/icons-vue'
import PageBanner from '../../components/PageBanner.vue'
import http from '../../api/http'

const items = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await http.get('/documents/failed/list')
    items.value = data.items
  } finally {
    loading.value = false
  }
}

async function reparse(id) {
  await http.post(`/documents/${id}/reparse`)
  ElMessage.success('已触发重新解析')
  load()
}

onMounted(load)
</script>

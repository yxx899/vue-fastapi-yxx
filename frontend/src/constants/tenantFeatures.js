/** 与后端 DEFAULT_TENANT_FEATURES 键名一致 */
export const TENANT_FEATURE_META = [
  { key: 'chat', label: 'AI 问答' },
  { key: 'knowledge_base', label: '知识库' },
  { key: 'document_upload', label: '文档上传' },
  { key: 'statistics_dashboard', label: '统计看板' },
  { key: 'user_management', label: '用户管理' },
  { key: 'department_management', label: '部门管理' },
  { key: 'audit', label: '问答审计' },
  { key: 'audit_export', label: '审计 CSV 导出' },
]

export function featureEnabled(policy, key) {
  return policy?.features?.[key] !== false
}

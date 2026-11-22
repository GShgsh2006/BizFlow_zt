import http from './http.js'

// 员工档案（Excel 导出链路）
// 后端优先走 RabbitMQ：投递任务 -> worker 查库 -> 回传结果；
// MQ 不可用时自动降级为本地直算，接口照样能用。
// 走的是哪条路由后端写在 X-Data-Source 响应头里（mq | local）。

function pickSource(headers) {
  return headers?.['x-data-source'] || ''
}

// 预览数据：{ rows: [{ name, tasks, salary }], source: 'mq' | 'local' }
export async function previewEmployees() {
  const res = await http.get('/dsz/employees/preview', {
    timeout: 70000,
    raw: true
  })
  return {
    rows: Array.isArray(res.data) ? res.data : [],
    source: pickSource(res.headers)
  }
}

// 取 Excel 二进制；mode: 'view' 浏览器内打开 | 'download' 直接下载
// 返回 { blob, source }
export async function fetchEmployeesExcel(mode = 'download') {
  const res = await http.get(`/dsz/employees/${mode}`, {
    responseType: 'blob',
    timeout: 70000,
    raw: true
  })
  return {
    blob: res.data,
    source: pickSource(res.headers)
  }
}

// 从 blob 错误响应里挖出后端的 detail（否则只会显示 [object Blob]）
export async function readBlobError(err, fallback = '操作失败') {
  const data = err?.response?.data
  if (data instanceof Blob) {
    try {
      const text = await data.text()
      const json = JSON.parse(text)
      return json.detail || json.message || fallback
    } catch {
      return fallback
    }
  }
  return data?.detail || data?.message || fallback
}

import http from './http.js'

// 首页「平台概览」用的真实数据源，不做任何写死的假数字。

const HTTP_METHODS = ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']

// 接口总数：直接读后端的 OpenAPI 文档，统计真实注册的接口数量。
// /openapi.json 在后端鉴权白名单里，不带 token 也能访问。
export async function fetchApiTotal() {
  const doc = await http.get('/openapi.json', { timeout: 15000 })
  const paths = doc?.paths
  if (!paths || typeof paths !== 'object') return 0

  return Object.values(paths).reduce(
    (total, item) =>
      total +
      Object.keys(item || {}).filter((k) => HTTP_METHODS.includes(k)).length,
    0
  )
}

// 服务状态：打一个真实查库的接口（GET /all_stall 会 SELECT users），
// 能通就说明「后端 + 数据库」这条链路是活的。
// 返回 { ok, ms }
export async function probeBackend() {
  const start = Date.now()
  try {
    await http.get('/all_stall', { timeout: 8000 })
    return { ok: true, ms: Date.now() - start }
  } catch (e) {
    return { ok: false, ms: Date.now() - start }
  }
}

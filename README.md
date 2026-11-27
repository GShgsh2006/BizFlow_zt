BizFlow 可以按“一个平台、三条链路”来讲，不用逐文件解释。

一句话定位 基于 FastAPI 的业务协作平台，业务侧有登录、任务、审批、工资；AI 侧有 RAG 知识库问答和 LangGraph Agent；长耗时任务用 RabbitMQ 解耦，前端 Vue 3。

分层架构

- 接入层：FastAPI 路由，REST + SSE，JWT 鉴权，按用户 1 秒限流
- 业务层：任务、审批、工资、员工、个人中心
- AI 层：RAG 检索问答、LangGraph Agent、RAGAS 评估
- 异步层：RabbitMQ 任务 / 结果 / 长期记忆 / 死信四类队列
- 数据层：MySQL 8 + SQLAlchemy + Alembic，Chroma 持久化向量库
- 部署：Docker Compose 编排 app、MySQL、RabbitMQ，带健康检查
- 前端：Vue 3 + Vite + vue-router + axios
技术栈逐项说清“为什么”

- FastAPI ：异步接口和 SSE 流式输出，Pydantic 做请求校验，lifespan 管启动初始化。
- JWT（python-jose） ：无状态鉴权，`Authorization: Bearer` ，无效 token 统一 401，前端拦截器跳登录。
- SQLAlchemy + Alembic ：ORM 建模 + 表结构迁移，避免手改库。
- Chroma ：本地持久化向量库，cosine 距离；每次启动重建，防止切分逻辑变化后`metadata["idx"]` 指向错父块。
- text2vec-base-chinese ：768 维、向量归一化、强制离线加载，避免 HuggingFace 联网超时。
- BM25 + jieba ：中文关键词召回，弥补向量对专有名词、编号不敏感。
- RRF ：`1/(rank+1)` 按排名融合，不需要把 BM25 和余弦分数归一化，工程上更稳。
- Ollama qwen3.5:9b ：本地推理，`keep_alive=30m` 常驻显存，启动时`num_predict=1` 预热。
- SSE ：按`contexts / thinking / answer / error / [DONE]` 分事件，前端能先展示检索依据再逐字出答案。
- LangGraph ：StateGraph + ToolNode +`interrupt()` + Checkpointer，按`thread_id` 保存快照，人工审核后`Command(resume=...)` 从断点继续。
- RabbitMQ（aio_pika） ：direct exchange，任务队列消费失败进死信，结果队列回传，长期记忆独立队列，durable + 手动 ack。
- LangSmith ：`tracing_context` 按链路开关，Agent / 审批全量采样，高频 RAG 关闭，控制数据量。
- Docker Compose ：`depends_on` + healthcheck 保证启动顺序，MySQL 映射 3308 避开宿主冲突。

##BizFlow 智能业务协作平台
#ai_Memory —— AI 记忆包（短期记忆 + 长期记忆）
#
# 目录结构：
#   checkpointer.py   官方 SQLite Checkpointer（LangGraph 短期记忆落库）
#   short_term.py     thread_id 会话管理（短期记忆的边界与归属）
#   long_term.py      长期记忆：抽取 + 读写 + 拼提示词
#   memory_service.py 一次请求的记忆编排（对外统一入口）
#   mq_producer.py    长期记忆任务的 MQ 生产端
#   mq_consumer.py    长期记忆任务的 MQ 消费端（含「按 id 校验归属」）
#
# 表定义（ai_ckpt_threads / ai_long_memory）放在 shujuku/user.py，
# 和项目其它表一致，migrate() 才能自动扫到并建表。
# 短期记忆的 checkpoint 快照存在本地 checkpoints.sqlite，由官方 saver 自建表，
# 不进 MySQL —— 所以这里没有 ai_ckpt_checkpoints / ai_ckpt_writes。
#
# 注意：本文件刻意不 import 任何子模块。
# 一旦这里 import 了 checkpointer / long_term，任何 from ...ai_Memory import x
# 都会把 langgraph、langchain_ollama 这些重依赖拖进迁移流程。
# 需要什么就直接 import 对应子模块。

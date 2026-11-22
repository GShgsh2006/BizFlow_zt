from BizFlow.shujuku.Management import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String,Index,Text
from sqlalchemy import DateTime
from datetime import datetime
class users(Base):
   __tablename__ = 'user'
   id:Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
   name:Mapped[str] = mapped_column(String(200),unique=True)
   password:Mapped[str] = mapped_column(String(200))
   employee_ID:Mapped[int] = mapped_column(Integer,unique=True)#工号
   position:Mapped[str] = mapped_column(String(200))#职位
   users_sy=(
      Index("idx_height_school_blood","id","position")
   )


class task(Base):
   __tablename__ = 'task'
   id:Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
   name:Mapped[str] = mapped_column(String(200))#任务名称
   Deadline:Mapped[DateTime] = mapped_column(DateTime)#截止时间
   content:Mapped[str] = mapped_column(String(500))#内容
   assignor :Mapped[str] = mapped_column(String(500))#发布人
   assignee_id :Mapped[int] = mapped_column(Integer)#接收人
   status:Mapped[str] = mapped_column(String(200))#完成状态
   amount:Mapped[int] = mapped_column(Integer)#金额
   task_sy=(
      Index("idx_height_school_blood","assignee_id","amount")
   )
   task_sy_rw=(
      Index("task_sy_rw_id","assignee_id","name","status")
   )
#我们自己创造的表
class employees(Base):
   __tablename__ = 'employee'
   id:Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
   name:Mapped[str] = mapped_column(String(200))
   name_rw:Mapped[str] = mapped_column(String(200))
   content: Mapped[str] = mapped_column(String(500))  # 内容
   status: Mapped[str] = mapped_column(String(200))  # 完成状态
   progress:Mapped[int] = mapped_column(Integer)#完成进度
   employee_rw=(
      Index("employee_rw","id","content","status")
   )


#员工提交表格
class yg_tjs(Base):
   __tablename__ = 'yg_tj'

   id:Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
   name:Mapped[str] = mapped_column(String(200))
   name_rw: Mapped[str] = mapped_column(String(200))
   content: Mapped[str] = mapped_column(String(500))
   assignee_id:Mapped[int] = mapped_column(Integer)
   zt:Mapped[str] = mapped_column(String(200))



#员工接收通知（已读未读表）
class notice(Base):
   __tablename__ = 'notice'
   id:Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
   name_id:Mapped[str] = mapped_column(String(200))#人物的id
   name:Mapped[str] = mapped_column(String(200))
   assignee:Mapped[str] = mapped_column(String(200))
   Read:Mapped[str] = mapped_column(String(200))



#员工年假表
class yynj(Base):
   __tablename__ = 'yynj'
   id:Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
   name:Mapped[str] = mapped_column(String(200))
   days:Mapped[int] = mapped_column(Integer)#请假天数

#优秀员工表
class yyygb(Base):
   __tablename__ = 'yyygb'
   id:Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
   name:Mapped[str] = mapped_column(String(200))

#ai记录表
class ai_jl(Base):
   __tablename__ = 'ai_jl'
   id:Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)#每条记录的id
   name_id:Mapped[str] = mapped_column(String(200))
   HumanMessage:Mapped[str] = mapped_column(Text)
   AIMessage:Mapped[str] = mapped_column(Text)
   __table_args__ = (
      Index("idx_name_id_id", "name_id", "id"),
   )
#权限表
class qxb(Base):
   __tablename__ = 'qxb'
   id:Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
   code:Mapped[str] = mapped_column(String(500))
   name:Mapped[str] = mapped_column(String(200))
#角色表
class jsb(Base):
   __tablename__ = 'jsb'
   id:Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
   name:Mapped[str] = mapped_column(String(200))
#关系表
class gxb(Base):
   __tablename__ = 'gxb'
   js_id:Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
   js_qx:Mapped[str] = mapped_column(String(500))

class mq_mdj(Base):
   __tablename__ = 'mq_mdj'
   task_id:Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
   zhuangtai:Mapped[str] = mapped_column(String(200))


class RAGAS(Base):
   __tablename__ = 'RAGAS'
   id:Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
   name:Mapped[str] = mapped_column(String(500))
   # 四个指标统一存 0~100 的整数：这几列是 Integer，
   # 直接写 0.85 会被 MySQL 四舍五入成 1，分数就废了。
   faithfulness:Mapped[int] = mapped_column(Integer)
   answer_relevancy:Mapped[int] = mapped_column(Integer)
   Context_Precision:Mapped[int] = mapped_column(Integer)
   context_recall:Mapped[int] = mapped_column(Integer)


class ai_jy_dq(Base):
   __tablename__ = 'ai_jy_dq'
   id:Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
   ai_dh:Mapped[str] = mapped_column(String(1000))
   human_message:Mapped[str] = mapped_column(String(1000))

class ai_cq_jiy(Base):
   __tablename__ = 'ai_cq_jiy'
   id:Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
   ai_hd:Mapped[str] = mapped_column(String(1000))
   human_message:Mapped[str] = mapped_column(String(1000))


#AI 记忆相关表（长期记忆 + 线程归属）
#短期记忆的 checkpoint 快照由 LangGraph 官方 SQLite Checkpointer 存
#（见 hdwj/LangGarph/ai_Memory/checkpointer.py），不再进 MySQL。
#这里只保留长期记忆，以及「thread 属于谁」——官方 Checkpointer 不带人的概念。


class AiCkptThread(Base):
   """短期记忆的线程归属表：thread_id -> 用户 / 会话。

   LangGraph 的 Checkpointer 只认 thread_id，本身不带「人」的概念。
   这张表把归属关系记下来，长期记忆消费者才能校验
   「这条任务是不是这个用户发出来的」（按 id 校验）。
   """

   __tablename__ = 'ai_ckpt_threads'
   thread_id:Mapped[str] = mapped_column(String(128), primary_key=True)
   user_id:Mapped[str] = mapped_column(String(128), index=True)
   session_id:Mapped[str | None] = mapped_column(String(128), nullable=True)
   created_at:Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
   updated_at:Mapped[datetime] = mapped_column(
      DateTime, default=datetime.now, onupdate=datetime.now
   )


class AiLongMemory(Base):
   """长期记忆：AI 从一轮对话里抽取出来、值得跨会话保留的用户信息。"""

   __tablename__ = 'ai_long_memory'
   id:Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
   user_id:Mapped[str] = mapped_column(String(128))
   session_id:Mapped[str | None] = mapped_column(String(128), nullable=True)
   thread_id:Mapped[str | None] = mapped_column(String(128), nullable=True)
   memory:Mapped[str] = mapped_column(Text)
   source_human:Mapped[str | None] = mapped_column(String(1000), nullable=True)
   source_ai:Mapped[str | None] = mapped_column(String(1000), nullable=True)
   created_at:Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
   __table_args__ = (
      # 取某个用户的长期记忆时按 user_id 过滤、按 id 倒序，正好走这条索引
      Index("idx_ai_long_memory_user", "user_id", "id"),
   )
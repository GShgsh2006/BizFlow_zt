#董事长查询所有员工信息（MQ worker 调用，返回纯数据，Excel 由路由层生成）
import logging

from sqlalchemy.orm import Session
import asyncio
from BizFlow.hdwj.Exception.exceptions import hdwjException
from BizFlow.shujuku.user import task,users,employees
from BizFlow.hdwj.function.Salary_hs import salary
from BizFlow.shujuku.Management import SessionLocal
from fastapi import Depends
from BizFlow.hdwj.tool.huancun import Huancun,redis_client

logger = logging.getLogger(__name__)

CACHE_KEY_DSZ = "所有员工的信息"


async def query_dsz(zd: dict):
    """查询所有员工的任务与工资，返回可 JSON 序列化的列表。

    返回 [{"name": 姓名, "tasks": 任务名, "salary": 工资}, ...]
    Excel 不在这里生成，交给路由层 build_excel 统一处理一次。
    """
    token = zd.get("token") or {}
    if token.get("role") != "董事长":
        raise hdwjException(500, "你还没有权限访问这个接口")

    huancun = Huancun(redis_client)

    # Redis 没起来时降级为直接查库，不让整个导出挂掉
    try:
        cached = await huancun.huancun_dq(CACHE_KEY_DSZ)
    except Exception as e:
        logger.warning("读取员工缓存失败，已降级为查库: %s", e)
        cached = None

    if cached is not None:
        return cached

    db: Session = SessionLocal()
    try:
        values = []
        for i in db.query(users).all():
            if i.position != "员工":
                continue

            # 兼容老版本 SQLAlchemy：Query 没有 scalars()
            rows = [r[0] for r in db.query(task.name).filter(task.assignee_id == i.id).all()]
            try:
                gz = salary(i.id, db)
            except hdwjException:
                gz = 0

            values.append(
                {
                    "name": i.name,
                    "tasks": "、".join(rows) if rows else "",
                    "salary": gz,
                }
            )
    finally:
        db.close()

    try:
        await huancun.huancun_xr(CACHE_KEY_DSZ, values)
    except Exception as e:
        logger.warning("写入员工缓存失败（不影响返回）: %s", e)

    return values



####练习接口
EMPTY = ["__EMPTY__" ]  # 空值缓存标志，防穿透
class EmployeeCache:
    def __init__(self, db):
        self.huancun=Huancun(redis_client)
        self.db = db
        self.locks = {}                     # key -> asyncio.Lock
        self.locks_guard = asyncio.Lock()   # 保护 self.locks 字典

    # 按 key 拿锁对象：有就返回，没有就创建
    async def _get_lock(self, key: str) -> asyncio.Lock:
        async with self.locks_guard:
            if key not in self.locks:
                self.locks[key] = asyncio.Lock()
            return self.locks[key]

    # ---------- 查单个员工 ----------
    async def get_employee(self, emp_id: int,db: Session):
        from BizFlow.shujuku.user import task, users, employees
        key = f"employee:{emp_id}"

        # 第 1 步：先查缓存
        data = await self.huancun.huancun_dq(key)
        if data == EMPTY:
            return None                       # 命中空值缓存，防穿透
        if data is not None:
            return data                       # 命中正常缓存

        # 第 2 步：缓存没命中，拿这个 key 的锁对象
        lock = await self._get_lock(key)

        # 第 3 步：加锁，只放一个协程进入
        async with lock:
            # 第 4 步：双重检查
            data = await self.huancun.huancun_dq(key)
            if data == EMPTY:
                return None
            if data is not None:
                return data
            a={}
            # 第 5 步：查数据库
            db_data =db.query(users.name).filter(users.id==emp_id).first()
            tasks=db.query(task.name).filter(task.assignee_id==emp_id).all()
            salarys=salary(emp_id,db)
            a["tasks"]=tasks
            a["salarys"]=salarys
            a['db_data']=db_data
            # 第 6 步：数据库也没有 → 写空值缓存，防穿透
            if a is None:
                await self.huancun.huancun_xr(key, EMPTY)
                return None

            # 第 7 步：数据库有 → 写正常缓存
            await self.huancun.huancun_xr(key, a)
            return {"text":a}

    # ---------- 修改员工：先更新数据库，再删缓存 ----------
    async def update_employee(self, emp_id: int, new_data: dict):
        await self.db.update_employee(emp_id, new_data)
        await self.huancun.huancun_sc(f"employee:{emp_id}")

    # ---------- 删除员工：删数据库 + 删缓存 ----------
    async def delete_employee(self, emp_id: int):
        await self.db.delete_employee(emp_id)
        await self.huancun.huancun_sc(f"employee:{emp_id}")






# BizFlow/hdwj/test_pytext/test_tools/test_shujuku.py


import pytest

from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool



# =====================================
# 1. 创建临时 SQLite 数据库
# =====================================

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={
        "check_same_thread": False
    },
    poolclass=StaticPool,
)



TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
)



# =====================================
# 2. 导入 Base 和全部模型
# =====================================

from BizFlow.shujuku.Management import Base


# 必须导入模型
# 让 SQLAlchemy 注册所有表结构

from BizFlow.shujuku.user import (
    users,
    task,
    employees,
    yg_tjs,
    notice,
    yynj,
    yyygb,
    ai_jl,
)



# =====================================
# 3. 创建临时数据库表
# =====================================

@pytest.fixture(
    scope="session",
    autouse=True
)
def create_test_tables():


    print(
        "测试数据库表:",
        list(Base.metadata.tables.keys())
    )


    Base.metadata.create_all(
        bind=test_engine
    )


    yield


    Base.metadata.drop_all(
        bind=test_engine
    )



# =====================================
# 4. 覆盖 FastAPI 数据库依赖
# =====================================

def override_get_db():


    db = TestingSessionLocal()


    try:

        yield db


    finally:

        db.close()



# =====================================
# 5. FastAPI 测试客户端
# =====================================

@pytest.fixture
def client():


    from BizFlow.hdwj.app import app

    from BizFlow.shujuku.Management import get_db



    old_override = (
        app.dependency_overrides.copy()
    )


    # 使用测试 SQLite
    app.dependency_overrides[get_db] = override_get_db



    with TestClient(app) as test_client:

        yield test_client



    # 恢复

    app.dependency_overrides.clear()

    app.dependency_overrides.update(
        old_override
    )



# =====================================
# 6. 测试直接操作数据库
# =====================================

@pytest.fixture
def db_session():


    db = TestingSessionLocal()


    try:

        yield db


    finally:

        db.close()
"""pytest 全局配置：测试库隔离 + 公共 fixtures。

关键点：
- app.core.db 的 engine 是模块级创建，因此 DB_URL 必须在导入任何 app 模块之前设置；
  conftest 在所有测试模块之前加载，满足时序要求。
- 使用文件型 sqlite（避免 sqlite:///:memory: 每连接独立导致跨请求丢失数据）。
- 每个测试函数重新 drop_all + create_all + 导入种子数据，保证测试间隔离。
"""

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

_TEST_DB_PATH = Path(tempfile.gettempdir()) / "ai_recipe_pytest.db"
os.environ["DB_URL"] = f"sqlite:///{_TEST_DB_PATH.as_posix()}"

import pytest  # noqa: E402

from app.core.db import Base, SessionLocal, engine, ensure_models_imported  # noqa: E402

ensure_models_imported()  # 注册全部表模型（对齐 ORM 聚合导入）


@pytest.fixture()
def db():
    """干净的数据库会话：重建全部表并导入种子数据（food_nutrition/dris）。"""
    from resources.init_data.import_seed import main as seed_main

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    seed_main()

    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def client(db):
    """TestClient：with 上下文触发 startup 建表（幂等）。"""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c

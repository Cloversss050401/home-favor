"""数据库会话管理：引擎创建、Session 工厂、FastAPI 依赖注入。"""

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import settings
from src.models import Base

# 引擎：连接 MySQL；Redis 用于缓存字典表（food_nutrition/dris/synonym）
engine = create_engine(
    settings.DB_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：每请求一个会话，异常回滚，请求结束关闭。"""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _migrate_legacy_schemas() -> None:
    """轻量迁移（幂等）：旧库升级，不重建表、不丢数据。

    当前迁移项：
    - family 表补 is_deleted 列（DEF-01 修复：逻辑删除字段对齐硬性业务规则）。
    """
    inspector = inspect(engine)
    if "family" in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns("family")}
        if "is_deleted" not in columns:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE family ADD COLUMN is_deleted INTEGER "
                        "NOT NULL DEFAULT 0"
                    )
                )
            print("[migrate] family.is_deleted 已补充")


def init_db() -> None:
    """建表（开发期使用）；随后执行幂等轻量迁移。生产环境建议迁移工具。"""
    Base.metadata.create_all(bind=engine)
    _migrate_legacy_schemas()

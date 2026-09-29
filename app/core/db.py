"""数据库核心：引擎、会话工厂、ORM 基类、建表与轻量迁移。

对应文档 app/core（全局通用能力）；
FastAPI 请求级依赖注入 get_db 见 app/common/deps.py。
"""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# 项目 ORM 基类：全部表模型继承本类
class Base(DeclarativeBase):
    """项目 ORM 基类。"""


# 引擎：连接 MySQL；Redis 用于缓存字典表（food_nutrition/dris/synonym）
engine = create_engine(
    settings.DB_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def ensure_models_imported() -> None:
    """注册全部 ORM 模型（延迟导入，规避 models→Base 循环依赖）。

    各模块 models 通过 `from app.core.db import Base` 继承基类；
    在本函数被调用前建表元数据不完整，drop_all/create_all 前必须先调用。
    """

    from app.modules.family_member import models as _fm
    from app.modules.ingredient import models as _ig
    from app.modules.nutrition import models as _nt
    from app.modules.personal_center import models as _pc
    from app.modules.recipe import models as _rc

    _ = (_fm, _ig, _nt, _pc, _rc)


def _migrate_legacy_schemas() -> None:
    """轻量迁移（幂等）：旧库升级，不重建表、不丢数据。

    当前迁移项：
    - family 表补 is_deleted 列（DEF-01 修复：逻辑删除字段对齐硬性业务规则）。
    - family_member 表补前端契约列 role / traits / avoid（前端档案表单适配，
      旧记录以默认值填充，不影响已有人档案）。
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

    if "family_member" in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns("family_member")}
        alters = []
        if "role" not in columns:
            alters.append(
                "ALTER TABLE family_member ADD COLUMN role VARCHAR(20) "
                "NOT NULL DEFAULT ''"
            )
        if "traits" not in columns:
            alters.append(
                "ALTER TABLE family_member ADD COLUMN traits TEXT NOT NULL DEFAULT '[]'"
            )
        if "avoid" not in columns:
            alters.append(
                "ALTER TABLE family_member ADD COLUMN avoid VARCHAR(200) "
                "NOT NULL DEFAULT ''"
            )
        if alters:
            with engine.begin() as conn:
                for stmt in alters:
                    conn.execute(text(stmt))
            print("[migrate] family_member 已补充 role/traits/avoid")


def init_db() -> None:
    """建表（开发期使用）；随后执行幂等轻量迁移。生产环境建议迁移工具。"""
    ensure_models_imported()
    Base.metadata.create_all(bind=engine)
    _migrate_legacy_schemas()

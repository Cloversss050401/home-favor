"""公共依赖注入：FastAPI 请求级数据库会话。

对应文档 app/common/deps.py；其他公共依赖（鉴权/请求校验等）后续在此扩展。
"""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.core.db import SessionLocal


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

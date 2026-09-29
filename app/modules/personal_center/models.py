"""个人中心 ORM 模型：UserProfile 用户个人资料表。

一期：全局单条记录（单用户模拟，代表当前使用者），无 user_id；
二期扩展时增加 user_id 字段支持多用户，并接入登录鉴权。

对齐项目 ORM 规范（Mapped/mapped_column 新风格）：时间字段采用
DateTime + server_default=func.now()（文档伪码中的 String 改为项目惯例，
字段名 create_time/update_time 保持不变）。
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class UserProfile(Base):
    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    avatar_url: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="头像访问地址"
    )
    signature: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="个性签名"
    )
    phone: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="手机号"
    )
    username: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="账号名"
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="密码哈希，不存明文"
    )
    create_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UserProfile id={self.id} username={self.username}>"

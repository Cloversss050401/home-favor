"""个人中心仓库：纯数据存取，无业务判断。

对齐项目 repository 层规范：同步 Session + CRUD，不包含业务逻辑。
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.modules.personal_center.models import UserProfile


class ProfileRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_profile(self) -> Optional[UserProfile]:
        """一期：只取第一条记录（模拟当前登录用户）。"""
        return self.db.query(UserProfile).order_by(UserProfile.id.asc()).first()

    def update(self, profile: UserProfile) -> UserProfile:
        """提交字段变更并落库（新记录先 add 再 commit）。"""
        self.db.commit()
        self.db.refresh(profile)
        return profile

"""家庭仓库：纯数据存取，无业务判断。"""
from typing import Optional
from sqlalchemy.orm import Session
from src.models.family_model import Family

class FamilyRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, family_id: int) -> Optional[Family]:
        return self.db.get(Family, family_id)

    def get_or_create_default(self) -> Family:
        """单家庭模式：取第一条未删除家庭，不存在则创建默认家庭。"""
        family = (
            self.db.query(Family)
            .filter(Family.is_deleted == 0)
            .order_by(Family.id.asc())
            .first()
        )
        if family is None:
            family = Family(name="我的家庭")
            self.db.add(family)
            self.db.commit()
            self.db.refresh(family)
        return family

    def update(self, family: Family) -> Family:
        """提交家庭字段变更并落库。"""
        self.db.commit()
        self.db.refresh(family)
        return family

"""家庭仓库：纯数据存取，无业务判断。"""
from typing import Optional
from sqlalchemy.orm import Session
from app.modules.family_member.models import Family

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


from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.constants import DELETE_FLAG_ACTIVE, DELETE_FLAG_DELETED
from app.modules.family_member.models import FamilyMember

class MemberRepo:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, member: FamilyMember) -> FamilyMember:
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def update(self, member: FamilyMember) -> FamilyMember:
        self.db.commit()
        self.db.refresh(member)
        return member

    def get(self, member_id: int) -> Optional[FamilyMember]:
        return self.db.get(FamilyMember, member_id)

    def list_active(self, family_id: int) -> list[FamilyMember]:
        stmt = (
            select(FamilyMember)
            .where(
                FamilyMember.family_id == family_id,
                FamilyMember.is_deleted == DELETE_FLAG_ACTIVE,
            )
            .order_by(FamilyMember.id.asc())
        )
        return list(self.db.scalars(stmt))

    def count_active(self, family_id: int) -> int:
        stmt = select(FamilyMember).where(
            FamilyMember.family_id == family_id,
            FamilyMember.is_deleted == DELETE_FLAG_ACTIVE,
        )
        return len(list(self.db.scalars(stmt)))

    def soft_delete(self, member: FamilyMember) -> FamilyMember:
        """逻辑删除：仅置 is_deleted=1，禁止物理删除。"""
        member.is_deleted = DELETE_FLAG_DELETED
        self.db.commit()
        self.db.refresh(member)
        return member

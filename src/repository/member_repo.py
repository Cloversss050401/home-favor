"""家庭成员仓库：纯数据存取，业务规则（上限、校验）在 service 层。"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.config.constants import DELETE_FLAG_ACTIVE, DELETE_FLAG_DELETED
from src.models.member_model import FamilyMember

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

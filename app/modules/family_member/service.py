"""家庭档案业务：成员 CRUD、8 人上限、字段校验、逻辑删除。

对齐硬性业务规则第 3 条：
- 单家庭最多 8 位成员
- 删除使用逻辑删除 is_deleted，禁止物理删除；历史数据保留，已删除成员不再参与新业务
"""

from sqlalchemy.orm import Session

from app.core.constants import MEMBER_FAMILY_LIMIT
from app.core.exceptions import MemberLimitExceeded, MemberNotFound
from app.modules.family_member.models import Family
from app.modules.family_member.models import FamilyMember
from app.modules.family_member.repository import FamilyRepo
from app.modules.family_member.repository import MemberRepo
from app.modules.family_member.schemas import MemberCreate, MemberUpdate


class FamilyService:
    """家庭成员档案服务（单家庭模式，family_id 默认 1）。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.family_repo = FamilyRepo(db)
        self.member_repo = MemberRepo(db)

    def ensure_family(self) -> int:
        family = self.family_repo.get_or_create_default()
        return family.id

    def get_family(self) -> Family:
        """获取（或创建）默认家庭档案：档案持久化的读取入口。"""
        return self.family_repo.get_or_create_default()

    def update_family_name(self, name: str) -> Family:
        """更新家庭名称：档案持久化的写入入口（一期单家庭模式）。"""
        family = self.get_family()
        family.name = name.strip()
        return self.family_repo.update(family)

    def list_members(self, family_id: int | None = None) -> list[FamilyMember]:
        fid = family_id or self.ensure_family()
        return self.member_repo.list_active(fid)

    def get_member(self, member_id: int) -> FamilyMember:
        member = self.member_repo.get(member_id)
        if member is None or member.is_deleted != 0:
            raise MemberNotFound()
        return member

    def create_member(self, payload: MemberCreate) -> FamilyMember:
        fid = payload.family_id if payload.family_id else self.ensure_family()
        if self.member_repo.count_active(fid) >= MEMBER_FAMILY_LIMIT:
            raise MemberLimitExceeded(MEMBER_FAMILY_LIMIT)

        member = FamilyMember(
            family_id=fid,
            name=payload.name,
            role=payload.role,
            height_cm=payload.height_cm,
            weight_kg=payload.weight_kg,
            activity=payload.activity or "light",
            age=payload.age,
            gender=payload.gender,
            diet_goal=payload.diet_goal,
            dietary_needs=payload.dietary_needs or [],
            avoid=payload.avoid,
            constitution=payload.constitution,
            health_conditions=payload.health_conditions,
            allergens=payload.allergens,
            dietary_restrictions=payload.dietary_restrictions,
        )
        return self.member_repo.create(member)

    def update_member(self, member_id: int, payload: MemberUpdate) -> FamilyMember:
        member = self.get_member(member_id)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(member, field, value)
        return self.member_repo.update(member)

    def delete_member(self, member_id: int) -> FamilyMember:
        """逻辑删除：is_deleted=1；历史食谱/反馈/周报 JSON 保留不变。"""
        member = self.get_member(member_id)
        return self.member_repo.soft_delete(member)

    def active_member_count(self, family_id: int | None = None) -> int:
        fid = family_id or self.ensure_family()
        return self.member_repo.count_active(fid)

"""家庭档案服务测试：成员 CRUD、8 人上限、逻辑删除。"""
from decimal import Decimal

import pytest

from app.core.exceptions import MemberLimitExceeded, MemberNotFound
from app.modules.family_member.schemas import MemberCreate, MemberUpdate
from app.modules.family_member.service import FamilyService


def _payload(name: str = "小明", **overrides) -> MemberCreate:
    data = {
        "name": name,
        "age": Decimal("30"),
        "gender": "male",
        "diet_goal": "normal",
        "constitution": ["balanced"],
        "health_conditions": ["none"],
        "allergens": [],
        "dietary_restrictions": [],
    }
    data.update(overrides)
    return MemberCreate(**data)


class TestCreateMember:
    def test_create_and_list(self, db):
        svc = FamilyService(db)
        member = svc.create_member(_payload())
        assert member.id > 0
        members = svc.list_members()
        assert len(members) == 1
        assert members[0].name == "小明"

    def test_create_baby_decimal_age(self, db):
        svc = FamilyService(db)
        member = svc.create_member(_payload(name="宝宝", age=Decimal("0.67"), diet_goal="baby"))
        assert member.age == Decimal("0.67")

    def test_8_member_limit(self, db):
        svc = FamilyService(db)
        for i in range(1, 9):
            svc.create_member(_payload(name=f"成员{i}"))
        with pytest.raises(MemberLimitExceeded):
            svc.create_member(_payload(name="第九人"))

    def test_active_count(self, db):
        svc = FamilyService(db)
        svc.create_member(_payload())
        assert svc.active_member_count() == 1


class TestUpdateMember:
    def test_partial_update(self, db):
        svc = FamilyService(db)
        member = svc.create_member(_payload())
        updated = svc.update_member(member.id, MemberUpdate(name="小红"))
        assert updated.name == "小红"
        assert updated.age == Decimal("30")

    def test_update_not_found(self, db):
        svc = FamilyService(db)
        with pytest.raises(MemberNotFound):
            svc.update_member(999, MemberUpdate(name="x"))


class TestDeleteMember:
    def test_soft_delete(self, db):
        svc = FamilyService(db)
        member = svc.create_member(_payload())
        deleted = svc.delete_member(member.id)
        assert deleted.is_deleted == 1
        # 删除后不再出现在活跃列表
        assert len(svc.list_members()) == 0
        # get 抛异常
        with pytest.raises(MemberNotFound):
            svc.get_member(member.id)

    def test_get_not_found(self, db):
        svc = FamilyService(db)
        with pytest.raises(MemberNotFound):
            svc.get_member(999)
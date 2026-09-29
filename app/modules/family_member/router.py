"""家庭档案路由：家庭名称级档案的读取与更新（DEF-01 持久化修复）。

一期单家庭模式（id=1 常驻，自动创建）：
- GET /api/family  读取家庭档案（不存在则自动创建默认家庭后返回）
- PUT /api/family  更新家庭名称（写入即落库，前端刷新/应用重启后仍可读回）

成员档案 CRUD 仍在 /api/members（8 人上限、逻辑删除在 service 层强制）。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.deps import get_db
from app.modules.family_member.schemas import FamilyOut, FamilyUpdate
from app.modules.family_member.service import FamilyService

router = APIRouter(prefix="/api/family", tags=["家庭档案"])


@router.get("", response_model=FamilyOut, summary="家庭档案（自动创建默认家庭）")
def get_family(db: Session = Depends(get_db)) -> FamilyOut:
    family = FamilyService(db).get_family()
    return FamilyOut.model_validate(family)


@router.put("", response_model=FamilyOut, summary="更新家庭名称（落库持久化）")
def update_family(payload: FamilyUpdate, db: Session = Depends(get_db)) -> FamilyOut:
    family = FamilyService(db).update_family_name(payload.name)
    return FamilyOut.model_validate(family)


"""家庭成员档案路由：CRUD + 8 人上限 + 逻辑删除。

对齐硬性业务规则第 3 条（业务约束由 service 层执行，本层仅透传）。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.deps import get_db
from app.modules.family_member.schemas import (
    MemberCreate,
    MemberListOut,
    MemberOut,
    MemberUpdate,
)
from app.modules.family_member.service import FamilyService

member_router = APIRouter(prefix="/api/members", tags=["成员档案"])


@member_router.get("", response_model=MemberListOut, summary="成员列表（不含已删除）")
def list_members(db: Session = Depends(get_db)) -> MemberListOut:
    svc = FamilyService(db)
    members = svc.list_members()
    return MemberListOut(total=len(members), items=[MemberOut.model_validate(m) for m in members])


@member_router.post("", response_model=MemberOut, status_code=201, summary="新增成员")
def create_member(payload: MemberCreate, db: Session = Depends(get_db)) -> MemberOut:
    member = FamilyService(db).create_member(payload)
    return MemberOut.model_validate(member)


@member_router.get("/{member_id}", response_model=MemberOut, summary="成员详情")
def get_member(member_id: int, db: Session = Depends(get_db)) -> MemberOut:
    member = FamilyService(db).get_member(member_id)
    return MemberOut.model_validate(member)


@member_router.put("/{member_id}", response_model=MemberOut, summary="更新成员")
def update_member(
    member_id: int, payload: MemberUpdate, db: Session = Depends(get_db)
) -> MemberOut:
    member = FamilyService(db).update_member(member_id, payload)
    return MemberOut.model_validate(member)


@member_router.delete("/{member_id}", response_model=MemberOut, summary="删除成员（逻辑删除）")
def delete_member(member_id: int, db: Session = Depends(get_db)) -> MemberOut:
    member = FamilyService(db).delete_member(member_id)
    return MemberOut.model_validate(member)

# 路由装配契约：main.py 遍历 include 本列表
routers: list[APIRouter] = [router, member_router]

"""家庭成员档案路由：CRUD + 8 人上限 + 逻辑删除。

对齐硬性业务规则第 3 条（业务约束由 service 层执行，本层仅透传）。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.repository.db_session import get_db
from src.schemas.member_schema import (
    MemberCreate,
    MemberListOut,
    MemberOut,
    MemberUpdate,
)
from src.services.family_service import FamilyService

router = APIRouter(prefix="/api/members", tags=["成员档案"])


@router.get("", response_model=MemberListOut, summary="成员列表（不含已删除）")
def list_members(db: Session = Depends(get_db)) -> MemberListOut:
    svc = FamilyService(db)
    members = svc.list_members()
    return MemberListOut(total=len(members), items=[MemberOut.model_validate(m) for m in members])


@router.post("", response_model=MemberOut, status_code=201, summary="新增成员")
def create_member(payload: MemberCreate, db: Session = Depends(get_db)) -> MemberOut:
    member = FamilyService(db).create_member(payload)
    return MemberOut.model_validate(member)


@router.get("/{member_id}", response_model=MemberOut, summary="成员详情")
def get_member(member_id: int, db: Session = Depends(get_db)) -> MemberOut:
    member = FamilyService(db).get_member(member_id)
    return MemberOut.model_validate(member)


@router.put("/{member_id}", response_model=MemberOut, summary="更新成员")
def update_member(
    member_id: int, payload: MemberUpdate, db: Session = Depends(get_db)
) -> MemberOut:
    member = FamilyService(db).update_member(member_id, payload)
    return MemberOut.model_validate(member)


@router.delete("/{member_id}", response_model=MemberOut, summary="删除成员（逻辑删除）")
def delete_member(member_id: int, db: Session = Depends(get_db)) -> MemberOut:
    member = FamilyService(db).delete_member(member_id)
    return MemberOut.model_validate(member)
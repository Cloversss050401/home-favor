"""家庭档案路由：家庭名称级档案的读取与更新（DEF-01 持久化修复）。

一期单家庭模式（id=1 常驻，自动创建）：
- GET /api/family  读取家庭档案（不存在则自动创建默认家庭后返回）
- PUT /api/family  更新家庭名称（写入即落库，前端刷新/应用重启后仍可读回）

成员档案 CRUD 仍在 /api/members（8 人上限、逻辑删除在 service 层强制）。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.repository.db_session import get_db
from src.schemas.family_schema import FamilyOut, FamilyUpdate
from src.services.family_service import FamilyService

router = APIRouter(prefix="/api/family", tags=["家庭档案"])


@router.get("", response_model=FamilyOut, summary="家庭档案（自动创建默认家庭）")
def get_family(db: Session = Depends(get_db)) -> FamilyOut:
    family = FamilyService(db).get_family()
    return FamilyOut.model_validate(family)


@router.put("", response_model=FamilyOut, summary="更新家庭名称（落库持久化）")
def update_family(payload: FamilyUpdate, db: Session = Depends(get_db)) -> FamilyOut:
    family = FamilyService(db).update_family_name(payload.name)
    return FamilyOut.model_validate(family)

"""个人中心路由：获取资料、更新资料、上传头像、修改密码。

一期单用户模拟，无登录无鉴权，接口直接可访问（二期再接入 token 校验）。
接口契约对齐设计文档：
- GET  /api/profile/info            读取个人资料（不存在自动初始化默认账号）
- PUT  /api/profile/info            更新签名、手机号
- POST /api/profile/avatar          上传头像，返回 /resources/upload/avatar/{filename}
- POST /api/profile/change-pwd      修改密码（bcrypt 校验原密码）
"""

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.common.deps import get_db
from app.modules.personal_center.schemas import (
    PasswordChangeReq,
    ProfileResp,
    ProfileUpdateReq,
)
from app.modules.personal_center.service import ProfileService

router = APIRouter(prefix="/api/profile", tags=["个人中心"])


@router.get(
    "/info", response_model=ProfileResp, summary="获取个人资料（自动初始化默认账号）"
)
def get_profile(db: Session = Depends(get_db)) -> ProfileResp:
    profile = ProfileService(db).get_my_profile()
    return ProfileResp.model_validate(profile)


@router.put("/info", response_model=ProfileResp, summary="更新签名、手机号")
def update_profile(
    payload: ProfileUpdateReq, db: Session = Depends(get_db)
) -> ProfileResp:
    profile = ProfileService(db).update_basic_info(
        signature=payload.signature, phone=payload.phone
    )
    return ProfileResp.model_validate(profile)


@router.post("/avatar", summary="上传头像")
def upload_avatar(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    avatar_url = ProfileService(db).upload_avatar(file)
    return {"avatar_url": avatar_url}


@router.post("/change-pwd", summary="修改密码")
def change_password(payload: PasswordChangeReq, db: Session = Depends(get_db)) -> dict:
    ProfileService(db).change_password(payload.old_password, payload.new_password)
    return {"msg": "密码修改成功"}


# 路由装配契约：main.py 遍历 include 本列表
routers: list[APIRouter] = [router]

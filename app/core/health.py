"""健康检查路由。"""
from fastapi import APIRouter

router = APIRouter(tags=["健康检查"])


@router.get("/health", summary="存活探针")
def health() -> dict:
    return {"status": "ok"}

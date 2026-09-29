"""FastAPI 应用装配入口。
- 注册全局异常处理器（src/exceptions/global_exception_handler.py）
- 注册全部 controllers 路由
- 挂载前端静态文件目录（frontend/）
- CORS 允许前端本地联调
- 启动时尝试建表（开发期便利；生产建议迁移工具）
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.config.settings import settings
from src.controllers import (
    family_controller,
    feedback_controller,
    health_controller,
    ingredient_controller,
    member_controller,
    purchase_controller,
    recipe_controller,
    report_controller,
)
from src.exceptions.global_exception_handler import register_exception_handler

app = FastAPI(
    title="家庭 AI 食谱推荐系统",
    description="家庭成员营养档案 + 食材录入 + AI 食谱生成 + 智能采购 + 反馈周报",
    version="0.1.0",
)
# CORS：一期前端本地联调；前端由后端同源托管，CORS 仅用于外部联调
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 全局异常处理器
register_exception_handler(app)
# 路由注册
app.include_router(health_controller.router)
app.include_router(family_controller.router)
app.include_router(member_controller.router)
app.include_router(ingredient_controller.router)
app.include_router(recipe_controller.router)
app.include_router(purchase_controller.router)
app.include_router(feedback_controller.router)
app.include_router(report_controller.router)
# 前端静态文件（frontend/）：html=True 时访问 / 自动返回 index.html
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

@app.on_event("startup")
def on_startup() -> None:
    """开发环境自动建表；失败（如 MySQL 未就绪）仅告警不阻断启动。"""
    try:
        from src.repository.db_session import init_db
        init_db()
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] 建表失败（请检查 MySQL）：{exc}")

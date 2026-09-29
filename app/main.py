"""FastAPI 应用装配入口。
- 注册全局异常处理器（app/core/exceptions.py）
- 注册 modules 各业务模块路由（按业务功能分包）
- 挂载前端静态文件目录（frontend/）
- CORS 允许前端本地联调
- 启动时尝试建表（开发期便利；生产建议迁移工具）
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.exceptions import register_exception_handler
from app.core.health import router as health_router
from app.modules.family_member.router import routers as family_member_routers
from app.modules.ingredient.router import routers as ingredient_routers
from app.modules.nutrition.router import routers as nutrition_routers
from app.modules.personal_center.router import routers as personal_center_routers
from app.modules.recipe.router import routers as recipe_routers
from app.modules.shopping_list.router import routers as shopping_list_routers

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
# 路由注册（按业务功能分包）
app.include_router(health_router)
for _r in (
    family_member_routers
    + ingredient_routers
    + recipe_routers
    + nutrition_routers
    + shopping_list_routers
    + personal_center_routers
):
    app.include_router(_r)
# 导出的 Excel 资源（采购清单 / 周报）：前端通过 /exports/{file_name} 下载
# 注意：必须注册在 "/" catch-all 挂载之前，否则被前端静态目录截获
EXPORTS_DIR = Path(__file__).resolve().parents[1] / "resources" / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/exports", StaticFiles(directory=EXPORTS_DIR), name="exports")
# 用户上传资源（个人中心头像等）：前端通过 /resources/upload/{...} 访问
# 注意：同样必须注册在 "/" catch-all 挂载之前
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "resources" / "upload"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/resources/upload", StaticFiles(directory=UPLOAD_DIR), name="uploads")
# 前端静态文件：优先托管构建产物 frontend/dist（生产模式）；
# 未构建时回退 frontend/ 根目录（可访问原始单文件原型 family-ai-recipe.html）
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"
_serve_dir = DIST_DIR if DIST_DIR.is_dir() else FRONTEND_DIR
app.mount("/", StaticFiles(directory=str(_serve_dir), html=True), name="frontend")


@app.on_event("startup")
def on_startup() -> None:
    """开发环境自动建表；失败（如 MySQL 未就绪）仅告警不阻断启动。"""
    try:
        from app.core.db import init_db

        init_db()
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] 建表失败（请检查 MySQL）：{exc}")

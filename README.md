# 家庭 AI 食谱推荐系统（后端）

桌面网页端家庭饮食健康管理工具的后端服务。录入家庭成员档案、家中现有食材，AI 生成全家共享食谱与分餐方案，输出营养评估与智能采购清单，收集做菜反馈并聚合生成周度营养分析报告。

## 技术栈

- Python 3.10+ / FastAPI
- SQLAlchemy 2.0 + MySQL 8.0
- Redis（缓存菜谱基础库、食物成分表）
- 第三方 AI 能力：大模型（食谱生成）、多模态 OCR（拍照识别食材）、ASR（武汉方言语音）

## 环境准备

本项目使用 [uv](https://docs.astral.sh/uv/) 管理依赖与解释器，需先安装 uv：

```bash
# Windows PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

`uv sync` 会按 `.python-version`（默认 3.11）下载解释器，按 `pyproject.toml` 创建 `.venv` 并安装全部依赖：

```bash
uv sync
```

要求 Python 3.10+。

## 配置说明

复制 `.env.example` 为 `.env`，填写数据库连接与第三方 API 密钥：

```bash
cp .env.example .env
```

**Mock 密钥模式**：未配置 LLM/MULTIMODAL/ASR 密钥时，系统自动使用内置 Mock 实现（食谱生成返回固定结果、拍照/语音返回内置文本），本地无密钥即可完成全链路联调；配置密钥后自动切换真实调用，接口契约不变。

## 数据库初始化

1. 创建 MySQL 库：`CREATE DATABASE ai_recipe DEFAULT CHARACTER SET utf8mb4;`
2. 建表：首次启动自动 `create_all`（开发期；生产建议迁移工具）。
3. 导入字典种子数据（幂等）：

```bash
uv run python resources/init_data/import_seed.py
```

## 一键启动（Windows）

双击 `start.bat`，自动完成：依赖检查 → 生成 `.env`（未检测到 MySQL 时默认改用 SQLite，开箱即用）→ 数据库与端口预检 → 幂等导入字典种子数据 → 启动服务并自动打开 API 文档页。

命令行等效入口：`uv run python scripts/dev_launcher.py`。

> 提示：如需使用 MySQL，先创建库 `CREATE DATABASE ai_recipe DEFAULT CHARACTER SET utf8mb4;`，并修改 `.env` 中的 `DB_URL` 后再启动。

## 本地启动

```bash
uv run python scripts/dev_launcher.py
```

API 文档访问地址：`http://127.0.0.1:8000/docs`
前端入口页：`http://127.0.0.1:8000/`（后端静态托管优先指向 `frontend/dist` 构建产物，未构建时回退 `frontend/` 根页面）。前端为 Vue3 + Vite + Element Plus 工程，开发模式见 `frontend/README.md`（`npm run dev` 起 5173 并代理 `/api`）。

## 测试

```bash
uv run pytest tests/ -v
```

测试覆盖 utils 单元测试、services 集成测试（sqlite 内存库）、controllers HTTP 链路测试、架构分层合规检查。
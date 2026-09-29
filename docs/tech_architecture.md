# 家庭 AI 食谱推荐系统 · 后端架构说明

> 架构基线：按**业务功能分包**（`app/modules/*`），每个业务模块内聚「路由 / 业务 / 数据访问 / ORM / DTO」五件套；
> 全局通用能力下沉 `app/core` 与 `app/common`。详细业务口径见《家庭饮食健康项目｜技术文档（整合版・按业务功能分包）.md》。

## 1. 分层架构（核心约束，模块内单向依赖）

每个业务模块 `app/modules/<module>/` 内严格单向依赖，**下层不得反向依赖上层**：

```
router.py（路由层：参数校验、HTTP 编排）
    ↓
service.py（业务层：领域逻辑、营养计算、第三方编排）
    ↓
repository.py（数据访问层：ORM 查询封装）
    ↓
models.py（ORM 实体：表结构定义）
```

- 横向能力：`schemas.py`（模块内 DTO）、`app/common/`（`utils.py` 通用工具、`deps.py` 公共依赖注入）、`app/core/`（`config.py` 配置、`constants.py` 业务常量、`exceptions.py` 异常 + 全局处理器、`db.py` 引擎/会话/建表、`logging.py` 日志）。
- 第三方能力封装：每个模块所需的 clients 放在模块内 `clients.py`（recipe→LLM；ai_assistant→OCR/ASR），**仅被 service 依赖**。
- 跨模块引用：service 层可依赖其他模块的 repository/service/clients；router 可依赖任意模块的 service 与 `app.common.deps`；不允许向下越层（router→repository/models/clients）。
- 校验手段：架构合规检查 `tests/test_architecture.py` 按五件套分层禁止反向 import，并兜底禁止残留旧 `src.` 引用。

## 2. 目录结构

```
D:\code\Home_Flavor
├── app/                            # 后端源码根（按业务功能分包）
│   ├── main.py                     # FastAPI 装配：注册异常处理器/模块路由/静态托管/启动建表
│   ├── core/                       # 全局通用能力
│   │   ├── config.py               # Settings：.env 环境变量（含 sqlite 绝对路径解析）
│   │   ├── constants.py            # 全项目业务常量（核心营养素、DRIs 口径等）
│   │   ├── exceptions.py           # 自定义业务异常 + 全局异常处理器（合并原两文件）
│   │   ├── logging.py              # 日志全局配置
│   │   ├── db.py                   # engine / SessionLocal / Base / init_db / 轻量迁移
│   │   └── health.py               # 健康检查路由（/health）
│   ├── common/                     # 公共依赖与工具
│   │   ├── deps.py                 # get_db：FastAPI 请求级会话依赖注入
│   │   └── utils.py                # 通用工具：重量解析 / 同义词 / Excel 导出 / 日期
│   └── modules/                    # 六大业务模块（每模块五件套 + 可选 clients）
│       ├── family_member/          # 家庭档案 + 成员档案（router/service/repository/models/schemas）
│       ├── ingredient/             # 食材录入（文字/拍照/语音三入口 + 确认入库）
│       ├── recipe/                 # AI 食谱生成 + 历史记录（含 clients.py：LLM）
│       ├── nutrition/              # 营养引擎 + 做菜反馈 + 周报（三 service 合并）
│       ├── shopping_list/          # 采购触发检查 + 清单导出（含采购 DTO）
│       └── ai_assistant/           # OCR/ASR 能力封装（clients.py 合并，一期无独立路由）
├── resources/
│   ├── dict/synonyms.json          # 食材同义词词典（可扩展）
│   ├── init_data/                  # 字典表种子数据 + 导入脚本
│   └── exports/                    # 采购清单导出产物目录
├── configs/                        # 环境/部署配置（文档对齐，占位）
├── tests/                          # pytest：utils 单测 / services 集成 / controllers 链路 / 架构合规
├── docs/                           # 架构/数据库/API/业务规则文档
├── requirements.txt / pyproject.toml / .env.example
└── README.md / CHANGELOG.md / LICENSE / .gitignore
```

## 3. 核心模块说明

### 3.1 模块路由（全部 `/api` 前缀，除健康检查）

| 模块 | 前缀 | 说明 |
|---|---|---|
| family_member | `/api/family`、`/api/members` | 家庭档案 + 成员档案 CRUD（含逻辑删除、8 人上限） |
| ingredient | `/api/ingredients` | 食材三入口录入（文字/拍照/语音）+ 确认入库 |
| recipe | `/api/recipes` | AI 食谱生成 + 历史记录 |
| shopping_list | `/api/purchase` | 采购触发检查 + 清单导出 |
| nutrition | `/api/feedback`、`/api/reports` | 做菜反馈录入 + 周度营养报告 |
| core/health | `/health` | 健康检查 |

### 3.2 service（各模块 service.py）

- `family_member/FamilyService`：家庭/成员档案，成员数量上限校验（`MEMBER_FAMILY_LIMIT`），逻辑删除。
- `ingredient/IngredientService`：三种识别入口统一走 `parse_weight` + 同义词规范化，确认入库/逻辑删除，语音按标点切分多食材。
- `recipe/RecipeService`：组装成员档案 + 存量食材 prompt → 调 LLM（本地 `clients.py`）→ `nutrition.NutritionService` 本地二次校验 → 落库快照。
- `nutrition/NutritionService`：营养核心引擎（RNI 查表、分量换算、缺口占比）。`FeedbackService`：反馈落库（use_ai_amount、成员食量明细）。`ReportService`：周报聚合（有效天数、营养素日均、达标率）。
- `shopping_list/PurchaseService`：缺口/主菜数触发判定，3 天全家需求采购量计算，Excel/CSV 导出（复用 ingredient/recipe/family_member repository）。

### 3.3 clients（第三方 AI：recipe/clients.py、ai_assistant/clients.py）

工厂模式：`settings.llm_ready / multimodal_ready / asr_ready` 任一未就绪时使用内置 Mock 实现，保证本地无密钥可全链路联调；配置 `.env` 密钥后自动切换真实大模型调用，业务代码零改动。

### 3.4 db（app/core/db.py）

- `engine` / `SessionLocal` 由 `Settings.DB_URL` 生成（默认 MySQL+pymysql，测试可用 `sqlite://` 覆盖）。
- `Base` 为 ORM 基类（原 `src/models/__init__.py` 的注册中心职责迁移至此）；`ensure_models_imported()` 聚合导入全部模块 models，供 `create_all` / `drop_all` 建全表。
- `get_db` 为 FastAPI 依赖（`app/common/deps.py`），请求级 Session。
- `init_db()` 开发期 `create_all` 建表 + 幂等轻量迁移（family.is_deleted / family_member.role/traits/avoid 补列），启动时执行，失败仅告警不阻断。

## 4. 外部依赖与密钥

| 依赖 | 用途 | 未配置时行为 |
|---|---|---|
| MySQL 8.0 | 主库 | 启动告警，接口 500 |
| Redis | 缓存食谱基础库/食物成分表（预留） | 未强依赖，可后置 |
| LLM（API_KEY/BASE_URL/MODEL） | AI 生成食谱 | Mock 返回固定结果 |
| 多模态 OCR | 拍照识别食材 | Mock 固定返回 |
| ASR | 武汉方言语音转文字 | Mock 固定返回 |

## 5. 启动与验证

```bash
pip install -r requirements.txt
python resources/init_data/import_seed.py   # 首次导入字典表种子数据
python scripts/dev_launcher.py              # 一键启动（等效 uvicorn app.main:app）
pytest tests/ -v                             # 单元/集成/架构合规测试
```
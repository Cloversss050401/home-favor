# 家庭 AI 食谱推荐系统｜标准 Python‑FastAPI 项目工程结构.md

> 
> 遵循 Python 工程最佳实践：区分项目入口、src 核心源码包、测试、文档、配置、资源；兼容前面定义的分层架构，同时补充测试、文档、git 忽略、许可证、变更日志。
> 采用 `src/` 源码包布局（行业标准），不是把所有文件直接放在根目录。

```
family_ai_recipe/                     # 项目根目录（git仓库根）
├── README.md                         # 项目总说明、快速启动、接口访问地址
├── CHANGELOG.md                      # 更新日志：版本、变更内容、业务/技术改动
├── LICENSE                           # 许可证文件
├── .gitignore                        # git忽略文件：.env、__pycache__、日志、venv、*.pyc、输出excel等
├── requirements.txt                  # 项目依赖
├── startup.py                        # 项目启动入口（命令行启动入口）
├── src/                              # ✨核心代码包，所有业务源码放这里
│   ├── __init__.py
│   ├── main.py                       # FastAPI App实例初始化，注册路由、全局异常处理器
│   ├── config/                       # 配置模块
│   │   ├── __init__.py
│   │   ├── settings.py               # 读取.env、数据库、第三方API密钥、服务配置
│   │   └── constants.py              # 业务常量、枚举、阈值（核心营养素、采购天数、成员上限）
│   ├── controllers/                  # Controller层：路由，只处理请求响应，不写复杂业务
│   │   ├── __init__.py
│   │   ├── family_controller.py
│   │   ├── ingredient_controller.py
│   │   ├── recipe_controller.py
│   │   ├── feedback_controller.py
│   │   └── report_controller.py
│   ├── schemas/                      # Pydantic DTO：请求模型、响应输出模型
│   │   ├── __init__.py
│   │   ├── family_schema.py
│   │   ├── member_schema.py
│   │   ├── ingredient_schema.py
│   │   ├── recipe_schema.py
│   │   ├── feedback_schema.py
│   │   └── report_schema.py
│   ├── models/                       # ORM数据库模型(SQLAlchemy)，映射MySQL表
│   │   ├── __init__.py
│   │   ├── family_model.py
│   │   ├── member_model.py
│   │   ├── ingredient_model.py
│   │   ├── recipe_record_model.py
│   │   ├── feedback_model.py
│   │   ├── report_model.py
│   │   ├── food_nutrition_model.py
│   │   └── dris_model.py
│   ├── services/                     # Service层，全部业务逻辑实现
│   │   ├── __init__.py
│   │   ├── family_service.py
│   │   ├── ingredient_service.py
│   │   ├── recipe_service.py
│   │   ├── nutrition_service.py      # 核心营养计算、缺口、周报折算
│   │   ├── purchase_service.py       # 采购清单生成、食材合并
│   │   ├── feedback_service.py
│   │   └── report_service.py
│   ├── repository/                   # Repository仓库层，纯数据库CRUD，无业务逻辑
│   │   ├── __init__.py
│   │   ├── db_session.py             # 数据库会话、连接管理
│   │   ├── family_repo.py
│   │   ├── member_repo.py
│   │   ├── ingredient_repo.py
│   │   ├── recipe_record_repo.py
│   │   ├── feedback_repo.py
│   │   ├── report_repo.py
│   │   ├── food_nutrition_repo.py
│   │   └── dris_repo.py
│   ├── clients/                      # 第三方API客户端封装（大模型、多模态OCR、ASR方言语音）
│   │   ├── __init__.py
│   │   ├── base_client.py
│   │   ├── llm_client.py
│   │   ├── multimodal_client.py
│   │   └── asr_client.py
│   ├── utils/                        # 通用工具函数
│   │   ├── __init__.py
│   │   ├── weight_parser.py          # "番茄 500g"解析名称重量
│   │   ├── synonym_util.py           # 食材同义词合并
│   │   ├── excel_export.py           # 采购清单导出Excel
│   │   └── date_util.py              # 周统计日期工具
│   └── exceptions/                   # 自定义业务异常、全局异常处理
│       ├── __init__.py
│       ├── business_exception.py
│       └── global_exception_handler.py
├── resources/                         # 资源文件
│   ├── dict/                          # 字典数据：食材同义词字典、初始化数据json
│   └── init_data/                     # 初始化导入：食物成分表、DRIs的csv/json数据文件
├── tests/                             # 单元测试 & 集成测试
│   ├── __init__.py
│   ├── conftest.py                    # pytest全局夹具：测试数据库session、mock第三方client
│   ├── test_service/                  # 业务逻辑单元测试
│   │   ├── test_nutrition_service.py
│   │   ├── test_purchase_service.py
│   │   └── test_family_service.py
│   ├── test_controller/               # 接口集成测试
│   └── test_utils/                    # 工具函数测试
├── docs/                              # 项目文档目录
│   ├── api.md                         # 接口说明
│   ├── business_rules.md              # 全部业务规则（食材粒度、缺口口径、档案规则、采购规则）
│   ├── tech_architecture.md           # 技术架构、分层说明
│   └── database_design.md             # 数据库表设计文档
├── .env                               # 环境变量（本地开发，禁止提交git）
└── .env.example                       # 环境变量模板，提交到git，给开发参考
```

## 1. 入口说明：`startup.py` + `src/main.py`

### src/main.py

> 
> 只负责构建 FastAPI 应用实例，**不写启动逻辑**

```
# src/main.py
from fastapi import FastAPI
from src.exceptions.global_exception_handler import register_exception_handler
from src.controllers import family_controller, ingredient_controller

app = FastAPI(title="家庭AI食谱推荐系统", version="v1.0")

# 注册全局异常
register_exception_handler(app)

# 注册路由
app.include_router(family_controller.router)
app.include_router(ingredient_controller.router)
# ...其他router
```

### startup.py（项目根目录，命令行启动入口）

> 
> 读取环境变量，加载配置，启动 uvicorn 服务；统一入口，方便部署脚本调用。

```
# startup.py
import uvicorn
from src.config.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG
    )
```

> 
> 本地启动命令：`python startup.py`

## 2. 关键目录职责重申（对齐标准 Python 工程规范）

表格

| 目录 | 作用 |
| --- | --- |
| `src/` | 核心源码包，所有业务代码，避免根目录散落 py 文件 |
| `src/controllers/` | 接收 http 请求，路由层，对应 MVC 的 Controller；**禁止写复杂业务逻辑** |
| `src/models/` | ORM 实体模型，数据库映射 |
| `src/services/` | 业务实现层，所有业务规则、计算逻辑放这里 |
| `src/repository/` | 数据访问层，收拢数据库 CRUD 操作 |
| `src/clients/` | 外部第三方 API 封装，隔离大模型 / OCR/ASR |
| `src/config/` | 配置、常量，密钥从.env 读取，禁止硬编码密钥 |
| `src/utils/` | 通用工具函数，不包含业务逻辑 |
| `src/exceptions/` | 自定义业务异常、全局异常捕获 |
| `resources/` | 静态资源、初始化字典数据（食材同义词、DRIs / 食物成分表原始导入文件） |
| `tests/` | pytest 测试集；`conftest.py`存放测试夹具；mock 外部接口避免测试调用真实大模型 API |
| `docs/` | 存放全部项目设计文档（业务规则、数据库、架构、接口文档） |

## 3. .gitignore 关键内容示例

```
# python缓存
__pycache__/
*.py[cod]
*$py.class

# 虚拟环境
venv/
env/

# 环境变量，密钥不提交
.env
*.local

# 导出生成文件
*.xlsx
*.csv

# IDE
.idea/
.vscode/

# 日志
logs/
*.log
```

`.env.example` 提交版本库，只保留 key 名，值留空，开发复制为`.env`填写自己密钥。

```
# .env.example
DB_URL=mysql+pymysql://user:password@127.0.0.1:3306/ai_recipe
LLM_API_KEY=
ASR_API_KEY=
DEBUG=True
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

## 4. README.md 建议包含章节

1. 项目简介
2. 技术栈
3. 环境准备、依赖安装
4. 配置说明（复制.env.example 为.env）
5. 本地启动方式 `python startup.py`
6. API 文档访问地址：`http://127.0.0.1:8000/docs`
7. 数据库初始化说明
8. 项目目录结构简述
9. 测试执行命令：`pytest tests/ -v`

## 5. CHANGELOG.md 模板示例

```
# CHANGELOG

## v1.0.0 (2026‑09‑25)
- 完成基础分层架构搭建
- 数据库表设计完成
- 业务规则定义完成：食材录入粒度、营养缺口口径、采购规则、档案规则
```

## 6. 开发约束补充

1. 业务逻辑必须写在`service`，controller 只做参数接收与返回；
2. 所有数据库操作通过`repository`，禁止业务层直接写 SQL；
3. 第三方接口调用统一走`clients`，方便单元测试做 mock；
4. 测试用例放在`tests`目录，不混入源码；
5. 所有业务常量统一放在`config/constants.py`，不要散落在业务代码中。
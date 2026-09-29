# 家庭 AI 食谱推荐系统（前端）

Vue3 + Vite + Element Plus 单页应用，与后端 FastAPI（`src/`）联调，还原原型 `frontend/family-ai-recipe.html` 的全部核心功能并接入真实接口。

## 技术栈

- Vue 3 + Composition API
- Vite（开发服务器 / 构建）
- Element Plus（表单、表格、弹窗、消息组件）
- Axios（接口请求，baseURL 走 Vite 代理 `/api`）

## 目录结构

```text
frontend/
├── index.html             # 入口 HTML
├── vite.config.js         # dev 代理 /api → 后端 8000
├── src/
│   ├── main.js            # 应用入口（注册 Element Plus、全局样式）
│   ├── App.vue            # 布局：侧边 5 项导航 + 主内容区
│   ├── api/index.js       # 全部后端接口封装（单一契约层）
│   ├── styles/main.css    # 毛玻璃卡片、柔和蓝绿配色（主色 #2B7BAF / #48B89C）
│   └── views/
│       ├── Members.vue    # 家庭成员档案：新增/编辑表单、列表、删除
│       ├── Pantry.vue     # 家中食材：文字/批量录入、存在标记、存量编辑
│       ├── Recipe.vue     # AI 食谱方案：生成、分餐与营养评估、采购清单、导出 Excel
│       ├── Feedback.vue   # 做菜反馈：勾选菜品、成员分量、一键全选（复用 AI 分配）
│       └── Report.vue     # 每周营养报告：生成周报、明细/问题建议、导出 Excel
├── dist/                  # 构建产物（后端 / 静态托管优先指向此目录）
└── family-ai-recipe.html  # 原始单文件原型（唯一契约正本，供比对参考）
```

## 开发启动

```bash
cd frontend
npm install
npm run dev        # http://127.0.0.1:5173，/api 代理到 http://127.0.0.1:8000
```

需先启动后端（见项目根 README：`uv run python scripts/dev_launcher.py` 或双击 `start.bat`）。

## 构建

```bash
npm run build      # 产物输出到 frontend/dist/
```

构建后访问 `http://127.0.0.1:8000/`（后端静态托管优先指向 `frontend/dist`，未构建时回退 `frontend/` 根目录页面），即由后端单端口服务前端 + API。

## 接口契约（前端 api/index.js 对接概要）

| 功能 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 成员列表 / 新增 / 编辑 / 删除 | GET/POST/PUT/DELETE | `/api/members`、`/api/members/{id}` | 档案字段：name/age/gender/role/constitution/health_conditions/allergens/dietary_restrictions/diet_goal |
| 食材列表 | GET | `/api/ingredients` | available_weight 为空表示仅标记存在 |
| 食材录入 | POST | `/api/ingredients/text`、`/text/batch`、`/image`、`/speech` | 结果需人工确认后入库（`/confirm`） |
| 生成食谱 | POST | `/api/recipes/generate` | 请求含成员快照、菜谱库；返回共享菜品 + 分餐 + 营养评估 |
| 食谱历史 | GET | `/api/recipes/records` | |
| 采购缺口检查 | POST | `/api/purchase/check` | 缺口语径：核心营养素缺口占比 > 30% 或主菜 < 2 道触发 |
| 采购清单导出 | GET | `/api/purchase/export?fmt=xlsx` | 生成 `resources/exports/purchase_list_*.xlsx`，前端经 `/exports/` 下载 |
| 提交反馈 | POST | `/api/feedback` | amount_g 手动优先级高于 is_ai_recommended 一键全选 |
| 反馈列表 | GET | `/api/feedback` | |
| 生成周报 | POST | `/api/reports/generate` | body 传 week_range；依赖反馈记录，空白日期不估算 |
| 周报导出 | GET | `/api/reports/export?fmt=xlsx` | 生成 `resources/exports/weekly_report_*.xlsx`（sheet1 周报明细 / sheet2 问题与建议） |

## Excel 导出

- 导出文件统一落在后端 `resources/exports/`，前端通过 `/exports/<文件名>` 下载。
- 采购清单：优先级 / 食材 / 补充营养素 / 建议采购量 / 优先补齐成员 / 缺口比例 / 备注。
- 周报明细：成员 / 营养素 / RNI / 有效天数 / 累计摄入 / 日均摄入 / 达标率 / 状态（缺口|达标|超标）/ 累计缺口；问题与建议 sheet 按成员给出本周问题与下周建议。

## 联调验证摘要（2026-09-26）

- 档案页：成员列表 2 条与后端一致（JJ狒/宝宝）。
- 食材页：番茄 500g（有存量）、鸡蛋（仅标记存在）、鸡胸肉 300g，与 `is_valid=1` + available_weight 数据一致。
- 食谱页：生成方案（最近方案 #3，共享菜品 2 道）→ 分餐与营养评估表 → 采购清单 11 项 → 触发“核心营养素缺口＞30%”警告 → 导出 Excel 成功。
- 反馈页：一键全选（复用 AI 分配分量）勾选成功，提交后 `/api/feedback` total=6。
- 周报页：生成周报（#2，2026-09-21~27，有效统计 1 天），明细含 JJ狒 9 营养素缺口判定与宝宝超标判定；导出 Excel 双 sheet 内容与页面一致。
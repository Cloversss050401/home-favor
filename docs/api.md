# 家庭 AI 食谱推荐系统 · API 文档

基础地址：`http://127.0.0.1:8000`；交互文档：`/docs`（Swagger UI）。首页 `GET /` 为前端档案管理页（frontend/，静态托管）。

## 0. 家庭档案 `/api/family`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/family` | 读取家庭档案（首次访问自动创建默认家庭，含 is_deleted 逻辑删除标记） |
| PUT | `/api/family` | 更新家庭名称（body: `{name}`，1-50 字符） |

家庭档案落库持久化：前端保存即写入后端数据库，刷新/重启服务后读回，档案不会丢失。

## 1. 成员档案 `/api/members`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/members` | 成员列表（排除逻辑删除） |
| POST | `/api/members` | 新建成员（body: name/age/gender/diet_goal/constitution/health_conditions/allergens/dietary_restrictions） |
| GET | `/api/members/{member_id}` | 成员详情 |
| PUT | `/api/members/{member_id}` | 更新成员 |
| DELETE | `/api/members/{member_id}` | 逻辑删除 |

业务约束：单家庭最多 8 人；年龄 0-120；过敏原/忌口入库。

## 2. 食材录入 `/api/ingredients`

三入口统一识别 → 结果确认 → 入库，支持逻辑删除失效：

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/ingredients/text` | 文字录入（body: `{name: "番茄 500g，鸡胸肉"}`，按标点切分多食材） |
| POST | `/api/ingredients/image` | 拍照识别（multipart: file；未配置多模态密钥时走 Mock） |
| POST | `/api/ingredients/speech` | 语音识别（multipart: file；未配置 ASR 密钥时走 Mock） |
| POST | `/api/ingredients/confirm` | 确认入库（body: family_id + items[]） |
| GET | `/api/ingredients` | 当前有效食材列表 |
| DELETE | `/api/ingredients/{ingredient_id}` | 失效该食材（逻辑删除） |

识别结果格式：`{name, available_weight, weight_unit}`；重量缺失时 `available_weight` 为 NULL。

## 3. AI 食谱生成 `/api/recipes`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/recipes/generate` | 生成食谱（body: `{family_id, dish_count}`，2≤dish_count≤10；未配置 LLM 密钥时走 Mock） |
| GET | `/api/recipes` | 生成历史列表 |
| GET | `/api/recipes/{record_id}` | 历史记录详情 |

生成结果三层结构：
- `shared_dishes`：全家共享菜品（name/category/is_main_dish/main_ingredients/…）
- `member_allocation`：每位成员分餐 + 营养缺口评估（rni/actual/gap_ratio/status）
- `purchase_list`：智能采购清单（priority/food_name/suggest_amount_g/…）

## 4. 智能采购 `/api/purchase`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/purchase/check` | 触发检查（params: family_id；返回 triggered + reason） |
| POST | `/api/purchase/export` | 导出采购清单（params: fmt=xlsx\|csv, family_id；产物写入 resources/exports/） |

触发条件：任意成员核心营养素缺口>30% 或 主菜数<2。采购满足全家 3 天需求；已录重量扣减存量、≤0 移除。

## 5. 做菜反馈 `/api/feedback`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/feedback` | 录反馈（body: family_id/recipe_record_id/eaten_date/use_ai_amount/items[]，items 含 member_id/dish_name/amount_g） |
| GET | `/api/feedback` | 反馈列表（可选 family_id 过滤） |

## 6. 周度营养报告 `/api/reports`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/reports/generate` | 生成周报（params: family_id, week_start 可选；返回达标率/缺口/建议） |
| GET | `/api/reports` | 历史周报列表 |

## 7. 健康检查 `/health`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 存活探针（返回 `{status: "ok"}`） |

## 8. Mock 密钥模式

未配置第三方密钥时（`LLM_API_KEY` / `MULTIMODAL_API_KEY` / `ASR_API_KEY` 为空）：
- 食谱生成：返回内置固定 Mock 结果（2 道菜，含番茄炒蛋等）；
- 拍照/语音：返回内置文本（“番茄 500g，鸡胸肉”）走相同入库链路。

配置 `.env` 密钥后自动切换真实调用，接口契约不变。
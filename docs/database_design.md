# 家庭 AI 食谱推荐系统 · 数据库设计

## 1. 总览

MySQL 8.0（utf8mb4），8 张表：2 张业务字典表 + 6 张业务表。

```
dris_standard（DRIs 推荐摄入量）
food_nutrition（中国食物成分表）
family（家庭）
├── family_member（成员档案）
├── household_ingredient（家中食材）
├── recipe_generation_record（AI 食谱生成快照）
│   └── user_feedback（做菜反馈，关联记录+成员）
└── weekly_nut_report（周度营养报告）
```

## 2. 表结构

### 2.1 dris_standard（膳食营养素参考摄入量字典）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| target_type | varchar(30) | 人群类别：adult_male/adult_female/slim/muscle/pregnant/baby_6_12m/elderly |
| nutrient_code | varchar(20) | protein/calcium/iron/zinc/vitamin_a/vitamin_c |
| nutrient_name | varchar(20) | 中文名 |
| rni_value | decimal(10,2) | 每日推荐值 | 
| unit | varchar(10) | g / mg |
| applicable_age | varchar(30) | 适用年龄段 |
| remark | varchar(200) | |
| created_at | datetime | |

唯一业务键：`(target_type, nutrient_code)`。种子数据见 `resources/init_data/dris_standard.json`。

### 2.2 food_nutrition（中国食物成分表字典）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| food_name | varchar(50) | 食材名（索引） |
| food_category | varchar(20) | 分类：蔬菜/蛋类/禽肉/畜肉/水产/奶类/豆制品/谷类/薯类/水果 |
| protein | decimal(8,2) | 蛋白质 g/100g |
| calcium / iron / zinc / vitamin_a / vitamin_c | decimal(8,2) | 钙/铁/锌/维A/维C mg/100g |
| energy | decimal(10,2) | 能量 kcal/100g |
| fat | decimal(8,2) | 脂肪 g/100g |
| carbohydrate | decimal(8,2) | 碳水化合物 g/100g |
| per_amount_g | decimal(8,2) | 该行对应的食物量（默认 100） |
| remark | varchar(200) | |
| created_at | datetime | |

种子数据见 `resources/init_data/food_nutrition.json`（内置为权威表示例数据，生产建议替换为《中国食物成分表》完整版）。

### 2.3 family（家庭）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| name | varchar(50) | 默认「我的家庭」 |
| created_at / updated_at | datetime | |

一期单家庭（id=1 常驻），为二期多家庭预留。

### 2.4 family_member（成员档案）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| family_id | int FK→family | 级联删除 |
| name | varchar(20) | 姓名 ≤20 字符 |
| age | decimal(5,2) | 0-120，允许婴儿小数（0.67=8月龄） |
| gender | varchar(10) | 枚举 |
| diet_goal | varchar(20) | 饮食目标单选 |
| constitution | JSON | 体质多选 |
| health_conditions | JSON | 慢病倾向多选 |
| allergens | JSON | 过敏原（枚举+自定义） |
| dietary_restrictions | JSON | 忌口文本数组 |
| is_deleted | int | 0 正常 / 1 逻辑删除（索引） |
| created_at / updated_at | datetime | |

约束：单家庭最多 8 位成员（service 层校验）。

### 2.5 household_ingredient（家中现有食材）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| family_id | int FK→family | 级联删除 |
| name | varchar(50) | 食材名称（索引，同义词已归并到规范名） |
| available_weight | decimal(10,2) NULL | 可用重量（选填） |
| weight_unit | varchar(10) | 默认 g |
| is_valid | int | 1 有效 / 0 失效（索引），逻辑删除 |
| created_at / updated_at | datetime | |

一期不做自动消耗扣减，食材由用户手动维护。

### 2.6 recipe_generation_record（AI 食谱生成记录）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| family_id | int FK→family | 级联删除 |
| input_snapshot | JSON | 输入快照：成员档案+食材列表 |
| shared_dishes | JSON | 一、全家共享菜品清单 |
| member_allocation | JSON | 二、个人分餐方案+双维度营养评估 |
| purchase_list | JSON | 三、采购清单（可能为空=未触发） |
| created_at | datetime | |

三层结果整体快照落库，供反馈折算、周报统计、历史追溯。

### 2.7 user_feedback（做菜反馈明细）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| family_id | int FK→family | 级联删除 |
| recipe_record_id | int FK→record NULL | SET NULL |
| member_id | int FK→member | 级联删除（索引） |
| dish_name | varchar(100) | 实际制作菜品 |
| amount_g | decimal(10,2) | 食用分量 g |
| eaten_date | date | 食用日期（索引） |
| is_ai_recommended | int | 1=一键全选复用AI分量 |
| created_at | datetime | |

### 2.8 weekly_nut_report（周度营养报告）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| family_id | int FK→family | 级联删除 |
| week_start | date | 周一 |
| week_end | date | 周日 |
| generate_type | int | 0 手动 / 1 自动 |
| report_data | JSON | 完整周报（达标率/累计缺口/超标项/下周建议） |
| created_at | datetime | |

## 3. 初始化流程

```bash
# 1. 建库（MySQL）
CREATE DATABASE ai_recipe DEFAULT CHARACTER SET utf8mb4;

# 2. 启动应用自动建表（开发期 create_all；生产建议迁移工具）

# 3. 导入字典种子数据（幂等，已存在则跳过）
python resources/init_data/import_seed.py
```

## 4. 设计约定

- 删除一律逻辑删除（is_deleted / is_valid 标记），禁止物理删除。
- JSON 列在 sqlite 下退化为通用 JSON 类型，便于本地测试；MySQL 下为原生 JSON。
- 外键均带 CASCADE/SET NULL，保证引用完整性。
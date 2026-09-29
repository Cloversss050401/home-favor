"""业务常量中心：全部业务阈值、枚举、配置统一放此处，禁止散落在业务代码中。"""

# ===== 家庭成员档案 =====
MEMBER_NAME_MAX_LEN: int = 20
MEMBER_FAMILY_LIMIT: int = 8  # 单家庭最多成员数
AGE_MIN: float = 0.0
AGE_MAX: float = 120.0

# 性别枚举
GENDER_MALE: str = "male"
GENDER_FEMALE: str = "female"
GENDER_OTHER: str = "other"
GENDER_ENUM = (GENDER_MALE, GENDER_FEMALE, GENDER_OTHER)

# 家庭角色（前端档案表单单选枚举；"" 表示不指定）
MEMBER_ROLE_ADULT: str = "adult"  # 成人
MEMBER_ROLE_ELDERS: str = "elders"  # 长辈（60岁以上）
MEMBER_ROLE_CHILD: str = "child"  # 儿童（3-12岁）
MEMBER_ROLE_TEEN: str = "teen"  # 青少年（13-17岁）
MEMBER_ROLE_BABY: str = "baby"  # 婴幼儿（0-3岁）
MEMBER_ROLE_PREGNANT: str = "pregnant"  # 孕妈妈
MEMBER_ROLE_ENUM = (
    "",
    MEMBER_ROLE_ADULT,
    MEMBER_ROLE_ELDERS,
    MEMBER_ROLE_CHILD,
    MEMBER_ROLE_TEEN,
    MEMBER_ROLE_BABY,
    MEMBER_ROLE_PREGNANT,
)

# 饮食特征（前端档案表单多选枚举）
MEMBER_TRAIT_MUSCLE: str = "muscle"  # 健身增肌
MEMBER_TRAIT_PREGNANT: str = "pregnant"  # 孕期营养
MEMBER_TRAIT_BABY_FOOD: str = "baby-food"  # 辅食期
MEMBER_TRAIT_VEGETARIAN: str = "vegetarian"  # 素食倾向
MEMBER_TRAIT_WEIGHT: str = "weight"  # 控制体重
MEMBER_TRAIT_AGING: str = "aging"  # 老年营养
MEMBER_TRAITS_ENUM = (
    MEMBER_TRAIT_MUSCLE,
    MEMBER_TRAIT_PREGNANT,
    MEMBER_TRAIT_BABY_FOOD,
    MEMBER_TRAIT_VEGETARIAN,
    MEMBER_TRAIT_WEIGHT,
    MEMBER_TRAIT_AGING,
)

# 前端未提供 age/gender/diet_goal 时，按角色/特征推导默认值
ROLE_DEFAULT_AGE_MAP: dict[str, float] = {
    "": 35.0,
    MEMBER_ROLE_ADULT: 35.0,
    MEMBER_ROLE_ELDERS: 70.0,
    MEMBER_ROLE_CHILD: 8.0,
    MEMBER_ROLE_TEEN: 15.0,
    MEMBER_ROLE_BABY: 2.0,
    MEMBER_ROLE_PREGNANT: 30.0,
}
# 前端"不指定"与缺失成员时默认性别（nutrition_service 按非 male 走成人女性基准）
MEMBER_DEFAULT_GENDER: str = GENDER_OTHER

# 饮食目标（单选）
DIET_GOAL_NORMAL: str = "normal"  # 均衡膳食
DIET_GOAL_SLIM: str = "slim"  # 减脂
DIET_GOAL_MUSCLE: str = "muscle"  # 健身增肌
DIET_GOAL_PREGNANT: str = "pregnant"  # 孕妈
DIET_GOAL_BABY: str = "baby"  # 婴幼儿辅食
DIET_GOAL_ELDERLY: str = "elderly"  # 老年营养
DIET_GOAL_VEGETARIAN: str = "vegetarian"  # 素食
DIET_GOAL_ENUM = (
    DIET_GOAL_NORMAL,
    DIET_GOAL_SLIM,
    DIET_GOAL_MUSCLE,
    DIET_GOAL_PREGNANT,
    DIET_GOAL_BABY,
    DIET_GOAL_ELDERLY,
    DIET_GOAL_VEGETARIAN,
)

# 附加需求（多选，叠加在主目标之上，不互相覆盖）
DIETARY_NEED_VEGETARIAN: str = "vegetarian"  # 素食
DIETARY_NEED_LOW_SALT: str = "low_salt"  # 低盐
DIETARY_NEED_LOW_SUGAR: str = "low_sugar"  # 控糖
DIETARY_NEED_LOW_FAT: str = "low_fat"  # 低脂
DIETARY_NEED_IRON_SUPP: str = "iron_supp"  # 补铁
DIETARY_NEED_HIGH_FIBER: str = "high_fiber"  # 高纤维
DIETARY_NEED_ENUM = (
    DIETARY_NEED_VEGETARIAN,
    DIETARY_NEED_LOW_SALT,
    DIETARY_NEED_LOW_SUGAR,
    DIETARY_NEED_LOW_FAT,
    DIETARY_NEED_IRON_SUPP,
    DIETARY_NEED_HIGH_FIBER,
)
DIETARY_NEED_LABEL_CN: dict[str, str] = {
    DIETARY_NEED_VEGETARIAN: "素食",
    DIETARY_NEED_LOW_SALT: "低盐",
    DIETARY_NEED_LOW_SUGAR: "控糖",
    DIETARY_NEED_LOW_FAT: "低脂",
    DIETARY_NEED_IRON_SUPP: "补铁",
    DIETARY_NEED_HIGH_FIBER: "高纤维",
}

# ===== 活动水平（能量计算用）=====
ACTIVITY_SEDENTARY: str = "sedentary"  # 久坐少动
ACTIVITY_LIGHT: str = "light"  # 轻度活动
ACTIVITY_MODERATE: str = "moderate"  # 中度活动
ACTIVITY_HEAVY: str = "heavy"  # 重度活动
ACTIVITY_ENUM = (
    ACTIVITY_SEDENTARY,
    ACTIVITY_LIGHT,
    ACTIVITY_MODERATE,
    ACTIVITY_HEAVY,
)
# 活动系数（PAL，乘以基础代谢）
ACTIVITY_PAL: dict[str, float] = {
    ACTIVITY_SEDENTARY: 1.2,
    ACTIVITY_LIGHT: 1.375,
    ACTIVITY_MODERATE: 1.55,
    ACTIVITY_HEAVY: 1.725,
}
# 饮食目标能量系数（在基础能量上乘；未列出的目标系数为 1.0）
DIET_GOAL_ENERGY_FACTOR: dict[str, float] = {
    DIET_GOAL_MUSCLE: 1.15,  # 增肌：能量盈余
    DIET_GOAL_SLIM: 0.85,  # 减脂：能量缺口
}
# 孕妈能量追加（千卡/天，简化取孕中期）
PREGNANT_ENERGY_ADD_KCAL: float = 300.0

# 体质类型（多选枚举）
CONSTITUTION_BALANCED: str = "balanced"  # 平和质
CONSTITUTION_QI_DEF: str = "qi_deficiency"  # 气虚质
CONSTITUTION_YANG_DEF: str = "yang_deficiency"  # 阳虚质（体寒）
CONSTITUTION_YIN_DEF: str = "yin_deficiency"  # 阴虚质
CONSTITUTION_PHLEGM: str = "phlegm_dampness"  # 痰湿质
CONSTITUTION_BLOOD_STASIS: str = "blood_stasis"  # 血瘀质
CONSTITUTION_HEAT: str = "damp_heat"  # 湿热质
CONSTITUTION_QI_STAG: str = "qi_stagnation"  # 气郁质
CONSTITUTION_SPECIAL: str = "special"  # 特禀质
# 前端档案表单（family-ai-recipe.html）使用的体质枚举（与上并集，向后端原枚举兼容）
CONSTITUTION_FE_COLD: str = "cold"  # 体质偏寒
CONSTITUTION_FE_HOT: str = "hot"  # 体质偏热
CONSTITUTION_FE_QI_DEF: str = "qi-deficiency"  # 气虚质（前端 key）
CONSTITUTION_FE_YIN_DEF: str = "yin-deficiency"  # 阴虚质（前端 key）
CONSTITUTION_FE_DAMPNESS: str = "dampness"  # 痰湿/湿热
CONSTITUTION_FE_STOMACH: str = "stomach"  # 脾胃虚寒
CONSTITUTION_ENUM = (
    CONSTITUTION_BALANCED,
    CONSTITUTION_QI_DEF,
    CONSTITUTION_YANG_DEF,
    CONSTITUTION_YIN_DEF,
    CONSTITUTION_PHLEGM,
    CONSTITUTION_BLOOD_STASIS,
    CONSTITUTION_HEAT,
    CONSTITUTION_QI_STAG,
    CONSTITUTION_SPECIAL,
    CONSTITUTION_FE_COLD,
    CONSTITUTION_FE_HOT,
    CONSTITUTION_FE_QI_DEF,
    CONSTITUTION_FE_YIN_DEF,
    CONSTITUTION_FE_DAMPNESS,
    CONSTITUTION_FE_STOMACH,
)

# 健康状况（慢病倾向，多选枚举）
HEALTH_NONE: str = "none"
HEALTH_HYPERTENSION: str = "hypertension"  # 高血压
HEALTH_DIABETES: str = "diabetes"  # 糖尿病
HEALTH_HYPERLIPIDEMIA: str = "hyperlipidemia"  # 高血脂
HEALTH_GOUT: str = "gout"  # 痛风
HEALTH_KIDNEY: str = "kidney"  # 肾病
# 前端档案表单使用的健康状况枚举（营养倾向目，与上并集）
HEALTH_FE_ANEMIA: str = "anemia"  # 贫血倾向
HEALTH_FE_LOW_PROTEIN: str = "low-protein"  # 优质蛋白不足
HEALTH_FE_LOW_CALCIUM: str = "low-calcium"  # 钙摄入不足
HEALTH_FE_LOW_VITA: str = "low-vita"  # 维生素A不足
HEALTH_ENUM = (
    HEALTH_NONE,
    HEALTH_HYPERTENSION,
    HEALTH_DIABETES,
    HEALTH_HYPERLIPIDEMIA,
    HEALTH_GOUT,
    HEALTH_KIDNEY,
    HEALTH_FE_ANEMIA,
    HEALTH_FE_LOW_PROTEIN,
    HEALTH_FE_LOW_CALCIUM,
    HEALTH_FE_LOW_VITA,
)

# 过敏原（枚举 + 自定义输入）
ALLERGEN_PEANUT: str = "peanut"  # 花生
ALLERGEN_EGG: str = "egg"  # 鸡蛋
ALLERGEN_SHELLFISH: str = "shellfish"  # 海鲜/贝类
ALLERGEN_MILK: str = "milk"  # 牛奶
ALLERGEN_SOY: str = "soy"  # 大豆
ALLERGEN_GLUTEN: str = "gluten"  # 麸质
# 前端档案表单使用的过敏原枚举（与上并集；shellfish 与 seafood 语义一致均保留）
ALLERGEN_FE_SEAFOOD: str = "seafood"  # 海鲜（前端 key）
ALLERGEN_FE_NUTS: str = "nuts"  # 花生/坚果
ALLERGEN_FE_SPICY: str = "spicy"  # 辛辣
ALLERGEN_FE_NIGHTSHADE: str = "nightshade"  # 番茄/茄果
ALLERGEN_ENUM = (
    ALLERGEN_PEANUT,
    ALLERGEN_EGG,
    ALLERGEN_SHELLFISH,
    ALLERGEN_MILK,
    ALLERGEN_SOY,
    ALLERGEN_GLUTEN,
    ALLERGEN_FE_SEAFOOD,
    ALLERGEN_FE_NUTS,
    ALLERGEN_FE_SPICY,
    ALLERGEN_FE_NIGHTSHADE,
)

# ===== 食材 =====
INGREDIENT_WEIGHT_UNIT: str = "g"
INGREDIENT_IS_VALID: int = 1
INGREDIENT_INVALID: int = 0

# ===== 营养缺口 & 采购清单 =====
# 反馈比例折算基准：前端反馈按"食用比例"提交时，整道菜参考总量（克/份×份数）
DISH_SERVING_BASE_G: float = 200.0  # 每份参考基准量（无总量时兜底估算）

# 核心营养素（仅这些参与采购触发）
CORE_NUTRIENTS: tuple[str, ...] = (
    "protein",  # 蛋白质
    "calcium",  # 钙
    "iron",  # 铁
    "zinc",  # 锌
    "vitamin_a",  # 维生素A
    "vitamin_c",  # 维生素C
)

NUTRIENT_LABEL_CN: dict[str, str] = {
    "protein": "蛋白质",
    "calcium": "钙",
    "iron": "铁",
    "zinc": "锌",
    "vitamin_a": "维生素A",
    "vitamin_c": "维生素C",
}

# 缺口占比阈值：任意成员任意核心营养素缺口 > 30% 触发采购
GAP_TRIGGER_RATIO: float = 0.30
# 主菜数量下限：生成主菜 < 2 道触发采购
MIN_MAIN_DISHES: int = 2
# 采购满足天数（一期固定 3 天）
PURCHASE_DAYS: int = 3
# 采购优先级
PURCHASE_P0: str = "P0"  # 缺口最大成员核心营养素来源食材
PURCHASE_P1: str = "P1"  # 性价比家常食材
PURCHASE_P2: str = "P2"  # 小众食材
PURCHASE_PRIORITY_ORDER: tuple[str, ...] = (PURCHASE_P0, PURCHASE_P1, PURCHASE_P2)

# 已有存量但未填重量的备注
REMARK_HAS_NO_WEIGHT: str = "家中已有，评估存量后采购"
REMARK_ALREADY_ENOUGH: str = "家中存量已满足"

# ===== 餐次 =====
MEAL_BREAKFAST: str = "breakfast"  # 早餐
MEAL_LUNCH: str = "lunch"  # 午餐
MEAL_DINNER: str = "dinner"  # 晚餐
MEAL_SNACK: str = "snack"  # 加餐
MEAL_TYPE_ENUM = (MEAL_BREAKFAST, MEAL_LUNCH, MEAL_DINNER, MEAL_SNACK)
MEAL_TYPE_LABEL_CN: dict[str, str] = {
    MEAL_BREAKFAST: "早餐",
    MEAL_LUNCH: "午餐",
    MEAL_DINNER: "晚餐",
    MEAL_SNACK: "加餐",
}
# 每餐能量占全天比例（加餐 0.10，其余三餐 30/40/30）
MEAL_ENERGY_SHARE: dict[str, float] = {
    MEAL_BREAKFAST: 0.30,
    MEAL_LUNCH: 0.40,
    MEAL_DINNER: 0.30,
    MEAL_SNACK: 0.10,
}

# 缺口"怎么补"建议（本地规则生成，不依赖大模型；展示用前 3 项）
GAP_ADVICE_CN: dict[str, list[str]] = {
    "energy": ["主食适量加量", "优质蛋白（蛋/奶/瘦肉）"],
    "protein": ["鸡蛋", "瘦肉/鸡胸肉", "豆制品/豆腐"],
    "calcium": ["牛奶/酸奶", "豆腐/豆制品", "深绿叶菜"],
    "iron": ["红肉/牛肉", "猪肝/动物血", "豆类"],
    "zinc": ["生蚝/贝类", "瘦牛肉", "动物内脏"],
    "vitamin_a": ["胡萝卜", "猪肝", "菠菜/深绿叶菜"],
    "vitamin_c": ["橙子/柑橘", "青椒/彩椒", "番茄/西兰花"],
}
# 历史联动：同一成员同一营养素缺口>30% 连续满 N 天 → 采购必买项
GAP_CONSECUTIVE_DAYS: int = 3
# 历史联动窗口（天）：只看最近 N 天内的反馈/估算
HISTORY_WINDOW_DAYS: int = 7

# 婴幼儿（<3 岁或 diet_goal=baby）禁食关键词（窒息/中毒/高盐风险）
BABY_FORBIDDEN_KEYWORDS: tuple[str, ...] = (
    "蜂蜜", "蜂",           # 肉毒杆菌风险
    "坚果", "核桃", "杏仁", "腰果", "花生",  # 整粒窒息风险
    "刺身", "生鱼", "溏心", "半熟", "生食",   # 生食感染风险
    "腊", "咸菜", "泡菜", "腌制", "火腿",    # 高盐/亚硝酸盐
)

# ===== 反馈 & 周报 =====
EXCEED_RATIO: float = 1.2  # 实际摄入 > 1.2 × RNI 视为超标
WEEK_REPORT_MANUAL: int = 0  # 手动生成
WEEK_REPORT_AUTO: int = 1  # 每周日自动生成
# 周报"数据不足"阈值：整周实际记录天数少于该值提示结论仅供参考
WEEK_REPORT_MIN_ACTUAL_DAYS: int = 3

# ===== 逻辑删除标记 =====
DELETE_FLAG_ACTIVE: int = 0
DELETE_FLAG_DELETED: int = 1

# ===== AI 引擎 =====
LLM_TIMEOUT_SEC: float = 30.0  # LLM 调用超时
LLM_MAX_RETRY: int = 1  # JSON 解析失败重试次数
LLM_TIMEOUT_MSG: str = "生成食谱超时，请减少食材或稍后重试"
LLM_JSON_ERROR_MSG: str = "食谱生成结果解析失败，请重试"
DEFAULT_PROMPT_MAX_CHARS: int = 6000

# 佐料/调味不进采购清单（家庭常备，无需专门采购）
SEASONING_EXACT: frozenset[str] = frozenset({
    "盐", "糖", "白糖", "冰糖", "油", "食用油", "橄榄油", "花生油",
    "菜籽油", "芝麻油", "香油", "猪油", "大豆油", "黄油",
    "葱", "小葱", "大葱", "葱花", "姜", "姜片", "姜丝", "生姜",
    "蒜", "蒜末", "蒜瓣", "大蒜", "蒜蓉", "蒜泥",
    "酱油", "生抽", "老抽", "醋", "料酒", "蚝油", "鸡精", "味精",
    "淀粉", "生粉", "花椒", "八角", "桂皮", "香叶",
    "黑胡椒", "白胡椒", "胡椒粉", "孜然", "五香粉",
    "豆瓣酱", "辣椒酱", "番茄酱", "甜面酱", "蜂蜜",
    "水", "温水", "开水", "清水", "热水", "凉水", "纯净水",
})


def is_seasoning(name: str) -> bool:
    """判断食材名是否为佐料/调味/水（采购清单应过滤）。"""
    n = (name or "").strip()
    if not n:
        return True
    # 剥离括号注释（如"蜂蜜（可选）""葱（装饰）"）后再判断
    base = n.split("（", 1)[0].split("(", 1)[0].strip()
    if base in SEASONING_EXACT:
        return True
    if base.endswith("油") or base.endswith("酱"):
        return True
    if any(k in base for k in ("胡椒", "花椒", "八角", "桂皮", "香叶")):
        return True
    return False

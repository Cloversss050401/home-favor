"""业务常量中心：全部业务阈值、枚举、配置统一放此处，禁止散落在业务代码中。"""

# ===== 家庭成员档案 =====
MEMBER_NAME_MAX_LEN: int = 20
MEMBER_FAMILY_LIMIT: int = 8          # 单家庭最多成员数
AGE_MIN: float = 0.0
AGE_MAX: float = 120.0

# 性别枚举
GENDER_MALE: str = "male"
GENDER_FEMALE: str = "female"
GENDER_OTHER: str = "other"
GENDER_ENUM = (GENDER_MALE, GENDER_FEMALE, GENDER_OTHER)

# 饮食目标（单选）
DIET_GOAL_NORMAL: str = "normal"                  # 均衡膳食
DIET_GOAL_SLIM: str = "slim"                      # 减脂
DIET_GOAL_MUSCLE: str = "muscle"                  # 健身增肌
DIET_GOAL_PREGNANT: str = "pregnant"              # 孕妈
DIET_GOAL_BABY: str = "baby"                      # 婴幼儿辅食
DIET_GOAL_ELDERLY: str = "elderly"                # 老年营养
DIET_GOAL_ENUM = (
    DIET_GOAL_NORMAL, DIET_GOAL_SLIM, DIET_GOAL_MUSCLE,
    DIET_GOAL_PREGNANT, DIET_GOAL_BABY, DIET_GOAL_ELDERLY,
)

# 体质类型（多选枚举）
CONSTITUTION_BALANCED: str = "balanced"           # 平和质
CONSTITUTION_QI_DEF: str = "qi_deficiency"        # 气虚质
CONSTITUTION_YANG_DEF: str = "yang_deficiency"    # 阳虚质（体寒）
CONSTITUTION_YIN_DEF: str = "yin_deficiency"      # 阴虚质
CONSTITUTION_PHLEGM: str = "phlegm_dampness"      # 痰湿质
CONSTITUTION_BLOOD_STASIS: str = "blood_stasis"   # 血瘀质
CONSTITUTION_HEAT: str = "damp_heat"              # 湿热质
CONSTITUTION_QI_STAG: str = "qi_stagnation"       # 气郁质
CONSTITUTION_SPECIAL: str = "special"             # 特禀质
CONSTITUTION_ENUM = (
    CONSTITUTION_BALANCED, CONSTITUTION_QI_DEF, CONSTITUTION_YANG_DEF,
    CONSTITUTION_YIN_DEF, CONSTITUTION_PHLEGM, CONSTITUTION_BLOOD_STASIS,
    CONSTITUTION_HEAT, CONSTITUTION_QI_STAG, CONSTITUTION_SPECIAL,
)

# 健康状况（慢病倾向，多选枚举）
HEALTH_NONE: str = "none"
HEALTH_HYPERTENSION: str = "hypertension"         # 高血压
HEALTH_DIABETES: str = "diabetes"                 # 糖尿病
HEALTH_HYPERLIPIDEMIA: str = "hyperlipidemia"     # 高血脂
HEALTH_GOUT: str = "gout"                         # 痛风
HEALTH_KIDNEY: str = "kidney"                     # 肾病
HEALTH_ENUM = (
    HEALTH_NONE, HEALTH_HYPERTENSION, HEALTH_DIABETES,
    HEALTH_HYPERLIPIDEMIA, HEALTH_GOUT, HEALTH_KIDNEY,
)

# 过敏原（枚举 + 自定义输入）
ALLERGEN_PEANUT: str = "peanut"                   # 花生
ALLERGEN_EGG: str = "egg"                         # 鸡蛋
ALLERGEN_SHELLFISH: str = "shellfish"             # 海鲜/贝类
ALLERGEN_MILK: str = "milk"                       # 牛奶
ALLERGEN_SOY: str = "soy"                         # 大豆
ALLERGEN_GLUTEN: str = "gluten"                   # 麸质
ALLERGEN_ENUM = (
    ALLERGEN_PEANUT, ALLERGEN_EGG, ALLERGEN_SHELLFISH,
    ALLERGEN_MILK, ALLERGEN_SOY, ALLERGEN_GLUTEN,
)

# ===== 食材 =====
INGREDIENT_WEIGHT_UNIT: str = "g"
INGREDIENT_IS_VALID: int = 1
INGREDIENT_INVALID: int = 0

# ===== 营养缺口 & 采购清单 =====
# 核心营养素（仅这些参与采购触发）
CORE_NUTRIENTS: tuple[str, ...] = (
    "protein",      # 蛋白质
    "calcium",      # 钙
    "iron",         # 铁
    "zinc",         # 锌
    "vitamin_a",    # 维生素A
    "vitamin_c",    # 维生素C
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
PURCHASE_P0: str = "P0"   # 缺口最大成员核心营养素来源食材
PURCHASE_P1: str = "P1"   # 性价比家常食材
PURCHASE_P2: str = "P2"   # 小众食材
PURCHASE_PRIORITY_ORDER: tuple[str, ...] = (PURCHASE_P0, PURCHASE_P1, PURCHASE_P2)

# 已有存量但未填重量的备注
REMARK_HAS_NO_WEIGHT: str = "家中已有，评估存量后采购"
REMARK_ALREADY_ENOUGH: str = "家中存量已满足"

# ===== 反馈 & 周报 =====
EXCEED_RATIO: float = 1.2          # 实际摄入 > 1.2 × RNI 视为超标
WEEK_REPORT_MANUAL: int = 0        # 手动生成
WEEK_REPORT_AUTO: int = 1          # 每周日自动生成

# ===== 逻辑删除标记 =====
DELETE_FLAG_ACTIVE: int = 0
DELETE_FLAG_DELETED: int = 1

# ===== AI 引擎 =====
LLM_TIMEOUT_SEC: float = 30.0      # LLM 调用超时
LLM_MAX_RETRY: int = 1             # JSON 解析失败重试次数
LLM_TIMEOUT_MSG: str = "生成食谱超时，请减少食材或稍后重试"
LLM_JSON_ERROR_MSG: str = "食谱生成结果解析失败，请重试"
DEFAULT_PROMPT_MAX_CHARS: int = 6000
"""家庭档案 DTO：家庭名称级档案的读取与更新（DEF-01 持久化修复）。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FamilyOut(BaseModel):
    """家庭档案输出（含逻辑删除标记，供前端回填）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str = Field(default="我的家庭", max_length=50)
    is_deleted: int
    created_at: datetime
    updated_at: datetime


class FamilyUpdate(BaseModel):
    """家庭名称更新：1-50 字符，去除首尾空白。"""

    name: str = Field(min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("家庭名称不能为空")
        return v



from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.constants import (
    ACTIVITY_ENUM,
    AGE_MAX,
    AGE_MIN,
    ALLERGEN_ENUM,
    CONSTITUTION_ENUM,
    DIETARY_NEED_ENUM,
    DIET_GOAL_ENUM,
    GENDER_ENUM,
    HEALTH_ENUM,
    MEMBER_DEFAULT_GENDER,
    MEMBER_FAMILY_LIMIT,
    MEMBER_NAME_MAX_LEN,
    MEMBER_ROLE_ENUM,
    ROLE_DEFAULT_AGE_MAP,
)

_MEMBER_AVOID_MAX_LEN: int = 200


class MemberBase(BaseModel):
    name: str = Field(min_length=1, max_length=MEMBER_NAME_MAX_LEN)
    role: str = Field(
        default="",
        description="家庭角色（前端契约）：adult/elders/child/teen/baby/pregnant，"
        " 表示不指定",
    )
    height_cm: Decimal | None = Field(
        default=None, ge=30, le=250, description="身高（cm），可空"
    )
    weight_kg: Decimal | None = Field(
        default=None, ge=1, le=300, description="体重（kg），可空"
    )
    activity: str | None = Field(
        default=None, description="活动水平 sedentary/light/moderate/heavy；缺省 light"
    )
    age: Decimal | None = Field(
        default=None,
        ge=AGE_MIN,
        le=AGE_MAX,
        description="年龄 0-120，支持婴儿小数；缺省按 role 推导",
    )
    gender: str | None = Field(default=None, description="性别；缺省 other")
    diet_goal: str | None = Field(
        default=None, description="饮食目标；缺省按 role 推导"
    )
    dietary_needs: list[str] = Field(
        default_factory=list,
        description="附加需求（多选，叠加在主目标之上）：素食/低盐/控糖/低脂/补铁/高纤维",
    )
    constitution: list[str] = Field(default_factory=list)
    health_conditions: list[str] = Field(default_factory=list)
    allergens: list[str] = Field(default_factory=list)
    dietary_restrictions: list[str] = Field(default_factory=list)
    avoid: str = Field(
        default="",
        max_length=_MEMBER_AVOID_MAX_LEN,
        description="其他忌口自由文本（前端契约）",
    )

    @field_validator("role")
    @classmethod
    def _check_role(cls, v: str) -> str:
        if v not in MEMBER_ROLE_ENUM:
            raise ValueError(f"role 必须为 {MEMBER_ROLE_ENUM} 之一")
        return v

    @field_validator("activity")
    @classmethod
    def _check_activity(cls, v: str | None) -> str | None:
        if v is not None and v not in ACTIVITY_ENUM:
            raise ValueError(f"activity 必须为 {ACTIVITY_ENUM} 之一")
        return v

    @field_validator("gender")
    @classmethod
    def _check_gender(cls, v: str | None) -> str | None:
        if v is not None and v not in GENDER_ENUM:
            raise ValueError(f"gender 必须为 {GENDER_ENUM} 之一")
        return v

    @field_validator("diet_goal")
    @classmethod
    def _check_diet_goal(cls, v: str | None) -> str | None:
        if v is not None and v not in DIET_GOAL_ENUM:
            raise ValueError(f"diet_goal 必须为 {DIET_GOAL_ENUM} 之一")
        return v

    @field_validator("dietary_needs")
    @classmethod
    def _check_dietary_needs(cls, v: list[str]) -> list[str]:
        unknown = [x for x in v if x not in DIETARY_NEED_ENUM]
        if unknown:
            raise ValueError(f"dietary_needs 含非法枚举: {unknown}")
        return list(dict.fromkeys(v))  # 去重保序

    @field_validator("constitution")
    @classmethod
    def _check_constitution(cls, v: list[str]) -> list[str]:
        unknown = [x for x in v if x not in CONSTITUTION_ENUM]
        if unknown:
            raise ValueError(f"constitution 含非法枚举: {unknown}")
        return v

    @field_validator("health_conditions")
    @classmethod
    def _check_health(cls, v: list[str]) -> list[str]:
        unknown = [x for x in v if x not in HEALTH_ENUM]
        if unknown:
            raise ValueError(f"health_conditions 含非法枚举: {unknown}")
        return v

    @field_validator("allergens")
    @classmethod
    def _check_allergens(cls, v: list[str]) -> list[str]:
        """过敏原支持枚举 + 自定义输入（含枚举值以外的自定义文本视为合法）。"""
        return [x.strip() for x in v if x.strip()]

    @field_validator("dietary_restrictions")
    @classmethod
    def _check_restrictions(cls, v: list[str]) -> list[str]:
        return [x.strip() for x in v if x.strip()]

    @model_validator(mode="after")
    def _apply_frontend_defaults(self) -> "MemberBase":
        """前端契约兼容：age/gender/diet_goal/activity 缺省时按 role 推导。

        - age：按角色取默认年龄段（baby=2 / child=8 / teen=15 / adult=35 / elders=70 / pregnant=30）
        - gender：默认 other（nutrition_service 按非 male 走成人女性基准）
        - diet_goal：空或未选时按 role 推导（pregnant/baby/elders），其余默认 normal；
          前端显式提交 normal 不再覆盖角色推导
        - activity：默认 light
        """
        if self.age is None:
            self.age = Decimal(str(ROLE_DEFAULT_AGE_MAP.get(self.role, 35.0)))
        if self.gender is None:
            self.gender = MEMBER_DEFAULT_GENDER
        if self.activity is None:
            self.activity = "light"
        if not self.diet_goal:
            if self.role == "pregnant":
                self.diet_goal = "pregnant"
            elif self.role == "baby":
                self.diet_goal = "baby"
            elif self.role == "elders":
                self.diet_goal = "elderly"
            else:
                self.diet_goal = "normal"
        return self


class MemberCreate(MemberBase):
    family_id: int = Field(default=1, gt=0)


class MemberUpdate(BaseModel):
    """字段全部可选：仅更新传入的字段。"""

    name: str | None = Field(default=None, min_length=1, max_length=MEMBER_NAME_MAX_LEN)
    role: str | None = Field(default=None, description="家庭角色（前端契约）")
    height_cm: Decimal | None = Field(default=None, ge=30, le=250)
    weight_kg: Decimal | None = Field(default=None, ge=1, le=300)
    activity: str | None = None
    age: Decimal | None = Field(default=None, ge=AGE_MIN, le=AGE_MAX)
    gender: str | None = None
    diet_goal: str | None = None
    dietary_needs: list[str] | None = Field(
        default=None, description="附加需求多选（覆盖式更新）"
    )
    constitution: list[str] | None = None
    health_conditions: list[str] | None = None
    allergens: list[str] | None = None
    dietary_restrictions: list[str] | None = None
    avoid: str | None = Field(default=None, max_length=_MEMBER_AVOID_MAX_LEN)

    @field_validator("role")
    @classmethod
    def _check_role(cls, v: str | None) -> str | None:
        if v is not None and v not in MEMBER_ROLE_ENUM:
            raise ValueError(f"role 必须为 {MEMBER_ROLE_ENUM} 之一")
        return v

    @field_validator("activity")
    @classmethod
    def _check_activity(cls, v: str | None) -> str | None:
        if v is not None and v not in ACTIVITY_ENUM:
            raise ValueError(f"activity 必须为 {ACTIVITY_ENUM} 之一")
        return v

    @field_validator("gender")
    @classmethod
    def _check_gender(cls, v: str | None) -> str | None:
        if v is not None and v not in GENDER_ENUM:
            raise ValueError(f"gender 必须为 {GENDER_ENUM} 之一")
        return v

    @field_validator("diet_goal")
    @classmethod
    def _check_diet_goal(cls, v: str | None) -> str | None:
        if v is not None and v not in DIET_GOAL_ENUM:
            raise ValueError(f"diet_goal 必须为 {DIET_GOAL_ENUM} 之一")
        return v

    @field_validator("dietary_needs")
    @classmethod
    def _check_dietary_needs_u(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        unknown = [x for x in v if x not in DIETARY_NEED_ENUM]
        if unknown:
            raise ValueError(f"dietary_needs 含非法枚举: {unknown}")
        return list(dict.fromkeys(v))

    @field_validator("constitution")
    @classmethod
    def _check_constitution(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        unknown = [x for x in v if x not in CONSTITUTION_ENUM]
        if unknown:
            raise ValueError(f"constitution 含非法枚举: {unknown}")
        return v

    @field_validator("health_conditions")
    @classmethod
    def _check_health(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        unknown = [x for x in v if x not in HEALTH_ENUM]
        if unknown:
            raise ValueError(f"health_conditions 含非法枚举: {unknown}")
        return v


class MemberOut(MemberBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    family_id: int
    is_deleted: int
    created_at: datetime
    updated_at: datetime


class MemberListOut(BaseModel):
    total: int
    items: list[MemberOut]


class MemberLimitMessage(BaseModel):
    """成员上限提示。"""

    ok: bool = False
    message: str = f"最多添加 {MEMBER_FAMILY_LIMIT} 位家庭成员"

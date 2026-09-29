"""家庭成员档案 DTO：对齐硬性业务规则第 3 条。

- 年龄 0-120，支持婴儿小数（如 8 月龄 0.67）
- 姓名 ≤ 20 字符
- 性别枚举；饮食目标单选；体质/健康状况多选枚举；过敏原支持枚举+自定义；忌口自定义文本数组
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.config.constants import (
    AGE_MAX,
    AGE_MIN,
    ALLERGEN_ENUM,
    CONSTITUTION_ENUM,
    DIET_GOAL_ENUM,
    GENDER_ENUM,
    HEALTH_ENUM,
    MEMBER_FAMILY_LIMIT,
    MEMBER_NAME_MAX_LEN,
)


class MemberBase(BaseModel):
    name: str = Field(min_length=1, max_length=MEMBER_NAME_MAX_LEN)
    age: Decimal = Field(ge=AGE_MIN, le=AGE_MAX, description="年龄 0-120，支持婴儿小数")
    gender: str
    diet_goal: str
    constitution: list[str] = Field(default_factory=list)
    health_conditions: list[str] = Field(default_factory=list)
    allergens: list[str] = Field(default_factory=list)
    dietary_restrictions: list[str] = Field(default_factory=list)

    @field_validator("gender")
    @classmethod
    def _check_gender(cls, v: str) -> str:
        if v not in GENDER_ENUM:
            raise ValueError(f"gender 必须为 {GENDER_ENUM} 之一")
        return v

    @field_validator("diet_goal")
    @classmethod
    def _check_diet_goal(cls, v: str) -> str:
        if v not in DIET_GOAL_ENUM:
            raise ValueError(f"diet_goal 必须为 {DIET_GOAL_ENUM} 之一")
        return v

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


class MemberCreate(MemberBase):
    family_id: int = Field(default=1, gt=0)


class MemberUpdate(BaseModel):
    """字段全部可选：仅更新传入的字段。"""

    name: str | None = Field(default=None, min_length=1, max_length=MEMBER_NAME_MAX_LEN)
    age: Decimal | None = Field(default=None, ge=AGE_MIN, le=AGE_MAX)
    gender: str | None = None
    diet_goal: str | None = None
    constitution: list[str] | None = None
    health_conditions: list[str] | None = None
    allergens: list[str] | None = None
    dietary_restrictions: list[str] | None = None

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
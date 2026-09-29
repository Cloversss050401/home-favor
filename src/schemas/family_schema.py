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

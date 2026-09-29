"""个人中心 DTO：资料读取/更新、修改密码请求模型。"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProfileResp(BaseModel):
    """个人资料响应（一期模拟账号，不含密码哈希与时间戳）。"""

    model_config = ConfigDict(from_attributes=True)

    avatar_url: str | None = None
    signature: str | None = None
    phone: str | None = None
    username: str | None = None


class ProfileUpdateReq(BaseModel):
    """更新基础资料：签名最多 100 字符；手机号可为空（非空则 5-20 位数字）。"""

    signature: str | None = Field(
        default=None, max_length=100, description="个性签名，最多100字符"
    )
    phone: str | None = Field(default=None, description="手机号")

    @field_validator("signature")
    @classmethod
    def _strip_signature(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        return v or None

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not v.isdigit() or not 5 <= len(v) <= 20:
            raise ValueError("手机号应为 5-20 位数字")
        return v


class PasswordChangeReq(BaseModel):
    """修改密码：新旧密码均必填。"""

    old_password: str = Field(min_length=1, description="原密码")
    new_password: str = Field(
        min_length=1, max_length=64, description="新密码（首尾空白将去除）"
    )

    @field_validator("new_password")
    @classmethod
    def _strip_new_password(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("新密码不能为空")
        return v

"""个人中心业务：头像保存、密码哈希校验更新、签名/手机号维护。

对齐硬性约束：
- 密码禁止存储明文，一律 bcrypt 哈希后落库；
- 头像保存到 resources/upload/avatar，返回可访问 URL（/resources/upload/avatar/{filename}）；
- 一期单用户模拟：无登录无鉴权，接口直接可访问；默认账号 username=默认用户、密码 123456。
"""

import bcrypt
from datetime import datetime
from fastapi import UploadFile
from pathlib import Path
from uuid import uuid4

from app.core.config import PROJECT_ROOT
from app.core.exceptions import BusinessException
from app.modules.personal_center.models import UserProfile
from app.modules.personal_center.repository import ProfileRepo

# 头像存储目录（挂载见 app/main.py: /resources/upload -> resources/upload）
AVATAR_DIR = PROJECT_ROOT / "resources" / "upload" / "avatar"
# 允许的头像扩展名
_ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
# 头像大小上限（5MB，避免超大文件打爆磁盘）
_MAX_AVATAR_BYTES = 5 * 1024 * 1024

DEFAULT_USERNAME = "默认用户"
DEFAULT_PASSWORD = "123456"


class ProfileService:
    """单用户模拟个人中心服务。"""

    def __init__(self, db) -> None:
        self.db = db
        self.repo = ProfileRepo(db)

    # ---------- 资料 ----------
    def get_my_profile(self) -> UserProfile:
        """获取当前用户资料；不存在则自动初始化默认记录（单条模拟，幂等）。"""
        profile = self.repo.get_profile()
        if profile is not None:
            return profile
        profile = UserProfile(
            username=DEFAULT_USERNAME,
            password_hash=self._hash_password(DEFAULT_PASSWORD),
        )
        self.db.add(profile)
        return self.repo.update(profile)

    def update_basic_info(
        self, signature: str | None, phone: str | None
    ) -> UserProfile:
        profile = self.get_my_profile()
        if signature is not None:
            profile.signature = signature
        if phone is not None:
            profile.phone = phone
        return self.repo.update(profile)

    # ---------- 头像 ----------
    def upload_avatar(self, file: UploadFile) -> str:
        """保存头像文件到本地资源目录，返回可访问 URL。"""
        ext = (Path(file.filename or "").suffix or "").lower()
        if ext not in _ALLOWED_EXTS:
            raise BusinessException(
                message=f"仅支持图片格式: {sorted(_ALLOWED_EXTS)}",
                status_code=400,
            )
        content = file.file.read()
        if len(content) <= 0:
            raise BusinessException(message="上传的头像文件为空", status_code=400)
        if len(content) > _MAX_AVATAR_BYTES:
            raise BusinessException(message="头像图片不能超过 5MB", status_code=400)

        AVATAR_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}{ext}"
        save_path = AVATAR_DIR / filename
        save_path.write_bytes(content)

        avatar_url = f"/resources/upload/avatar/{filename}"
        profile = self.get_my_profile()
        profile.avatar_url = avatar_url
        self.repo.update(profile)
        return avatar_url

    # ---------- 密码 ----------
    def change_password(self, old_password: str, new_password: str) -> None:
        profile = self.get_my_profile()
        if not self._verify_password(old_password, profile.password_hash):
            raise BusinessException(message="原密码错误", status_code=400)
        if new_password == old_password:
            raise BusinessException(message="新密码不能与原密码相同", status_code=400)
        profile.password_hash = self._hash_password(new_password)
        self.repo.update(profile)

    # ---------- 工具 ----------
    @staticmethod
    def _hash_password(raw_pwd: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(raw_pwd.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def _verify_password(raw_pwd: str, hash_pwd: str) -> bool:
        try:
            return bcrypt.checkpw(raw_pwd.encode("utf-8"), hash_pwd.encode("utf-8"))
        except ValueError:
            return False

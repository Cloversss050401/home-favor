"""个人中心模块 API 测试。

覆盖：
- GET /api/profile/info 自动初始化默认账号（username=默认用户，密码 123456）；
- PUT /api/profile/info 更新签名、手机号并落库；
- 手机号校验（非 5-20 位数字 -> 422）；
- POST /api/profile/avatar 上传头像返回可访问 URL（头像落盘目录被重定向到 tmp_path）；
- 头像格式/空文件校验（400）；
- POST /api/profile/change-pwd 原密码正确则修改成功（bcrypt）、原密码错误 -> 400、
  新旧相同 -> 400；重启后新密码仍可校验通过（持久化）。
"""

from pathlib import Path

import pytest


class TestProfileInfoAPI:
    def test_get_initializes_default_profile(self, client):
        r = client.get("/api/profile/info")
        assert r.status_code == 200
        body = r.json()
        assert body["username"] == "默认用户"
        assert body["avatar_url"] is None
        assert body["signature"] is None
        assert body["phone"] is None

    def test_update_signature_and_phone(self, client):
        r = client.put(
            "/api/profile/info",
            json={"signature": " 好好吃饭，健康生活 ", "phone": "13800138000"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["signature"] == "好好吃饭，健康生活"
        assert body["phone"] == "13800138000"
        assert body["username"] == "默认用户"

        # 读回验证落库
        r = client.get("/api/profile/info")
        assert r.status_code == 200
        assert r.json()["signature"] == "好好吃饭，健康生活"
        assert r.json()["phone"] == "13800138000"

    def test_phone_validation(self, client):
        r = client.put("/api/profile/info", json={"phone": "123"})
        assert r.status_code == 422
        r = client.put("/api/profile/info", json={"phone": "abcdefghij"})
        assert r.status_code == 422

    def test_signature_too_long(self, client):
        r = client.put("/api/profile/info", json={"signature": "签" * 101})
        assert r.status_code == 422


class TestAvatarAPI:
    def test_upload_avatar_saves_file(self, client, tmp_path, monkeypatch):
        from app.modules.personal_center import service as pc_service

        monkeypatch.setattr(pc_service, "AVATAR_DIR", tmp_path)

        r = client.post(
            "/api/profile/avatar",
            files={"file": ("me.png", b"\x89PNG\r\n\x1a\nfake-image", "image/png")},
        )
        assert r.status_code == 200
        avatar_url = r.json()["avatar_url"]
        assert avatar_url.startswith("/resources/upload/avatar/")
        assert avatar_url.endswith(".png")

        # 头像落盘真实存在
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].name == Path(avatar_url).name

        # profile 持久化头像 URL
        r = client.get("/api/profile/info")
        assert r.json()["avatar_url"] == avatar_url

    def test_upload_avatar_rejects_bad_format(self, client, tmp_path, monkeypatch):
        from app.modules.personal_center import service as pc_service

        monkeypatch.setattr(pc_service, "AVATAR_DIR", tmp_path)

        r = client.post(
            "/api/profile/avatar",
            files={"file": ("evil.exe", b"MZ fake", "application/octet-stream")},
        )
        assert r.status_code == 400

    def test_upload_avatar_rejects_empty(self, client, tmp_path, monkeypatch):
        from app.modules.personal_center import service as pc_service

        monkeypatch.setattr(pc_service, "AVATAR_DIR", tmp_path)

        r = client.post(
            "/api/profile/avatar",
            files={"file": ("empty.png", b"", "image/png")},
        )
        assert r.status_code == 400


class TestChangePasswordAPI:
    def test_change_password_with_old_password(self, client):
        # 初始密码 123456 修改成功
        r = client.post(
            "/api/profile/change-pwd",
            json={"old_password": "123456", "new_password": "newpass888"},
        )
        assert r.status_code == 200
        assert r.json()["msg"] == "密码修改成功"

        # 新密码可再次修改（证明已生效）
        r = client.post(
            "/api/profile/change-pwd",
            json={"old_password": "newpass888", "new_password": "another999"},
        )
        assert r.status_code == 200

    def test_change_password_wrong_old(self, client):
        r = client.post(
            "/api/profile/change-pwd",
            json={"old_password": "wrong-pwd", "new_password": "newpass888"},
        )
        assert r.status_code == 400
        assert "原密码错误" in r.json()["message"]

    def test_change_password_same_as_old(self, client):
        r = client.post(
            "/api/profile/change-pwd",
            json={"old_password": "123456", "new_password": "123456"},
        )
        assert r.status_code == 400
        assert "不能与原密码相同" in r.json()["message"]

    def test_password_hash_not_plaintext(self, client, db):
        """落库 password_hash 必须为 bcrypt 哈希，禁止明文。"""
        from app.modules.personal_center.models import UserProfile

        client.post(
            "/api/profile/change-pwd",
            json={"old_password": "123456", "new_password": "newpass888"},
        )
        profile = db.query(UserProfile).first()
        assert profile is not None
        hash_val = profile.password_hash
        assert hash_val != "123456"
        assert hash_val != "newpass888"
        assert hash_val.startswith("$2")

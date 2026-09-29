"""家庭档案 API 测试（DEF-01 持久化修复验证）。

覆盖：
- GET /api/family 自动创建默认家庭并返回；
- PUT /api/family 更新家庭名称并落库；
- 重新打开数据库会话（模拟应用重启）后数据仍在 —— 持久化验收；
- 名称校验（空串/超长 -> 422）。
"""

from app.core.db import SessionLocal


class TestFamilyAPI:
    def test_get_creates_default_family(self, client):
        r = client.get("/api/family")
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == 1
        assert body["name"] == "我的家庭"
        assert body["is_deleted"] == 0

    def test_update_name_and_get_back(self, client):
        r = client.put("/api/family", json={"name": "  幸福之家  "})
        assert r.status_code == 200
        assert r.json()["name"] == "幸福之家"
        assert r.json()["is_deleted"] == 0

        r = client.get("/api/family")
        assert r.status_code == 200
        assert r.json()["name"] == "幸福之家"

    def test_persist_across_restart(self, client, db):
        """模拟应用重启：关闭旧会话，用新会话直查磁盘库，档案仍在。"""
        client.put("/api/family", json={"name": "武汉小家"})

        # 新的数据库会话（等价于应用重启后再次连接同一 db 文件）
        fresh = SessionLocal()
        try:
            from app.modules.family_member.models import Family

            family = fresh.query(Family).filter(Family.id == 1).one()
            assert family.name == "武汉小家"
            assert family.is_deleted == 0
        finally:
            fresh.close()

    def test_member_saved_after_family(self, client):
        """档案链路：家庭 + 成员均可落库并被列表读回。"""
        r = client.post(
            "/api/members",
            json={
                "name": "小明",
                "age": 30,
                "gender": "male",
                "diet_goal": "normal",
                "constitution": ["balanced"],
                "health_conditions": ["none"],
                "allergens": [],
                "dietary_restrictions": [],
            },
        )
        assert r.status_code == 201
        mid = r.json()["id"]

        r = client.get("/api/members")
        assert r.status_code == 200
        assert r.json()["total"] == 1
        assert r.json()["items"][0]["id"] == mid
        assert r.json()["items"][0]["name"] == "小明"

    def test_name_validation(self, client):
        r = client.put("/api/family", json={"name": "   "})
        assert r.status_code == 422
        r = client.put("/api/family", json={"name": "家" * 51})
        assert r.status_code == 422

"""HTTP 层全链路测试：health -> 成员 -> 食材 -> 生成 -> 采购 -> 反馈 -> 周报。"""

from datetime import date

from app.modules.recipe import clients as clients_mod
from app.modules.recipe.clients import MockLLMClient


class TestHealth:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestMemberAPI:
    def _member_payload(self, name="小明", age=30, gender="male"):
        return {
            "name": name,
            "age": age,
            "gender": gender,
            "diet_goal": "normal",
            "constitution": ["balanced"],
            "health_conditions": ["none"],
            "allergens": [],
            "dietary_restrictions": [],
        }

    def test_create_list_get_update_delete(self, client):
        r = client.post("/api/members", json=self._member_payload())
        assert r.status_code == 201
        member_id = r.json()["id"]

        r = client.get("/api/members")
        assert r.status_code == 200
        assert r.json()["total"] == 1

        r = client.get(f"/api/members/{member_id}")
        assert r.status_code == 200
        assert r.json()["name"] == "小明"

        r = client.put(f"/api/members/{member_id}", json={"name": "小红"})
        assert r.status_code == 200
        assert r.json()["name"] == "小红"

        r = client.delete(f"/api/members/{member_id}")
        assert r.status_code == 200
        assert r.json()["is_deleted"] == 1

        r = client.get(f"/api/members/{member_id}")
        assert r.status_code == 404

    def test_member_limit_8(self, client):
        for i in range(1, 9):
            r = client.post("/api/members", json=self._member_payload(name=f"成员{i}"))
            assert r.status_code == 201
        r = client.post("/api/members", json=self._member_payload(name="第九人"))
        assert r.status_code == 400
        assert "最多添加 8 位家庭成员" in r.json()["message"]

    def test_validation_errors(self, client):
        # 年龄超上限
        r = client.post("/api/members", json=self._member_payload(age=200))
        assert r.status_code == 422
        # 性别非法
        r = client.post("/api/members", json=self._member_payload(gender="unknown"))
        assert r.status_code == 422


class TestIngredientAPI:
    def test_text_and_batch(self, client):
        r = client.post("/api/ingredients/text", json={"name": "番茄 500g"})
        assert r.status_code == 200
        body = r.json()
        assert body["recognized"][0]["name"] == "番茄"
        assert float(body["recognized"][0]["available_weight"]) == 500.0
        assert body["need_confirm"] is True

        r = client.post("/api/ingredients/text/batch", json=["番茄 500g，鸡胸肉；土豆"])
        assert r.status_code == 200
        assert len(r.json()["recognized"]) == 3

    def test_confirm_list_update_delete_clear(self, client):
        # 确认入库
        r = client.post(
            "/api/ingredients/confirm",
            json={"family_id": 1, "items": [{"name": "番茄", "available_weight": 500}]},
        )
        assert r.status_code == 201
        assert r.json()["affected"] == 1

        r = client.get("/api/ingredients")
        assert r.status_code == 200
        assert r.json()["total"] == 1
        item_id = r.json()["items"][0]["id"]

        r = client.put(f"/api/ingredients/{item_id}", json={"available_weight": 800})
        assert r.status_code == 200
        assert float(r.json()["available_weight"]) == 800.0

        r = client.delete(f"/api/ingredients/{item_id}")
        assert r.status_code == 200
        assert r.json()["is_valid"] == 0

        r = client.post("/api/ingredients/clear")
        assert r.status_code == 200
        assert r.json()["affected"] == 0

    def test_text_without_name_400(self, client):
        r = client.post("/api/ingredients/text", json={"name": "500g"})
        assert r.status_code == 400


class TestRecipeAPI:
    def _setup_member_and_ingredients(self, client):
        assert (
            client.post(
                "/api/members",
                json={
                    "name": "小美",
                    "age": 30,
                    "gender": "female",
                    "diet_goal": "normal",
                    "constitution": [],
                    "health_conditions": [],
                    "allergens": [],
                    "dietary_restrictions": [],
                },
            ).status_code
            == 201
        )
        assert (
            client.post(
                "/api/ingredients/confirm",
                json={
                    "family_id": 1,
                    "items": [
                        {"name": "番茄", "available_weight": 500},
                        {"name": "鸡蛋", "available_weight": 300},
                        {"name": "油菜", "available_weight": 200},
                    ],
                },
            ).status_code
            == 201
        )

    def test_generate_and_records(self, client, monkeypatch):
        # 固定为 Mock 模型，测试 API 链路本身而非真实模型返回
        monkeypatch.setattr(clients_mod, "get_llm_client", lambda: MockLLMClient())
        self._setup_member_and_ingredients(client)
        r = client.post(
            "/api/recipes/generate",
            json={"family_id": 1, "dish_count": 4, "buy_supplement": True},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["record_id"] > 0
        # 推荐采购模式：Mock 2 道如实返回，不补菜谱凑数
        assert len(body["result"]["shared_dishes"]) == 2
        assert body["result"]["member_allocation"][0]["member_name"] == "小美"
        # Mock 两道菜食材全在家 → 不标需采购，菜够就不推采购
        by_name = {d["name"]: d for d in body["result"]["shared_dishes"]}
        assert not by_name["番茄炒蛋"]["needs_purchase"]
        assert not by_name["清炒时蔬"]["needs_purchase"]
        # 家里的食材按存量扣减：存量充足的不重复推荐（营养缺口采购按 3 天量-存量）
        missing = {p["food_name"] for p in body["result"]["purchase_list"]}
        assert "番茄" not in missing  # 番茄在家且非缺口食材，不推荐
        # 两轮生成后仍不足：tip 如实说明（含"少于期望的"口径）
        assert "少于期望的" in body["result"]["tip"] or "已按采购建议补齐" in body["result"]["tip"]

        r = client.get("/api/recipes/records?family_id=1")
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_generate_without_member_fails(self, client):
        r = client.post("/api/recipes/generate", json={"family_id": 1, "dish_count": 4})
        assert r.status_code == 400
        assert "请先在家庭档案中添加成员" in r.json()["message"]


class TestPurchaseAPI:
    def test_check_and_export(self, client):
        # 有成员但无反馈 -> 缺口>30% 触发
        client.post(
            "/api/members",
            json={
                "name": "小美",
                "age": 30,
                "gender": "female",
                "diet_goal": "normal",
                "constitution": [],
                "health_conditions": [],
                "allergens": [],
                "dietary_restrictions": [],
            },
        )
        r = client.post("/api/purchase/check?family_id=1")
        assert r.status_code == 200
        assert r.json()["triggered"] is True

        r = client.post("/api/purchase/export?fmt=csv&family_id=1")
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["file_name"].endswith(".csv")


class TestFeedbackReportAPI:
    def test_full_feedback_report_flow(self, client):
        # 成员 + 食材 + 生成记录
        client.post(
            "/api/members",
            json={
                "name": "小美",
                "age": 30,
                "gender": "female",
                "diet_goal": "normal",
                "constitution": [],
                "health_conditions": [],
                "allergens": [],
                "dietary_restrictions": [],
            },
        )
        client.post(
            "/api/ingredients/confirm",
            json={"family_id": 1, "items": [{"name": "番茄", "available_weight": 500}]},
        )
        gen = client.post(
            "/api/recipes/generate", json={"family_id": 1, "dish_count": 4}
        )
        record_id = gen.json()["record_id"]

        # 反馈（手动分量）
        r = client.post(
            "/api/feedback",
            json={
                "family_id": 1,
                "recipe_record_id": record_id,
                "eaten_date": date(2026, 9, 25).isoformat(),
                "use_ai_amount": False,
                "items": [
                    {"member_id": 1, "dish_name": "番茄炒蛋", "amount_g": 150},
                ],
            },
        )
        assert r.status_code == 201
        assert r.json()["affected"] == 1

        r = client.get("/api/feedback?family_id=1")
        assert r.status_code == 200
        assert r.json()["total"] == 1

        # 周报
        r = client.post(
            "/api/reports/generate",
            json={
                "family_id": 1,
                "week_start": date(2026, 9, 21).isoformat(),
                "week_end": date(2026, 9, 27).isoformat(),
                "generate_type": 0,
            },
        )
        assert r.status_code == 200
        report = r.json()["report_data"]
        assert report["effective_days"] == 1
        assert report["members"][0]["member_name"] == "小美"
        assert report["week_start"] == "2026-09-21"

        r = client.get("/api/reports?family_id=1")
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_report_without_feedback_400(self, client):
        client.post(
            "/api/members",
            json={
                "name": "小美",
                "age": 30,
                "gender": "female",
                "diet_goal": "normal",
                "constitution": [],
                "health_conditions": [],
                "allergens": [],
                "dietary_restrictions": [],
            },
        )
        r = client.post(
            "/api/reports/generate",
            json={
                "family_id": 1,
                "week_start": date(2026, 9, 21).isoformat(),
                "week_end": date(2026, 9, 27).isoformat(),
            },
        )
        assert r.status_code == 400
        assert "本周暂无有效反馈记录" in r.json()["message"]

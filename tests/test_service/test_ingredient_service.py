"""食材录入服务测试：文字解析 / 批量识别 / 确认入库 / 管理。"""
from decimal import Decimal

import pytest

from app.core.exceptions import IngredientNotFound
from app.modules.ingredient.schemas import IngredientConfirmIn, IngredientCreate
from app.modules.ingredient.service import IngredientService


class TestParseTextLine:
    def test_with_weight(self, db):
        svc = IngredientService(db)
        item = svc.parse_text_line("番茄 500g")
        assert item.name == "番茄"
        assert item.available_weight == Decimal("500")
        assert item.weight_unit == "g"

    def test_without_weight(self, db):
        svc = IngredientService(db)
        item = svc.parse_text_line("鸡胸肉")
        assert item.name == "鸡胸肉"
        assert item.available_weight is None

    def test_pure_weight_raises(self, db):
        svc = IngredientService(db)
        with pytest.raises(ValueError):
            svc.parse_text_line("500g")


class TestRecognizeByText:
    def test_multiple_foods_in_one_line(self, db):
        svc = IngredientService(db)
        items = svc.recognize_by_text(["番茄 500g，鸡胸肉；土豆"])
        assert len(items) == 3
        assert {i.name for i in items} == {"番茄", "鸡胸肉", "土豆"}

    def test_empty_lines_skipped(self, db):
        svc = IngredientService(db)
        items = svc.recognize_by_text(["", "   ", "鸡蛋"])
        assert len(items) == 1
        assert items[0].name == "鸡蛋"



class TestConfirmAndSave:
    def test_confirm_saves_items(self, db):
        svc = IngredientService(db)
        payload = IngredientConfirmIn(
            family_id=1,
            items=[
                IngredientCreate(name="番茄", available_weight=Decimal("500")),
                IngredientCreate(name="鸡胸肉"),
            ],
        )
        count = svc.confirm_and_save(payload)
        assert count == 2
        saved = svc.list_ingredients()
        assert len(saved) == 2


class TestIngredientManagement:
    def _save_two(self, db) -> list:
        svc = IngredientService(db)
        payload = IngredientConfirmIn(
            family_id=1,
            items=[
                IngredientCreate(name="番茄", available_weight=Decimal("500")),
                IngredientCreate(name="鸡胸肉"),
            ],
        )
        svc.confirm_and_save(payload)
        return svc.list_ingredients()

    def test_update(self, db):
        svc = IngredientService(db)
        items = self._save_two(db)
        updated = svc.update_ingredient(items[0].id, available_weight=Decimal("800"))
        assert updated.available_weight == Decimal("800")

    def test_delete_marks_invalid(self, db):
        svc = IngredientService(db)
        items = self._save_two(db)
        deleted = svc.delete_ingredient(items[0].id)
        assert deleted.is_valid == 0
        assert len(svc.list_ingredients()) == 1
        with pytest.raises(IngredientNotFound):
            svc.get_ingredient(items[0].id)

    def test_clear_all(self, db):
        svc = IngredientService(db)
        self._save_two(db)
        affected = svc.clear_ingredients()
        assert affected == 2
        assert svc.list_ingredients() == []
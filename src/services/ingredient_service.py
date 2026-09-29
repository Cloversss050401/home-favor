"""食材录入业务：三种录入方式（拍照/文字/方言语音）+ 人工确认兜底。

对齐硬性业务规则第 1 条：
- 名称必填、重量选填；“番茄 500g”自动拆分
- 无重量：仅标记“家中已有”，不做重量扣减；一期不做自动消耗扣减
- 所有识别结果必须经用户人工确认后才进入业务流程
- 确认后的列表入库；帧数据可改重量、可删错补漏
"""
import re
from decimal import Decimal

from sqlalchemy.orm import Session

from src.exceptions.business_exception import IngredientNotFound
from src.models.ingredient_model import HouseholdIngredient
from src.repository.family_repo import FamilyRepo
from src.repository.ingredient_repo import IngredientRepo
from src.schemas.ingredient_schema import (
    IngredientConfirmIn,
    IngredientCreate,
    IngredientRecognizeItem,
)
from src.utils import weight_parser

# ASR/批量文本按分隔符切分（中英文逗号/顿号/句号/竖线/换行）
_ENTRY_SEPARATOR = re.compile(r"[，,、。；;|\n]+")


class IngredientService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.family_repo = FamilyRepo(db)
        self.ingredient_repo = IngredientRepo(db)

    # ---------- 文字输入 ----------
    def parse_text_line(self, text: str) -> IngredientRecognizeItem:
        """解析文本行：'番茄 500g' 或 '鸡胸肉'，返回待确认食材。"""
        parsed = weight_parser.parse_weight(text)
        if not parsed.name:
            # 只有重量没有名称：丢弃重量，视为名称缺失
            raise ValueError("未识别到食材名称，请重新输入")
        weight = (
            Decimal(str(parsed.available_weight))
            if parsed.available_weight is not None
            else None
        )
        return IngredientRecognizeItem(
            name=parsed.name,
            available_weight=weight,
            weight_unit="g",
        )

    def recognize_by_text(self, lines: list[str]) -> list[IngredientRecognizeItem]:
        """文字批量录入：每行（含内部标点分隔）解析为多个食材，返回待确认列表。

        ASR/粘贴文本可能一条消息含多个食材（如“番茄 500g，鸡胸肉”），
        按中英文标点切分后逐段解析。
        """
        items: list[IngredientRecognizeItem] = []
        for line in lines:
            if not line or not line.strip():
                continue
            for segment in _ENTRY_SEPARATOR.split(line):
                segment = segment.strip()
                if not segment:
                    continue
                items.append(self.parse_text_line(segment))
        return items

    # ---------- 拍照识别（多模态） ----------
    def recognize_by_image(self, image_path: str) -> list[IngredientRecognizeItem]:
        """拍照识别：委托 multimodal_client，返回待确认列表。

        密钥未就绪时抛出 ExternalClientUnavailable，由 controller 转 503。
        识别结果一律走人工确认。
        """
        from src.clients.multimodal_client import get_multimodal_client

        client = get_multimodal_client()
        return client.recognize_ingredients(image_path)

    # ---------- 武汉方言语音（ASR） ----------
    def recognize_by_speech(
        self, audio_path: str | None = None, audio_text: str | None = None
    ) -> list[IngredientRecognizeItem]:
        """语音录入：ASR 转文字后按文本解析；支持直接传入转写文本（测试/降级）。

        武汉话场景一期以普通话兜底；识别结果走人工确认。
        """
        if audio_text is None:
            from src.clients.asr_client import get_asr_client

            client = get_asr_client()
            audio_text = client.speech_to_text(audio_path or "")
        if not audio_text or not audio_text.strip():
            return []
        return self.recognize_by_text([audio_text])

    # ---------- 确认入库 ----------
    def confirm_and_save(self, payload: IngredientConfirmIn) -> int:
        """人工确认后批量入库：用户可删错补漏、修改重量。

        同一名称存在多条时保留用户提交的多条（不自动合并），
        列表展示由前端按名称合并；一期不做重量自动扣减。
        """
        fid = payload.family_id
        self.family_repo.get_or_create_default()  # 确保家庭存在
        items = [
            HouseholdIngredient(
                family_id=fid,
                name=it.name,
                available_weight=it.available_weight,
                weight_unit=it.weight_unit,
            )
            for it in payload.items
        ]
        return self.ingredient_repo.create_many(items)

    # ---------- 查询 / 管理 ----------
    def list_ingredients(self, family_id: int | None = None) -> list[HouseholdIngredient]:
        items = self.ingredient_repo.list_valid(family_id or 1)
        return items

    def get_ingredient(self, item_id: int) -> HouseholdIngredient:
        item = self.ingredient_repo.get(item_id)
        if item is None or item.is_valid != 1:
            raise IngredientNotFound()
        return item

    def update_ingredient(
        self, item_id: int, name: str | None = None, available_weight=None, weight_unit: str | None = None
    ) -> HouseholdIngredient:
        item = self.get_ingredient(item_id)
        if name is not None:
            item.name = name
        if available_weight is not None:
            item.available_weight = available_weight
        if weight_unit is not None:
            item.weight_unit = weight_unit
        return self.ingredient_repo.update(item)

    def delete_ingredient(self, item_id: int) -> HouseholdIngredient:
        """删除食材：标记失效（is_valid=0），不使用物理删除。"""
        item = self.get_ingredient(item_id)
        return self.ingredient_repo.soft_delete(item)

    def clear_ingredients(self, family_id: int | None = None) -> int:
        """清空全家食材：批量标记失效。"""
        return self.ingredient_repo.invalidate_family_items(family_id or 1)
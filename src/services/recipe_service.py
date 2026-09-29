"""AI 食谱生成业务：档案+食材组装 Prompt、强制 JSON、30s 超时、本地二次校验。

对齐硬性业务规则第 5 条：
- 调用大模型 API 生成，强制输出 JSON 结构
- 营养计算不信任模型：service 层用食物成分表/DRIs 本地二次校验修正
- 输入快照 + 三层结果落 recipe_generation_record（供采购/反馈/周报）
- 超时 30s，超时/解析失败有降级提示
"""
import json
from typing import Any

from sqlalchemy.orm import Session

from src.config.constants import (
    DEFAULT_PROMPT_MAX_CHARS,
    MIN_MAIN_DISHES,
)
from src.exceptions.business_exception import (
    BusinessException,
    LLMJsonParseError,
    LLMTimeoutError,
)
from src.models.recipe_record_model import RecipeGenerationRecord
from src.repository.family_repo import FamilyRepo
from src.repository.ingredient_repo import IngredientRepo
from src.repository.member_repo import MemberRepo
from src.repository.recipe_record_repo import RecipeRecordRepo
from src.schemas.recipe_schema import (
    MemberAllocation,
    PurchaseItem,
    RecipeGenerateRequest,
    RecipeGenerateResult,
    SharedDish,
)
from src.services.nutrition_service import NutritionService
from src.utils.synonym_util import canonical


class RecipeService:
    """AI 食谱生成引擎（依赖注入 DB Session；外部调用走 clients 延迟注入）。"""

    def __init__(
        self,
        db: Session,
        llm_client=None,
    ) -> None:
        self.db = db
        self.family_repo = FamilyRepo(db)
        self.member_repo = MemberRepo(db)
        self.ingredient_repo = IngredientRepo(db)
        self.record_repo = RecipeRecordRepo(db)
        self.nutrition = NutritionService(db)
        self._llm_client = llm_client

    @property
    def llm_client(self):
        if self._llm_client is None:
            from src.clients.llm_client import get_llm_client

            self._llm_client = get_llm_client()
        return self._llm_client

    # ---------- Prompt 组装 ----------
    def build_prompt(self, family_id: int, dish_count: int) -> tuple[str, dict]:
        """组装 Prompt + 输入快照（快照随记录落库）。"""
        members = self.member_repo.list_active(family_id)
        ingredients = self.ingredient_repo.list_valid(family_id)
        if not members:
            raise BusinessException(
                code="EMPTY_FAMILY_MEMBER",
                message="请先在家庭档案中添加成员后再生成食谱",
                status_code=400,
            )

        member_lines = []
        for m in members:
            member_lines.append(
                {
                    "member_id": m.id,
                    "name": m.name,
                    "age": float(m.age),
                    "gender": m.gender,
                    "diet_goal": m.diet_goal,
                    "constitution": m.constitution,
                    "health": m.health_conditions,
                    "allergens": m.allergens,
                    "restrictions": m.dietary_restrictions,
                }
            )
        ingredient_lines = []
        for ing in ingredients:
            entry = {
                "name": ing.name,
                "available_weight_g": (
                    float(ing.available_weight)
                    if ing.available_weight is not None
                    else None
                ),
            }
            ingredient_lines.append(entry)

        snapshot = {
            "members": member_lines,
            "ingredients": ingredient_lines,
            "dish_count": dish_count,
        }
        prompt = (
            "你是一位家庭营养师。请根据以下家庭成员档案与家中现有食材，"
            f"生成全家共享的一桌菜品（{dish_count} 道，其中主菜至少 {MIN_MAIN_DISHES} 道）。\n"
            "严格要求：\n"
            "1. 只使用家中现有食材（名称匹配即可，不要求严格按重量）；不足时可补充建议采购，不要臆造食材。\n"
            "2. 避开所有成员的过敏原与忌口；考虑饮食目标（减脂/增肌/孕妈/婴幼儿/老年/均衡）。\n"
            "3. 输出必须是合法 JSON（不要 markdown 代码块），结构如下：\n"
            '{"shared_dishes":[{"name":"菜名","category":"main|staple|soup|dessert",'
            '"is_main_dish":true,"main_ingredients":["食材名"],"cooking_method":"做法",'
            '"estimated_servings":4,"note":"备注"}],'
            '"member_allocation":[{"member_id":1,"member_name":"姓名","dishes":'
            '[{"dish_name":"菜名","amount_g":150}],"intake_advantage":["优点"],'
            '"nutrition_gap":[]}]}\n'
            "4. member_allocation 必须覆盖每一位成员；每家每人给出每道菜建议分量（克）。\n"
            "5. 不要输出采购清单，采购由后端计算。\n"
            f"成员档案：{json.dumps(member_lines, ensure_ascii=False)}\n"
            f"家中食材：{json.dumps(ingredient_lines, ensure_ascii=False)}"
        )
        return prompt[:DEFAULT_PROMPT_MAX_CHARS], snapshot

    # ---------- JSON 解析 ----------
    @staticmethod
    def parse_llm_json(text: str) -> dict[str, Any]:
        """解析大模型 JSON（兼容外层代码块）。"""
        if not text or not text.strip():
            raise LLMJsonParseError()
        content = text.strip()
        # 去除 markdown 代码块包裹
        if content.startswith("```"):
            lines = content.splitlines()
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            content = "\n".join(lines).strip()
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            # 尝试截取首个 { 到最后一个 }
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise LLMJsonParseError() from exc
            try:
                data = json.loads(content[start : end + 1])
            except json.JSONDecodeError as exc2:
                raise LLMJsonParseError() from exc2
        if not isinstance(data, dict):
            raise LLMJsonParseError()
        return data

    # ---------- 结果规整 ----------
    @staticmethod
    def _normalize_dishes(raw: Any) -> list[SharedDish]:
        dishes: list[SharedDish] = []
        for item in raw or []:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            dishes.append(
                SharedDish(
                    name=str(item["name"]),
                    category=str(item.get("category", "main")),
                    is_main_dish=bool(item.get("is_main_dish", True)),
                    main_ingredients=[str(x) for x in item.get("main_ingredients", [])],
                    cooking_method=str(item.get("cooking_method", "")),
                    estimated_servings=int(item.get("estimated_servings", 1) or 1),
                    note=str(item.get("note", "")),
                )
            )
        return dishes

    def _normalize_allocations(
        self, raw: Any
    ) -> list[dict]:
        """规整 member_allocation，并逐成员做本地营养二次校验。"""
        result: list[dict] = []
        allowed_ids = [m.id for m in self.member_repo.list_active(self.current_family_id)]
        for item in raw or []:
            if not isinstance(item, dict):
                continue
            member_id = int(item.get("member_id", 0))
            if member_id not in allowed_ids:
                continue
            member = next(
                (m for m in self.member_repo.list_active(self.current_family_id) if m.id == member_id),
                None,
            )
            if member is None:
                continue
            dishes = []
            for d in item.get("dishes", []) or []:
                if isinstance(d, dict) and d.get("dish_name"):
                    dishes.append(
                        {
                            "dish_name": str(d["dish_name"]),
                            "amount_g": float(d.get("amount_g", 0) or 0),
                        }
                    )
            allocation = {
                "member_id": member_id,
                "member_name": str(item.get("member_name", member.name)),
                "dishes": dishes,
                "intake_advantage": [str(x) for x in item.get("intake_advantage", []) or []],
                "nutrition_gap": [],
            }
            # 本地二次校验：覆写缺口与摄入
            allocation = self.nutrition.local_verify_allocation(member, allocation)
            result.append(allocation)
        return result

    # ---------- 主流程 ----------
    def generate(self, payload: RecipeGenerateRequest) -> RecipeGenerateResult:
        self.current_family_id = payload.family_id
        prompt, snapshot = self.build_prompt(payload.family_id, payload.dish_count)
        self.last_snapshot = snapshot

        try:
            raw_text = self.llm_client.generate_text(prompt)
        except LLMTimeoutError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMTimeoutError() from exc

        data = self.parse_llm_json(raw_text)
        shared_dishes = self._normalize_dishes(data.get("shared_dishes"))
        member_allocation = self._normalize_allocations(data.get("member_allocation"))

        # 主菜数量兜底：不足 2 道时由采购服务判定触发采购
        main_count = sum(1 for d in shared_dishes if d.is_main_dish)

        result = RecipeGenerateResult(
            shared_dishes=shared_dishes,
            member_allocation=[
                MemberAllocation(**alloc) for alloc in member_allocation
            ],
            purchase_list=[],
        )
        # 供 purchase 判定使用（记录主菜数量）
        self._last_main_count = main_count
        return result

    def persist(
        self,
        family_id: int,
        result: RecipeGenerateResult,
        snapshot: dict | None = None,
        purchase_items: list[PurchaseItem] | None = None,
    ) -> RecipeGenerationRecord:
        """生成结果 + 采购清单落库。snapshot 缺省用最近一次生成输入快照。"""
        use_snapshot = snapshot or getattr(self, "last_snapshot", {})
        record = RecipeGenerationRecord(
            family_id=family_id,
            input_snapshot=use_snapshot,
            shared_dishes=[d.model_dump() for d in result.shared_dishes],
            member_allocation=[a.model_dump() for a in result.member_allocation],
            purchase_list=(
                [
                    # model_dump(mode="json")：将 Decimal 等转为可 JSON 序列化类型
                    p.model_dump(mode="json")
                    for p in purchase_items
                ]
                if purchase_items
                else []
            ),
        )
        return self.record_repo.create(record)

    def list_records(
        self, family_id: int, limit: int = 50
    ) -> list[RecipeGenerationRecord]:
        """生成历史（按时间倒序）。"""
        return self.record_repo.list_by_family(family_id, limit=limit)

    def get_record(self, record_id: int) -> RecipeGenerationRecord | None:
        """按 ID 获取单条生成记录。"""
        return self.record_repo.get(record_id)

    @staticmethod
    def canonical_ingredients(ingredients: list[str]) -> list[str]:
        """同义词归一（供过滤使用）。"""
        return [canonical(x) for x in ingredients]
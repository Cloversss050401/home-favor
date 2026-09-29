"""AI 食谱生成业务：档案+食材组装 Prompt、强制 JSON、30s 超时、本地二次校验。

对齐硬性业务规则第 5 条：
- 调用大模型 API 生成，强制输出 JSON 结构
- 营养计算不信任模型：service 层用食物成分表/DRIs 本地二次校验修正
- 输入快照 + 三层结果落 recipe_generation_record（供采购/反馈/周报）
- 超时 30s，超时/解析失败有降级提示

双模式（对齐问题文档《期望 4 道只出 2 道》的改造）：
- buy_supplement=False：仅使用家中现有食材，数量不足时返回实际数量 + tip 提示；
- buy_supplement=True：允许菜品使用家中没有的食材（缺料自动汇总为采购清单），
  数量不足时如实返回，不补菜谱、不硬凑重复菜。
"""

import json
import re
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import (
    BABY_FORBIDDEN_KEYWORDS,
    is_seasoning,
    DEFAULT_PROMPT_MAX_CHARS,
    DIETARY_NEED_LABEL_CN,
    MEAL_ENERGY_SHARE,
    MEAL_TYPE_LABEL_CN,
    MIN_MAIN_DISHES,
    PURCHASE_P1,
)
from app.core.exceptions import (
    BusinessException,
    LLMJsonParseError,
    LLMTimeoutError,
)
from app.modules.recipe.models import RecipeGenerationRecord
from app.modules.family_member.repository import FamilyRepo
from app.modules.ingredient.repository import IngredientRepo
from app.modules.family_member.repository import MemberRepo
from app.modules.recipe.repository import RecipeRecordRepo
from app.modules.recipe.schemas import (
    MemberAllocation,
    RecipeGenerateRequest,
    RecipeGenerateResult,
    SharedDish,
)
from app.modules.shopping_list.schemas import PurchaseItem
from app.modules.nutrition.service import NutritionService, gap_foods_for
from app.common.utils import canonical


def _main_overlap(a: set[str], b: set[str]) -> float:
    """两道菜主料重合率：交集 / 较少主料数。"""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / min(len(a), len(b))



# 内置菜谱库已下线（2026-09-28）：菜不够按"补食材不补菜谱"原则，由模型如实出菜 + 缺料采购清单。


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
            from app.modules.recipe.clients import get_llm_client

            self._llm_client = get_llm_client()
        return self._llm_client

    # ---------- Prompt 组装 ----------
    def build_prompt(
        self, family_id: int, dish_count: int, buy_supplement: bool = True,
        meal_type: str = "", extra_ingredients: list[str] | None = None,
        exclude_dishes: list[str] | None = None,
        gap_mission: list[str] | None = None,
        strict_mode: bool = True,
    ) -> tuple[str, dict]:
        """组装 Prompt + 输入快照（快照随记录落库）。

        buy_supplement=False 时强制只用库存食材并如实返回数量；
        True 时允许补充建议采购的食材以凑满期望数量。
        """
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
            targets = self.nutrition.member_targets(m)
            member_lines.append(
                {
                    "member_id": m.id,
                    "name": m.name,
                    "role": m.role,
                    "age": float(m.age),
                    "gender": m.gender,
                    "height_cm": float(m.height_cm) if m.height_cm else None,
                    "weight_kg": float(m.weight_kg) if m.weight_kg else None,
                    "activity": m.activity or "light",
                    "diet_goal": m.diet_goal,
                    "dietary_needs": m.dietary_needs or [],
                    "meal_energy_kcal": float(
                        targets["energy_kcal"]
                        * Decimal(str(MEAL_ENERGY_SHARE.get(meal_type, 1.0)))
                    ),
                    "daily_energy_kcal": float(targets["energy_kcal"]),
                    "daily_protein_g": float(targets["protein_g"]),
                    "daily_rni": {
                        k: (float(v) if v is not None else None)
                        for k, v in targets.items()
                        if k not in ("energy_kcal", "protein_g")
                    },
                    "constitution": m.constitution,
                    "health": m.health_conditions,
                    "allergens": m.allergens,
                    "restrictions": m.dietary_restrictions,
                    "avoid": m.avoid,
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
        # 两轮生成：把采购建议里的食材视为本轮可用（available_weight_g 留空）
        for name in extra_ingredients or []:
            if not any(ing.name == name for ing in ingredients):
                ingredient_lines.append({"name": name, "available_weight_g": None})

        snapshot = {
            "members": member_lines,
            "ingredients": ingredient_lines,
            "dish_count": dish_count,
            "buy_supplement": buy_supplement,
            "meal_type": meal_type,
        }
        usage_rule = (
            "只使用家中现有食材（名称匹配即可，不要求严格按重量）；"
            "如果食材不足以完成期望数量，请如实输出能做的菜品数量，不要编造食材。"
            if not buy_supplement
            else "优先使用家中现有食材充分组合；允许为菜品搭配家中没有的食材"
            "（务必在 main_ingredients 中列出该菜全部食材，后端会据此生成采购清单）；"
            "若确实无法凑满期望数量，如实输出能做的最多数量，不要硬编凑数。"
        )
        # 两轮生成（补齐食材后）：本轮目标就是补满期望数量，缺料菜也照常输出
        if extra_ingredients:
            usage_rule = (
                f"已按采购计划补齐食材。本轮目标：必须生成 {dish_count} 道完整的菜"
                "（主菜至少 "
                f"{MIN_MAIN_DISHES} 道）；即使某道菜需要家中没有的食材，"
                "也请照常输出并在 main_ingredients 中列出全部食材"
                "（后端会自动补充到采购清单）。不要因为担心缺食材而少输出菜品。"
            )
        prompt = (
            "你是一位家庭营养师。请根据以下家庭成员档案与家中现有食材，"
            f"生成全家共享的一桌菜品（{dish_count} 道，其中主菜至少 {min(MIN_MAIN_DISHES, dish_count)} 道）。\n"
            "严格要求：\n"
            f"1. {usage_rule}\n"
            f"2. 本餐为【{MEAL_TYPE_LABEL_CN.get(meal_type, '不限')}】，"
            "每人的本餐能量目标是全天目标的"
            f"{int(MEAL_ENERGY_SHARE.get(meal_type, 1.0)*100)}%（见 meal_energy_kcal）。"
            "避开所有成员的过敏原与忌口；主目标（均衡/减脂/增肌/孕妈/婴幼儿/老年/素食）"
            "决定能量与蛋白基准，附加需求（素食/低盐/控糖/低脂/补铁/高纤维）叠加约束；"
            "与每人每日能量、蛋白质目标。\n"
            "3. 若有婴幼儿（<3岁）：严禁使用蜂蜜、整粒坚果、生食/刺身、腌制/腊味。\n"
            "4. "
            + (
                "本轮为补菜轮：允许复用已有食材、换不同做法（炒/蒸/炖/煮/凉拌/做汤）出新菜；只要求菜名不与已生成菜品重复，主料可以有部分重叠（同一食材不同做法是合理的）。"
                if (exclude_dishes and not strict_mode)
                else "菜品不得重复：菜名不得相同、主料搭配不得高度雷同（宁缺毋滥，不要为凑数编相似菜）；"
            )
            + "\n"
            "采用覆盖式设计：不必每道菜满足所有成员，一道菜可以只适合部分成员，"
            "但一桌菜合起来必须覆盖每一位成员（每人至少有一两道适合自己吃的菜）。\n"
            "5. 输出必须是合法 JSON（不要 markdown 代码块），结构如下：\n"
            '{"shared_dishes":[{"name":"菜名","category":"main|staple|soup|dessert",'
            '"is_main_dish":true,"main_ingredients":["食材名"],"cooking_method":"做法",'
            '"estimated_servings":4,"note":"备注"}],'
            '"member_allocation":[{"member_id":1,"member_name":"姓名","dishes":'
            '[{"dish_name":"菜名","amount_g":150}],"intake_advantage":["优点"],'
            '"nutrition_gap":[]}]}\n'
            "6. member_allocation 必须覆盖每一位成员；每位成员的分餐只包含适合他/她的菜，"
            "并按每日能量需求分配分量（克）：婴幼儿/儿童分量必须明显小于成人，"
            "增肌/青少年可多于同龄平均，严禁全员同分量。\n"
            "7. 不要输出采购清单，采购由后端计算。\n"
            f"成员档案：{json.dumps(member_lines, ensure_ascii=False)}\n"
            f"家中食材：{json.dumps(ingredient_lines, ensure_ascii=False)}"
            + (
                "\n已生成过的菜品："
                + "、".join(exclude_dishes)
                + "。本轮只需生成【新】的菜品，严禁与以上任何一道重复"
                "（菜名、主料搭配都不得雷同）；也不要输出已生成过的菜。"
                if exclude_dishes
                else ""
            )
        )
        if extra_ingredients:
            prompt += (
                "\n补充说明：以上食材中"
                + "、".join(extra_ingredients)
                + " 已列入本轮采购计划，视为本轮可用的食材。"
                "请尽量生成完整数量的菜品，并确保 member_allocation 覆盖每一位成员"
                "（婴幼儿/素食者也要分到适合的菜）。"
            )
        if gap_mission:
            prompt += (
                "\n营养缺口任务：本轮新菜请优先针对以下缺口设计：\n"
                + "\n".join(gap_mission)
                + "\n（一道菜可以同时补多位成员的缺口；营养优先，做法可灵活）"
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

    # 备注清洗：剔除"分给谁"人群表述，只保留口味/做法注意点
    _NOTE_PEOPLE_PAT = re.compile(
        r"适合[^；;，,。！!]*|可吃|宜食|不宜|宝宝|婴幼儿|幼儿|素食|荤|老人|长辈|儿童|孩子|孕妇|青少年|全家|每人|所有成员|忌口人群"
    )

    @staticmethod
    def _clean_dish_note(note: str) -> str:
        if not note:
            return ""
        parts = re.split(r"[；;，,。！!]", note)
        keep: list[str] = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if RecipeService._NOTE_PEOPLE_PAT.search(p):
                continue
            keep.append(p)
        return "；".join(keep)

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
                    note=RecipeService._clean_dish_note(str(item.get("note", ""))),
                )
            )
        return dishes

    def _normalize_allocations(self, raw: Any, shared_dishes: list[SharedDish] | None = None) -> list[dict]:
        """规整 member_allocation，并逐成员做本地营养二次校验。"""
        result: list[dict] = []
        allowed_ids = [
            m.id for m in self.member_repo.list_active(self.current_family_id)
        ]
        for item in raw or []:
            if not isinstance(item, dict):
                continue
            member_id = int(item.get("member_id", 0))
            if member_id not in allowed_ids:
                continue
            member = next(
                (
                    m
                    for m in self.member_repo.list_active(self.current_family_id)
                    if m.id == member_id
                ),
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
                "intake_advantage": [
                    str(x) for x in item.get("intake_advantage", []) or []
                ],
                "nutrition_gap": [],
            }
            # 本地二次校验：覆写缺口与摄入（按菜谱主料折算）
            allocation = self.nutrition.local_verify_allocation(
                member, allocation, shared_dishes
            )
            result.append(allocation)
        return result

    # ---------- 适合性规则（后端确定性判断，不信任模型） ----------
    @staticmethod
    def dish_suitable(member, dish) -> bool:
        """该菜是否适合该成员：过敏原/忌口/素食/慢病禁忌（硬约束优先）。"""
        ings = [str(x) for x in getattr(dish, "main_ingredients", []) or []]
        text = (dish.name or "") + " " + " ".join(ings)
        allergen_cn = {
            "peanut": {"花生"},
            "egg": {"鸡蛋", "蛋"},
            "shellfish": {"虾", "蟹", "贝", "蛤", "海鲜", "贝壳"},
            "milk": {"牛奶", "奶", "乳", "奶酪", "黄油"},
            "soy": {"大豆", "黄豆", "豆腐", "豆浆", "豆制品"},
            "gluten": {"面粉", "小麦", "麸质", "面包", "面条"},
            "seafood": {"海鲜", "鱼", "虾", "蟹"},
            "nuts": {"花生", "坚果", "核桃", "杏仁", "腰果"},
            "spicy": {"辣椒", "辣"},
            "nightshade": {"番茄", "茄子", "青椒", "辣椒", "土豆"},
        }
        for kw in [*(member.allergens or []), *(member.dietary_restrictions or [])]:
            kw = str(kw or "").strip()
            if not kw:
                continue
            for banned in [kw, *allergen_cn.get(kw, set())]:
                if banned and banned in text:
                    return False
        # 婴幼儿禁食：<3岁或 diet_goal=baby 时，蜂蜜/整粒坚果/生食/腌制一律排除
        is_baby = getattr(member, "diet_goal", "") == "baby" or float(
            getattr(member, "age", 99) or 99
        ) < 3
        if is_baby and any(k in text for k in BABY_FORBIDDEN_KEYWORDS):
            return False
        # 附加需求叠加约束：素食/低盐/控糖/低脂（食材层硬约束）
        needs = getattr(member, "dietary_needs", []) or []
        if "low_sugar" in needs and any(k in text for k in ("糖", "蜂蜜", "蛋糕", "冰淇淋", "甜点")):
            return False
        if "low_fat" in needs and any(k in text for k in ("油炸", "肥肉", "猪油", "黄油", "五花")):
            return False
        # 素食：避开肉/鱼/虾/蟹等
        if getattr(member, "diet_goal", "") == "vegetarian":
            meat_kw = ("鸡", "鸭", "猪", "牛", "羊", "鱼", "虾", "蟹", "肉", "骨", "火腿", "培根", "腊")
            if any(k in text for k in meat_kw):
                return False
        # 慢病禁忌
        health = member.health_conditions or []
        if "gout" in health:
            if any(k in text for k in ("海鲜", "虾", "蟹", "贝", "内脏", "肝", "浓汤", "啤酒")):
                return False
        if "kidney" in health:
            if any(k in text for k in ("海鲜", "虾", "蟹", "内脏", "肝", "浓汤")):
                return False
        if "diabetes" in health:
            if any(k in text for k in ("糖", "蜂蜜", "蛋糕", "冰淇淋", "甜点")):
                return False
        return True

    def _personalize_allocations(
        self, family_id: int, shared_dishes: list[SharedDish], allocations: list[dict],
        meal_type: str = "",
    ) -> list[dict]:
        """分餐个性化：① 只保留适合的菜；② 按本餐能量目标占比缩放分量；③ 注入烹饪提示；④ 重算缺口。"""
        members = {m.id: m for m in self.member_repo.list_active(family_id)}
        dish_by_name = {d.name: d for d in shared_dishes}
        share = MEAL_ENERGY_SHARE.get(meal_type, 1.0)
        energies = {
            mid: float(self.nutrition.daily_energy_kcal(m)) * share
            for mid, m in members.items()
        }
        mean_energy = (sum(energies.values()) / len(energies)) if energies else 1.0

        for alloc in allocations:
            member = members.get(int(alloc.get("member_id", 0)))
            if member is None:
                continue
            kept = []
            for d in alloc.get("dishes", []):
                dish = dish_by_name.get(d.get("dish_name"))
                if dish is not None and self.dish_suitable(member, dish):
                    kept.append(d)
            # 一道适合的都没有时，至少保留一道（避免空分餐）
            if not kept and alloc.get("dishes"):
                kept = [
                    d for d in alloc.get("dishes") if d.get("dish_name") in dish_by_name
                ][:1]
            alloc["dishes"] = kept
            # 按本餐能量目标比例缩放分量（确定性差异，0.4~2.5 倍区间）
            if mean_energy > 0 and kept:
                energy = energies.get(int(alloc.get("member_id", 0)), mean_energy)
                factor = max(0.4, min(2.5, energy / mean_energy))
                for d in kept:
                    amount = max(30.0, (float(d.get("amount_g", 0)) or 100.0) * factor)
                    d["amount_g"] = round(amount / 10) * 10
            # 摄入优点：本地确定性生成（不信任模型编的文案）
            alloc["intake_advantage"] = self._local_intake_advantages(member)
            # 烹饪提示：婴幼儿附加
            is_baby = getattr(member, "diet_goal", "") == "baby" or float(
                getattr(member, "age", 99) or 99
            ) < 3
            if is_baby:
                alloc["cooking_tips"] = ["低盐少油、软烂好嚼", "食材去骨切碎，避免整粒坚果"]
            alloc = self.nutrition.local_verify_allocation(member, alloc, shared_dishes)
        return allocations

    def _ensure_all_members_covered(
        self, family_id: int, shared_dishes: list[SharedDish], allocations: list[dict]
    ) -> list[dict]:
        """保证每位活跃成员都有分餐：缺人补人、空分餐从适合的菜补一道。"""
        members = {m.id: m for m in self.member_repo.list_active(family_id)}
        by_id = {int(a.get("member_id", 0)): a for a in allocations}
        out: list[dict] = []
        for mid, m in members.items():
            alloc = by_id.get(mid)
            if alloc is None:
                alloc = {
                    "member_id": mid,
                    "member_name": m.name,
                    "dishes": [],
                    "intake_advantage": [],
                    "nutrition_gap": [],
                }
                out.append(alloc)
            else:
                out.append(alloc)
            if not alloc.get("dishes") and shared_dishes:
                suit = [d.name for d in shared_dishes if self.dish_suitable(m, d)]
                pick = suit[:2] if suit else [shared_dishes[0].name]
                alloc["dishes"] = [
                    {"dish_name": n, "amount_g": 100.0} for n in pick
                ]
                alloc = self.nutrition.local_verify_allocation(m, alloc, shared_dishes)
        # 兜底 2：每道菜都必须有成员分到（否则做菜反馈"一键全选"匹配不到分餐，勾不上）
        for d in shared_dishes:
            if any(
                x.get("dish_name") == d.name for a in out for x in a.get("dishes", [])
            ):
                continue
            candidates = [m for m in members.values() if self.dish_suitable(m, d)]
            if not candidates:
                candidates = list(members.values())
            target = min(
                candidates,
                key=lambda m: len(
                    next((a.get("dishes", []) for a in out if a.get("member_id") == m.id), [])
                ),
            )
            for a in out:
                if a.get("member_id") == target.id:
                    a.setdefault("dishes", []).append(
                        {"dish_name": d.name, "amount_g": 50.0}
                    )
                    a = self.nutrition.local_verify_allocation(target, a, shared_dishes)
                    break
        return out

    @staticmethod
    def _local_intake_advantages(member) -> list[str]:
        """摄入优点本地生成：按主目标 + 附加需求写确定性文案（不靠大模型）。"""
        adv: list[str] = []
        goal = getattr(member, "diet_goal", "normal")
        needs = getattr(member, "dietary_needs", []) or []
        if goal == "vegetarian":
            adv.append("植物蛋白为主，符合素食习惯")
        if goal == "muscle":
            adv.append("高蛋白搭配，支持增肌")
        if goal == "slim":
            adv.append("控制能量摄入，利于减脂")
        if goal == "baby":
            adv.append("软烂易嚼，适合幼儿消化")
        if goal == "elderly":
            adv.append("易消化高蛋白，适合老年营养")
        if goal == "pregnant":
            adv.append("满足孕妈营养需求（能量+300千卡）")
        if "low_salt" in needs:
            adv.append("低盐烹调，保护心血管")
        if "low_sugar" in needs:
            adv.append("控糖友好，少精制糖")
        if "low_fat" in needs:
            adv.append("低脂烹饪，减少油脂")
        if "iron_supp" in needs:
            adv.append("搭配富铁食材，帮助补铁")
        if "high_fiber" in needs:
            adv.append("高纤维搭配，促进肠道健康")
        if not adv:
            adv.append("营养均衡，符合全家需求")
        return adv

    @staticmethod
    def _merge_allocations(old: list[dict], new: list[dict]) -> list[dict]:
        """合并两轮分餐：同一成员 dishes 去重合并，其余字段以后一轮为准。"""
        merged: dict[int, dict] = {}
        for alloc in list(old) + list(new):
            mid = int(alloc.get("member_id", 0))
            if mid in merged:
                seen = {d.get("dish_name") for d in merged[mid].get("dishes", [])}
                for d in alloc.get("dishes", []):
                    if d.get("dish_name") not in seen:
                        merged[mid].setdefault("dishes", []).append(d)
            else:
                merged[mid] = dict(alloc)
        return list(merged.values())

    def _fallback_allocations(
        self, family_id: int, dishes: list[SharedDish]
    ) -> list[dict]:
        """模型未返回成员分餐时的本地兜底：每位活跃成员均分各菜品。"""
        allocations: list[dict] = []
        for member in self.member_repo.list_active(family_id):
            dish_rows = [
                {
                    "dish_name": d.name,
                    "amount_g": 150.0 if d.is_main_dish else 100.0,
                }
                for d in dishes
            ]
            allocation = {
                "member_id": member.id,
                "member_name": member.name,
                "dishes": dish_rows,
                "intake_advantage": [],
                "nutrition_gap": [],
            }
            allocations.append(
                self.nutrition.local_verify_allocation(member, allocation)
            )
        return allocations

    # ---------- 主流程 ----------
    def generate(self, payload: RecipeGenerateRequest) -> RecipeGenerateResult:
        self.current_family_id = payload.family_id
        prompt, snapshot = self.build_prompt(
            payload.family_id, payload.dish_count, payload.buy_supplement,
            payload.meal_type or "",
        )
        self.last_snapshot = snapshot

        try:
            raw_text = self.llm_client.generate_text(prompt)
        except LLMTimeoutError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMTimeoutError() from exc

        data = self.parse_llm_json(raw_text)
        shared_dishes = self._dedupe_dishes(
            self._normalize_dishes(data.get("shared_dishes"))
        )

        # 严格模式：按库存名单硬过滤非库存食材/菜品（不信任模型自觉）
        dropped_by_filter = 0
        missing_at_gen: set[str] = set()
        if not payload.buy_supplement:
            all_ingredients = {
                canonical(x) for d in shared_dishes for x in d.main_ingredients
            }
            shared_dishes, dropped_by_filter = self._enforce_inventory(
                payload.family_id, shared_dishes
            )
            home_now = {
                canonical(ing.name)
                for ing in self.ingredient_repo.list_valid(payload.family_id)
            }
            missing_at_gen = all_ingredients - home_now

        member_allocation = self._normalize_allocations(
            data.get("member_allocation"), shared_dishes
        )

        # 标记每道菜是否含需采购食材（后端按库存比对，不信任模型标注）
        self._mark_purchase_flags(payload.family_id, shared_dishes)

        # 采购模式：模型可出家中没有食材的菜，缺料统一汇总为采购清单（不补菜谱、不硬凑）
        tip = ""
        supplement_items: list[PurchaseItem] = []
        if payload.buy_supplement:
            supplement_items = self._build_supplement_purchase_items(
                payload.family_id, shared_dishes
            )
            if len(shared_dishes) < payload.dish_count:
                tip = (
                    f"当前最多生成 {len(shared_dishes)} 道菜，少于您期望的 {payload.dish_count} 道"
                    "（不硬凑重复菜）；建议按下方采购清单补齐家中没有的食材，"
                    "买齐后可做的菜会更多。"
                )
        elif len(shared_dishes) < payload.dish_count:
            filter_note = (
                f"其中 {dropped_by_filter} 道因使用了家中没有的食材已被过滤；"
                if dropped_by_filter
                else ""
            )
            missing_display = "、".join(sorted(missing_at_gen))
            tip = (
                f"{filter_note}当前库存食材最多只能生成 {len(shared_dishes)} 道菜，"
                f"少于您期望的 {payload.dish_count} 道。"
            )
            if missing_display:
                tip += f"缺的食材：{missing_display}；补齐这些食材后可做的菜会更多。"
            tip += "可开启\u201c现有食材+推荐采购\u201d模式，由系统补充菜谱并列出采购清单。"

        # ===== 多轮循环（推荐采购）：强制补满期望数量；仅用现有食材模式不做数量要求 =====
        if payload.buy_supplement:
            active_ids = {m.id for m in self.member_repo.list_active(payload.family_id)}
            covered_ids = {
                int(a.get("member_id", 0)) for a in member_allocation
            }
            need_more = (
                len(shared_dishes) < payload.dish_count
                or bool(active_ids - covered_ids)
            )
            if need_more:
                # 补齐食材池：累计缺料采购 + 家庭营养缺口建议食材兜底
                try:
                    from app.modules.shopping_list.service import PurchaseService

                    gap = PurchaseService(self.db)._suggest_foods_for_gap(
                        payload.family_id
                    )
                    gap_names = sorted(gap.keys())
                except Exception:
                    gap_names = []
                extra = sorted({p.food_name for p in supplement_items} | set(gap_names))
            all_names = {d.name for d in shared_dishes}
            max_rounds = 8  # 第一轮之外最多再补 8 轮（强制凑满期望数量）
            strict_rounds = 2  # 前 2 轮严格（营养导向、主料不得雷同）——优先
            relaxed = False  # 是否已切换到放宽兜底（同食材换做法）
            round_no = 0
            while need_more and extra and round_no < max_rounds:
                round_no += 1
                if round_no > strict_rounds:
                    relaxed = True  # 严格轮结束，切放宽兜底
                missing = max(payload.dish_count - len(shared_dishes), 1)
                try:
                    promptN, _ = self.build_prompt(
                        payload.family_id, missing, True,
                        payload.meal_type or "", extra_ingredients=extra,
                        exclude_dishes=all_names,
                        gap_mission=self._build_gap_mission(payload.family_id),
                        strict_mode=not relaxed,
                    )
                    rawN = self.llm_client.generate_text(promptN)
                except Exception:
                    rawN = ""
                if not rawN or not rawN.strip():
                    if not relaxed:
                        relaxed = True
                        continue  # 严格轮拿不到输出，切放宽重试
                    break
                try:
                    dataN = self.parse_llm_json(rawN)
                    dishesN = self._dedupe_dishes(
                        self._normalize_dishes(dataN.get("shared_dishes"))
                    )
                    allocN = self._normalize_allocations(
                        dataN.get("member_allocation"), dishesN
                    )
                    self._mark_purchase_flags(payload.family_id, dishesN)
                    supN = self._build_supplement_purchase_items(
                        payload.family_id, dishesN
                    )
                except Exception:
                    if not relaxed:
                        relaxed = True
                        continue  # 严格轮解析失败，切放宽重试
                    break
                new_dishes = [d for d in dishesN if d.name not in all_names]
                if not new_dishes:
                    if not relaxed:
                        relaxed = True
                        continue  # 严格轮无新菜（主料雷同被过滤），切放宽继续
                    break  # 放宽轮也无新菜，停止避免死循环
                shared_dishes = self._dedupe_dishes(
                    shared_dishes + new_dishes, strict_overlap=not relaxed
                )
                all_names = {d.name for d in shared_dishes}
                known = {p.food_name for p in supplement_items}
                for p in supN:
                    if p.food_name not in known:
                        supplement_items.append(p)
                member_allocation = self._merge_allocations(
                    member_allocation, allocN
                )
                extra = sorted({p.food_name for p in supplement_items})
                need_more = len(shared_dishes) < payload.dish_count
            if len(shared_dishes) >= payload.dish_count:
                tip = (
                    f"已按采购建议补齐食材，共生成 {len(shared_dishes)} 道菜；"
                    "下方采购清单为仍缺的食材。"
                )
            elif shared_dishes:
                tip = (
                    f"已按采购建议尽力补齐，当前共 {len(shared_dishes)} 道菜，"
                    f"仍少于期望的 {payload.dish_count} 道；"
                    "下方采购清单为仍缺的食材，继续补齐后可做的菜会更多。"
                )

        # 本地兜底：模型/Mock 未覆盖任何成员时，按共享菜品为每位成员生成默认分餐，
        # 保证前端"每人食用分配"链路可用（Mock 返回的 member_id 可能与库不一致）。
        if not member_allocation and shared_dishes:
            member_allocation = self._fallback_allocations(
                payload.family_id, shared_dishes
            )

        # 清理成员分餐中引用了被过滤菜品的孤儿条目
        kept_names = {d.name for d in shared_dishes}
        for alloc in member_allocation:
            alloc["dishes"] = [
                d for d in alloc.get("dishes", []) if d.get("dish_name") in kept_names
            ]

        # 分餐个性化（确定性兜底）：只保留适合的菜 + 按能量目标缩放分量 + 重算缺口
        member_allocation = self._personalize_allocations(
            payload.family_id, shared_dishes, member_allocation, payload.meal_type or ""
        )
        # 全员覆盖兜底：缺人补人、空分餐补菜（宝宝等不再出现"暂未分配"）
        member_allocation = self._ensure_all_members_covered(
            payload.family_id, shared_dishes, member_allocation
        )

        # 主菜数量兜底：不足 2 道时由采购服务判定触发采购
        main_count = sum(1 for d in shared_dishes if d.is_main_dish)

        result = RecipeGenerateResult(
            shared_dishes=shared_dishes,
            member_allocation=[
                MemberAllocation(**alloc) for alloc in member_allocation
            ],
            purchase_list=supplement_items,
            tip=tip,
        )
        # 供 purchase 判定使用（记录主菜数量）
        self._last_main_count = main_count
        return result

    def _build_gap_mission(self, family_id: int) -> list[str]:
        """补菜轮任务：每位成员营养缺口 + 对应食材 -> 补菜指令。"""
        lines: list[str] = []
        nuts = (
            "protein", "calcium", "iron", "zinc", "vitamin_a", "vitamin_c"
        )
        for m in self.member_repo.list_active(family_id):
            try:
                gaps = self.nutrition.member_gap(
                    m, {nut: Decimal("0") for nut in nuts}
                )
            except Exception:
                gaps = []
            for g in gaps[:3]:
                if g["status"] == "ok":
                    continue
                foods = gap_foods_for(m, g["nutrient"])[:2]
                if not foods:
                    continue
                lines.append(
                    f"{m.name}缺{g['nutrient_name']}，请用{'、'.join(foods)}做菜补上"
                )
        return lines

    # ---------- 双模式：库存比对 / 菜谱库补齐 ----------
    @staticmethod
    def _dedupe_dishes(
        dishes: list[SharedDish], strict_overlap: bool = True
    ) -> list[SharedDish]:
        """全局去重：strict_overlap=True 菜名或主料高度雷同（≥60%）只留第一道；
        False 只防同名（补菜轮允许同食材换做法）。"""
        kept: list[SharedDish] = []
        for d in dishes:
            name = (d.name or "").strip()
            if any((k.name or "").strip() == name for k in kept):
                continue
            if strict_overlap:
                cur = {canonical(x) for x in d.main_ingredients}
                if cur and any(
                    _main_overlap(cur, {canonical(x) for x in k.main_ingredients}) >= 0.6
                    for k in kept
                    if k.main_ingredients
                ):
                    continue
            kept.append(d)
        return kept

    def _mark_purchase_flags(self, family_id: int, dishes: list[SharedDish]) -> None:
        """按家中库存（canonical 归一）标记每道菜 needs_purchase / purchase_ingredients。"""
        home = {
            canonical(ing.name) for ing in self.ingredient_repo.list_valid(family_id)
        }
        for d in dishes:
            missing = [ing for ing in d.main_ingredients if canonical(ing) not in home]
            d.needs_purchase = bool(missing)
            d.purchase_ingredients = missing

    def _enforce_inventory(
        self, family_id: int, dishes: list[SharedDish]
    ) -> tuple[list[SharedDish], int]:
        """严格模式硬过滤：只保留库存中有的食材；剔除一道库存主料都没有的菜。

        返回 (过滤后菜品, 被剔除菜品数)。不信任模型的自觉，按库存名单强制执行。
        """
        home = {
            canonical(ing.name) for ing in self.ingredient_repo.list_valid(family_id)
        }
        kept: list[SharedDish] = []
        dropped = 0
        for d in dishes:
            valid = [ing for ing in d.main_ingredients if canonical(ing) in home]
            if not valid:
                dropped += 1
                continue
            d.main_ingredients = valid
            kept.append(d)
        return kept, dropped

    @staticmethod
    def _collect_banned_keywords(members) -> set[str]:
        """聚合全部成员的过敏原与忌口关键词（子串匹配用）。

        过敏原支持枚举+自定义输入：枚举先映射到中文食材关键词再参与匹配，
        自定义忌口文本原样参与（如"不吃辣"、"鸡蛋过敏"）。
        """
        allergen_cn = {
            "peanut": {"花生"},
            "egg": {"鸡蛋", "蛋"},
            "shellfish": {"虾", "蟹", "贝", "蛤", "海鲜", "贝壳"},
            "milk": {"牛奶", "奶", "乳", "奶酪", "黄油"},
            "soy": {"大豆", "黄豆", "豆腐", "豆浆", "豆制品"},
            "gluten": {"面粉", "小麦", "麸质", "面包", "面条"},
            "seafood": {"海鲜", "鱼", "虾", "蟹"},
            "nuts": {"花生", "坚果", "核桃", "杏仁", "腰果"},
            "spicy": {"辣椒", "辣"},
            "nightshade": {"番茄", "茄子", "青椒", "辣椒", "土豆"},
        }
        banned: set[str] = set()
        for m in members:
            for item in [*(m.allergens or []), *(m.dietary_restrictions or [])]:
                text = (item or "").strip()
                if not text:
                    continue
                banned.add(text)
                banned.update(allergen_cn.get(text, set()))
        return banned

    def _build_supplement_purchase_items(
        self, family_id: int, dishes: list[SharedDish]
    ) -> list[PurchaseItem]:
        """缺料采购项：汇总全部菜品（模型菜+补充菜）家里没有的食材，按菜谱库量级估算采购克数（调料不进清单）。"""
        home = {
            canonical(ing.name) for ing in self.ingredient_repo.list_valid(family_id)
        }
        need_map: dict[str, float] = {}
        dishes_using: dict[str, set[str]] = {}
        for d in dishes:
            for ing in d.purchase_ingredients:
                key = canonical(ing)
                if key in home or is_seasoning(key):
                    continue
                # 无菜谱库量级参考，按每份 100g 估算采购量
                need_map[key] = need_map.get(key, 0.0) + 100.0
                dishes_using.setdefault(key, set()).add(d.name)
        items: list[PurchaseItem] = []
        for food, amount_g in need_map.items():
            items.append(
                PurchaseItem(
                    priority=PURCHASE_P1,
                    food_name=food,
                    supplement_nutrient=[],
                    suggest_amount_g=amount_g,
                    remark="用于" + "、".join(sorted(dishes_using[food])),
                    target_member="",
                    gap_ratio=0.0,
                )
            )
        return items

    def _extend_allocations(
        self, allocations: list[dict], added: list[SharedDish]
    ) -> list[dict]:
        """将补齐菜品追加进各成员分餐，并重新做本地营养二次校验。"""
        members = {
            m.id: m for m in self.member_repo.list_active(self.current_family_id)
        }
        for alloc in allocations:
            member = members.get(int(alloc.get("member_id", 0)))
            if member is None:
                continue
            existing = {d.get("dish_name") for d in alloc.get("dishes", [])}
            for d in added:
                if d.name in existing:
                    continue
                alloc.setdefault("dishes", []).append(
                    {
                        "dish_name": d.name,
                        "amount_g": 150.0 if d.is_main_dish else 100.0,
                    }
                )
            alloc = self.nutrition.local_verify_allocation(member, alloc, added)
        return allocations

    def persist(
        self,
        family_id: int,
        result: RecipeGenerateResult,
        snapshot: dict | None = None,
        purchase_items: list[PurchaseItem] | None = None,
        meal_type: str = "",
    ) -> RecipeGenerationRecord:
        """生成结果 + 采购清单落库。snapshot 缺省用最近一次生成输入快照。"""
        use_snapshot = snapshot or getattr(self, "last_snapshot", {})
        record = RecipeGenerationRecord(
            family_id=family_id,
            input_snapshot=use_snapshot,
            meal_type=meal_type,
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

    @staticmethod
    def canonical_ingredients(ingredients: list[str]) -> list[str]:
        """同义词归一（供过滤使用）。"""
        return [canonical(x) for x in ingredients]

"""通用工具：日期工具（周统计窗口、日期范围）。"""
from datetime import date, timedelta


def monday_of_week(day: date) -> date:
    """返回所在周的周一（ISO 周起始）。"""
    return day - timedelta(days=day.weekday())


def week_range(day: date) -> tuple[date, date]:
    """返回 (周一, 周日)。"""
    monday = monday_of_week(day)
    return monday, monday + timedelta(days=6)


def date_list(start: date, end: date) -> list[date]:
    """返回闭区间内的日期列表。"""
    days = (end - start).days
    if days < 0:
        return []
    return [start + timedelta(days=i) for i in range(days + 1)]


def effective_days(
    start: date, end: date, recorded_dates: set[date]
) -> list[date]:
    """周报只统计有反馈记录的天数（空白日期不做 AI 估算）。"""
    return [d for d in date_list(start, end) if d in recorded_dates]


def is_weekend(day: date) -> bool:
    """是否周日（自动生成周报的执行判断）。"""
    return day.weekday() == 6


import re
from dataclasses import dataclass

# 数字 + 单位：g/克/kg/千克/ml/毫升
_WEIGHT_PATTERN = re.compile(r"([\d]+(?:\.\d+)?)\s*(g|克|kg|千克|ml|毫升)?", re.IGNORECASE)


@dataclass
class ParsedWeight:
    name: str
    available_weight: float | None  # None=未识别到重量
    weight_unit: str = "g"


_UNIT_TO_G = {
    "g": 1.0,
    "克": 1.0,
    "ml": 1.0,
    "毫升": 1.0,
    "kg": 1000.0,
    "千克": 1000.0,
}


def parse_weight(text: str) -> ParsedWeight:
    """解析 "番茄 500g" / "番茄500克" / "鸡胸肉"。

    规则：
    - 去除首尾空白；
    - 末尾（或全串）匹配数字+单位则拆出重量（换算为 g）；
    - 其余部分为食材名称；
    - 若文本本身就是一个纯数字（例如「500g」），name 返回空串由调用方兜底。
    """
    text = (text or "").strip()
    if not text:
        return ParsedWeight(name="", available_weight=None)

    # 从文本中用正则找出所有重量token
    matches = list(_WEIGHT_PATTERN.finditer(text))
    candidates = []
    for m in matches:
        value_str, unit = m.group(1), (m.group(2) or "g").lower()
        if unit not in _UNIT_TO_G:
            unit = "g"
        candidates.append((m.start(), m.end(), float(value_str) * _UNIT_TO_G[unit]))

    # 取最后一个匹配（食材名称一般在前，重量在后）
    if candidates:
        start, end, weight_g = candidates[-1]
        name = (text[:start] + " " + text[end:]).strip()
        # "500g" 单独成串时 name 为空
        if not name:
            return ParsedWeight(name="", available_weight=round(weight_g, 2))
        return ParsedWeight(name=name, available_weight=round(weight_g, 2))

    return ParsedWeight(name=text, available_weight=None)


def format_weight(weight_g: float) -> str:
    """内部展示用：克数转为可读字符串（>=1000g 显示 kg）。"""
    if weight_g >= 1000:
        return f"{weight_g / 1000:.2f}kg"
    return f"{weight_g:.0f}g"


import json
from functools import lru_cache
from pathlib import Path

# 项目根目录（src 的上一级）
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNONYM_FILE = _PROJECT_ROOT / "resources" / "dict" / "synonyms.json"

_DEFAULT_SYNONYMS: dict[str, list[str]] = {
    "鸡蛋": ["洋鸡蛋", "土鸡蛋", "笨鸡蛋", "草鸡蛋"],
    "番茄": ["西红柿", "圣女果"],
    "土豆": ["马铃薯", "洋芋"],
    "鸡胸肉": ["鸡小胸", "鸡里脊"],
    "猪肉": ["五花肉", "里脊肉"],
    "白菜": ["大白菜", "黄芽白"],
    "油菜": ["上海青", "小油菜", "青菜"],
}


def _load_table() -> dict[str, list[str]]:
    if SYNONYM_FILE.exists():
        try:
            data = json.loads(SYNONYM_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            # 文件损坏时回退默认表
            pass
    return _DEFAULT_SYNONYMS


@lru_cache(maxsize=8)
def _canonical_map() -> dict[str, str]:
    """别名 -> 规范名 映射（含自身）。"""
    table = _load_table()
    mapping: dict[str, str] = {}
    for canonical, aliases in table.items():
        mapping[canonical] = canonical
        for alias in aliases:
            mapping[alias] = canonical
    return mapping


def canonical(name: str) -> str:
    """返回规范名；无映射时原样返回。"""
    name = (name or "").strip()
    if not name:
        return name
    return _canonical_map().get(name, name)


def merge_synonyms(names: list[str]) -> dict[str, int]:
    """合并同义词并返回 {规范名: 出现次数}（供采购清单同类合并使用）。"""
    result: dict[str, int] = {}
    for name in names:
        key = canonical(name)
        result[key] = result.get(key, 0) + 1
    return result


def has_synonym(name: str) -> bool:
    """判断是否存在别名映射。"""
    return name in _canonical_map()



import csv
from pathlib import Path

from openpyxl import Workbook

from app.core.constants import PURCHASE_PRIORITY_ORDER

_EXPORT_DIR = Path(__file__).resolve().parents[2] / "resources" / "exports"
_EXPORT_HEADERS = [
    "优先级",
    "食材名称",
    "补充营养素",
    "建议采购量(g)",
    "备注",
    "优先补齐成员",
    "缺口比例",
]


def _ensure_dir() -> Path:
    _EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    return _EXPORT_DIR


def export_purchase_xlsx(
    items: list[dict], file_name: str = "purchase_list.xlsx"
) -> str:
    """导出采购清单为 xlsx，返回文件绝对路径。

    items 元素字段：priority / food_name / supplement_nutrient / suggest_amount_g / remark
    """
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "采购清单"
    ws.append(_EXPORT_HEADERS)

    for item in sorted(
        items,
        key=lambda x: (
            PURCHASE_PRIORITY_ORDER.index(x.get("priority", "P2")),
            x.get("food_name", ""),
        ),
    ):
        ws.append(
            [
                item.get("priority", "P2"),
                item.get("food_name", ""),
                "/".join(item.get("supplement_nutrient", [])),
                float(item.get("suggest_amount_g", 0)),
                item.get("remark", ""),
                item.get("target_member", ""),
                item.get("gap_ratio", 0),
            ]
        )

    # 列宽基础优化
    for col, width in zip("ABCDEFG", [8, 16, 20, 16, 30, 14, 10], strict=True):
        ws.column_dimensions[col].width = width

    out_path = _ensure_dir() / file_name
    wb.save(out_path)
    return str(out_path)


def export_purchase_csv(items: list[dict], file_name: str = "purchase_list.csv") -> str:
    """导出采购清单为 csv（UTF-8 with BOM，Excel 可直接打开）。"""
    out_path = _ensure_dir() / file_name
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(_EXPORT_HEADERS)
        for item in sorted(
            items,
            key=lambda x: (
                PURCHASE_PRIORITY_ORDER.index(x.get("priority", "P2")),
                x.get("food_name", ""),
            ),
        ):
            writer.writerow(
                [
                    item.get("priority", "P2"),
                    item.get("food_name", ""),
                    "/".join(item.get("supplement_nutrient", [])),
                    float(item.get("suggest_amount_g", 0)),
                    item.get("remark", ""),
                    item.get("target_member", ""),
                    item.get("gap_ratio", 0),
                ]
            )
    return str(out_path)


def export_report_xlsx(report_data: dict, file_name: str = "weekly_report.xlsx") -> str:
    """导出周度营养报告为 xlsx（前端周报表格 + 前端契约对齐）。

    report_data 结构（来自 report_service.build_report / report.report_data）：
    {
      "week_start", "week_end", "effective_days",
      "members": [{member_id, member_name, nutrients: [
          {nutrient_name, rni_per_day, effective_days, total_intake,
           daily_avg, rate, exceeded, gap}], problem_summary}],
      "weekly_tips": [str]
    }

    sheet1 周报明细（成员 x 营养素逐行）；sheet2 成员问题汇总。
    """
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "周报明细"
    ws.append(
        [
            "成员",
            "营养素",
            "RNI/天",
            "有效天数",
            "累计摄入",
            "日均摄入",
            "达标率%",
            "状态",
            "累计缺口",
        ]
    )

    for member in report_data.get("members", []):
        for n in member.get("nutrients", []):
            status = (
                "超标"
                if n.get("exceeded")
                else ("缺口" if float(n.get("rate", 0)) < 100 else "达标")
            )
            ws.append(
                [
                    member.get("member_name", ""),
                    n.get("nutrient_name", ""),
                    n.get("rni_per_day", 0),
                    n.get("effective_days", 0),
                    n.get("total_intake", 0),
                    n.get("daily_avg", 0),
                    n.get("rate", 0),
                    status,
                    n.get("gap", 0),
                ]
            )

    for col, width in zip(
        "ABCDEFGHI", [12, 12, 10, 10, 12, 12, 10, 8, 12], strict=True
    ):
        ws.column_dimensions[col].width = width

    ws2 = wb.create_sheet("问题与建议")
    ws2.append(["成员", "本周问题", "下周建议"])
    # 建议按成员各自的问题生成，避免跨成员串建议；无问题则给保持性建议
    for member in report_data.get("members", []):
        problems = member.get("problem_summary", [])
        ws2.append(
            [
                member.get("member_name", ""),
                "；".join(problems),
                ("建议关注：" + problems[0])
                if problems
                else "下周继续保持规律饮食与运动",
            ]
        )
    for col, width in zip("ABC", [12, 60, 60], strict=True):
        ws2.column_dimensions[col].width = width

    out_path = _ensure_dir() / file_name
    wb.save(out_path)
    return str(out_path)

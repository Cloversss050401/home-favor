"""通用工具：采购清单导出 Excel。

字段顺序（对齐业务规则）：优先级 / 食材名称 / 需要补充营养素 / 建议采购量(g) / 备注
也支持 csv 导出。产物写入 resources/exports 目录（被 .gitignore 忽略）。
"""
import csv
from pathlib import Path

from openpyxl import Workbook

from src.config.constants import PURCHASE_PRIORITY_ORDER

_EXPORT_DIR = Path(__file__).resolve().parents[2] / "resources" / "exports"
_EXPORT_HEADERS = ["优先级", "食材名称", "需要补充营养素", "建议采购量(g)", "备注"]


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
            ]
        )

    # 列宽基础优化
    for col, width in zip("ABCDE", [8, 16, 20, 16, 30], strict=True):
        ws.column_dimensions[col].width = width

    out_path = _ensure_dir() / file_name
    wb.save(out_path)
    return str(out_path)


def export_purchase_csv(
    items: list[dict], file_name: str = "purchase_list.csv"
) -> str:
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
                ]
            )
    return str(out_path)
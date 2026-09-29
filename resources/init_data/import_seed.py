"""字典表种子数据导入脚本。

用法（须在项目根目录执行）：
    python resources/init_data/import_seed.py

功能：
- food_nutrition.json   -> food_nutrition 表（中国食物成分表示例数据）
- dris_standard.json    -> dris_standard 表（DRIs 参考摄入量示例数据）
- 幂等：按 food_name / (target_type, nutrient_code) 已存在则跳过，不重复插入。

说明：内置 JSON 为「示例数据」，生产环境请以权威版本
（《中国食物成分表》、WS/T 578《中国居民膳食营养素参考摄入量》）替换后重新导入。
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.db import (  # noqa: E402
    Base,
    SessionLocal,
    engine,
    ensure_models_imported,
)
from app.modules.nutrition.models import DrisStandard, FoodNutrition  # noqa: E402

ensure_models_imported()  # 注册全部表模型，保证 create_all 建全表

DATA_DIR = Path(__file__).resolve().parent


def load(name: str) -> list[dict]:
    with (DATA_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()

    food_count = dris_count = skipped = 0
    try:
        # 1) 食物成分表
        existing_food = {
            row.food_name for row in db.query(FoodNutrition.food_name).all()
        }
        for item in load("food_nutrition.json"):
            if item["food_name"] in existing_food:
                skipped += 1
                continue
            db.add(FoodNutrition(**item))
            food_count += 1

        # 2) DRIs
        existing_dris = {
            (row.target_type, row.nutrient_code)
            for row in db.query(
                DrisStandard.target_type, DrisStandard.nutrient_code
            ).all()
        }
        for item in load("dris_standard.json"):
            key = (item["target_type"], item["nutrient_code"])
            if key in existing_dris:
                skipped += 1
                continue
            db.add(DrisStandard(**item))
            dris_count += 1

        db.commit()
        print(
            f"[import_seed] food_nutrition +{food_count} / dris_standard +{dris_count} / skipped {skipped}"
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

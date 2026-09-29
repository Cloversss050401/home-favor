"""通用工具：食材同义词合并。

从 resources/dict/synonyms.json 加载同义词映射：
{
  "canonical": ["别名1", "别名2"]
}
用于采购清单同类合并、识别结果去重归并。
"""
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
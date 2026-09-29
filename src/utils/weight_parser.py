"""通用工具：重量解析（“番茄 500g”自动拆分名称与重量）。"""
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
"""多模态 OCR 客户端（拍照识别食材）。

设计要点：
- 全部外部多模态识别能力统一封装在本层
- 密钥就绪走真实调用；否则 Mock 返回样例（供联调）
- 输入：本地图片路径/bytes；输出：规范化的待确认食材列表
"""
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from src.config.settings import settings
from src.exceptions.business_exception import ExternalClientUnavailable
from src.schemas.ingredient_schema import IngredientRecognizeItem


class BaseMultimodalClient:
    name = "multimodal"

    def recognize_ingredients(self, image_path: str) -> list[IngredientRecognizeItem]:
        raise NotImplementedError


class MultimodalClient(BaseMultimodalClient):
    """OpenAI 兼容多模态接口（图片输入）。"""

    name = "multimodal"

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def recognize_ingredients(self, image_path: str) -> list[IngredientRecognizeItem]:
        path = Path(image_path)
        if not path.exists():
            raise ExternalClientUnavailable("图片文件不存在")
        import base64

        image_b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "识别图中全部食材，输出 JSON 数组，"
                            "每项形如 {\"name\":\"食材名\",\"available_weight\":数量或null,"
                            "\"weight_unit\":\"g\"}，不要输出多余内容",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                    ],
                }
            ],
        }
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise ExternalClientUnavailable("多模态识别服务异常") from exc
        return self._parse_items(content)

    @staticmethod
    def _parse_items(content: str) -> list[IngredientRecognizeItem]:
        import json

        text = content.strip()
        if text.startswith("```"):
            lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
            text = "\n".join(lines).strip()
        start, end = text.find("["), text.rfind("]")
        if start == -1 or end == -1:
            raise ExternalClientUnavailable("多模态识别结果解析失败")
        try:
            raw = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ExternalClientUnavailable("多模态识别结果解析失败") from exc
        items: list[IngredientRecognizeItem] = []
        for item in raw if isinstance(raw, list) else []:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            weight = item.get("available_weight")
            items.append(
                IngredientRecognizeItem(
                    name=str(item["name"]),
                    available_weight=(
                        Decimal(str(weight)) if weight is not None else None
                    ),
                    weight_unit=str(item.get("weight_unit", "g")),
                )
            )
        return items


class MockMultimodalClient(BaseMultimodalClient):
    """本地 Mock：无密钥时返回样例识别结果（供前端联调）。"""

    name = "multimodal-mock"

    def recognize_ingredients(self, image_path: str) -> list[IngredientRecognizeItem]:
        return [
            IngredientRecognizeItem(
                name="番茄", available_weight=Decimal("500.0"), weight_unit="g"
            ),
            IngredientRecognizeItem(name="鸡蛋", available_weight=None, weight_unit="g"),
        ]


_client: BaseMultimodalClient | None = None


def get_multimodal_client() -> BaseMultimodalClient:
    global _client
    if _client is None:
        if settings.multimodal_ready:
            _client = MultimodalClient(
                api_key=settings.MULTIMODAL_API_KEY,
                base_url=settings.MULTIMODAL_BASE_URL,
                model=settings.MULTIMODAL_MODEL,
            )
        else:
            _client = MockMultimodalClient()
    return _client
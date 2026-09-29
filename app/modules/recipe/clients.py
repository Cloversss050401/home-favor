"""大模型客户端（AI 食谱生成）。

设计要点（对齐技术方案选型）：
- 所有外部大模型能力统一封装在本层，业务层不得直接调用 API
- OpenAI 兼容接口：POST {base_url}/chat/completions
- 密钥就绪（LLM_API_KEY + LLM_BASE_URL）走真实调用；否则使用 MockLLMClient
  保证前端/本地联调阶段可用
- 超时 30s（LLM_TIMEOUT_SEC），超时抛 LLMTimeoutError；JSON 解析在 service 层
"""
import httpx

from app.core.constants import LLM_TIMEOUT_SEC, LLM_TIMEOUT_MSG
from app.core.config import settings
from app.core.exceptions import ExternalClientUnavailable, LLMTimeoutError


class BaseLLMClient:
    """大模型客户端接口约定。"""

    name = "llm"

    def generate_text(self, prompt: str) -> str:
        raise NotImplementedError


class LLMClient(BaseLLMClient):
    """OpenAI 兼容接口真实客户端。"""

    name = "llm"

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = LLM_TIMEOUT_SEC,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate_text(self, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是资深家庭营养师，严格遵守输出 JSON 结构要求。",
                },
                {"role": "user", "content": prompt},
            ],
            # 低温度：输出更稳定、收敛更快；限制输出长度避免长文本拖慢生成
            "temperature": 0.3,
            "max_tokens": 2000,
        }
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(LLM_TIMEOUT_MSG) from exc
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise ExternalClientUnavailable("大模型服务异常") from exc


class MockLLMClient(BaseLLMClient):
    """本地 Mock：无密钥时返回固定样例 JSON，保证联调链路可走通。"""

    name = "llm-mock"

    def generate_text(self, prompt: str) -> str:
        return (
            '{"shared_dishes":'
            '[{"name":"番茄炒蛋","category":"main","is_main_dish":true,'
            '"main_ingredients":["番茄","鸡蛋"],"cooking_method":"热锅下油炒蛋，加入番茄翻炒",'
            '"estimated_servings":2,"note":""},'
            '{"name":"清炒时蔬","category":"main","is_main_dish":true,'
            '"main_ingredients":["油菜"],"cooking_method":"快炒",'
            '"estimated_servings":2,"note":""}],'
            '"member_allocation":[{"member_id":1,"member_name":"小美","dishes":'
            '[{"dish_name":"番茄炒蛋","amount_g":150},{"dish_name":"清炒时蔬","amount_g":120}],'
            '"intake_advantage":["蛋白质充足"],"nutrition_gap":[]}]}'
        )


_client: BaseLLMClient | None = None


def get_llm_client() -> BaseLLMClient:
    """工厂：密钥就绪返回真实客户端，否则返回 Mock。"""
    global _client
    if _client is None:
        if settings.llm_ready:
            _client = LLMClient(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
                model=settings.LLM_MODEL,
            )
        else:
            _client = MockLLMClient()
    return _client
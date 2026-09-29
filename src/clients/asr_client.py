"""ASR 方言语音客户端（武汉方言 → 文字）。

设计要点：
- 语音识别能力统一封装在本层
- 密钥就绪走真实调用；否则 Mock 返回固定转写文本
- 转写仅是食材文字，后续与文字录入共用同一解析链路（人工确认兜底）
"""
from pathlib import Path

import httpx

from src.config.settings import settings
from src.exceptions.business_exception import ExternalClientUnavailable


class BaseASRClient:
    name = "asr"

    def speech_to_text(self, audio_path: str) -> str:
        raise NotImplementedError


class ASRClient(BaseASRClient):
    """百度短语音/长语音（或 OpenAI 兼容）接口。"""

    name = "asr"

    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def speech_to_text(self, audio_path: str) -> str:
        path = Path(audio_path)
        if not path.exists():
            raise ExternalClientUnavailable("音频文件不存在")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            with path.open("rb") as f:
                resp = httpx.post(
                    f"{self.base_url}/asr",
                    headers=headers,
                    files={"file": (path.name, f.read())},
                    timeout=30.0,
                )
            resp.raise_for_status()
            data = resp.json()
            return str(data.get("result", data.get("text", "")))
        except (httpx.HTTPError, OSError, ValueError) as exc:
            raise ExternalClientUnavailable("语音识别服务异常") from exc


class MockASRClient(BaseASRClient):
    """本地 Mock：无密钥时返回固定转写（模拟武汉话：番茄带把的，鸡胸肉半斤）。"""

    name = "asr-mock"

    def speech_to_text(self, audio_path: str) -> str:
        return "番茄 500g，鸡胸肉"


_client: BaseASRClient | None = None


def get_asr_client() -> BaseASRClient:
    global _client
    if _client is None:
        if settings.asr_ready:
            _client = ASRClient(
                api_key=settings.ASR_API_KEY,
                base_url=settings.ASR_BASE_URL,
            )
        else:
            _client = MockASRClient()
    return _client
"""业务异常：统一错误码 + 消息。"""
from typing import Any


class BusinessException(Exception):
    """业务规则异常：由全局异常处理器捕获并转为 JSON 响应。"""

    def __init__(
        self,
        code: str = "BUSINESS_ERROR",
        message: str = "业务处理失败",
        status_code: int = 400,
        data: Any = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.data = data
        super().__init__(message)


class MemberLimitExceeded(BusinessException):
    def __init__(self, limit: int = 8) -> None:
        super().__init__(
            code="MEMBER_LIMIT_EXCEEDED",
            message=f"最多添加 {limit} 位家庭成员",
            status_code=400,
        )


class MemberNotFound(BusinessException):
    def __init__(self) -> None:
        super().__init__(
            code="MEMBER_NOT_FOUND", message="家庭成员不存在", status_code=404
        )


class IngredientNotFound(BusinessException):
    def __init__(self) -> None:
        super().__init__(
            code="INGREDIENT_NOT_FOUND", message="食材不存在", status_code=404
        )


class FamilyNotFound(BusinessException):
    def __init__(self) -> None:
        super().__init__(
            code="FAMILY_NOT_FOUND", message="家庭不存在", status_code=404
        )


class RecipeRecordNotFound(BusinessException):
    def __init__(self) -> None:
        super().__init__(
            code="RECIPE_RECORD_NOT_FOUND", message="食谱记录不存在", status_code=404
        )


class LLMTimeoutError(BusinessException):
    def __init__(self, message: str = "生成食谱超时，请减少食材或稍后重试") -> None:
        super().__init__(code="LLM_TIMEOUT", message=message, status_code=504)


class LLMJsonParseError(BusinessException):
    def __init__(self, message: str = "食谱生成结果解析失败，请重试") -> None:
        super().__init__(code="LLM_JSON_PARSE_ERROR", message=message, status_code=502)


class NutritionDataMissing(BusinessException):
    def __init__(self, nutrient: str = "") -> None:
        super().__init__(
            code="NUTRITION_DATA_MISSING",
            message=f"营养字典数据缺失: {nutrient}",
            status_code=500,
        )


class ExternalClientUnavailable(BusinessException):
    def __init__(self, client: str = "") -> None:
        super().__init__(
            code="EXTERNAL_CLIENT_UNAVAILABLE",
            message=f"外部能力暂不可用: {client}",
            status_code=503,
        )


class ReportNotReady(BusinessException):
    def __init__(self, message: str = "本周暂无有效反馈记录，无法生成周报") -> None:
        super().__init__(code="REPORT_NOT_READY", message=message, status_code=400)
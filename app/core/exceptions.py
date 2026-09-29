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


import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


logger = logging.getLogger(__name__)


def _error_body(code: str, message: str, data=None) -> dict:
    body = {"code": code, "message": message, "data": data}
    return body


def register_exception_handler(app: FastAPI) -> None:
    """注册全部全局异常处理器（业务异常 + HTTP 异常 + 兜底异常）。"""

    @app.exception_handler(BusinessException)
    async def handle_business(
        _request: Request, exc: BusinessException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.data),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body("HTTP_ERROR", str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("未处理异常: %s", exc)
        return JSONResponse(
            status_code=500,
            content=_error_body("INTERNAL_ERROR", "服务器内部错误"),
        )

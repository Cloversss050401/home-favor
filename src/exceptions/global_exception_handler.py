"""全局异常处理器：统一异常 -> JSON 响应。"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.exceptions.business_exception import BusinessException

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
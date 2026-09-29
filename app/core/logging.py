"""日志全局配置：统一输出格式，供各模块复用。

用法：
    from app.core.logging import get_logger
    logger = get_logger(__name__)
"""

import logging
import sys

_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    """全局初始化日志（应用启动时调用一次）。"""
    logging.basicConfig(
        level=level,
        format=_FORMAT,
        stream=sys.stdout,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """获取统一配置的业务 Logger。"""
    return logging.getLogger(name)

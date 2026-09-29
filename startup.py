"""
项目启动入口（命令行启动入口）。

用法:
    python startup.py

修复记录（DEF-01）：无论从哪个工作目录调用本脚本，都先切换到项目根目录并
把项目根加入 sys.path，再加载配置启动服务。避免因 cwd 不同导致：
- 读不到 .env（回退默认 MySQL 连接串，接口全部失败）；
- sqlite 数据库文件落到错误目录（表现为"重启后档案丢失"）。
与 scripts/dev_launcher.py 的 os.chdir + sys.path.insert 行为保持一致。
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    # 关键：先切到项目根并修正导入路径，再导入业务模块
    os.chdir(PROJECT_ROOT)
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    import uvicorn

    from src.config.settings import settings

    uvicorn.run(
        "src.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
    )

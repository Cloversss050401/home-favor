"""一键启动器：检查依赖 -> 生成 .env -> 预检数据库/端口 -> 导入种子 -> 启动并打开浏览器。

用法（Windows 双击 start.bat，或命令行）:
    python scripts/dev_launcher.py
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"

# 启动必需的关键依赖（缺失时自动 pip install -r requirements.txt）
REQUIRED_MODULES = (
    "fastapi",
    "uvicorn",
    "sqlalchemy",
    "pydantic",
    "pydantic_settings",
    "httpx",
    "openpyxl",
    "multipart",
    "dotenv",
)


def _importable(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def ensure_deps() -> None:
    missing = [m for m in REQUIRED_MODULES if not _importable(m)]
    if not missing:
        print("[1/5] 依赖检查通过")
        return
    print(f"[1/5] 缺少依赖 {missing}，正在安装 requirements.txt ...")
    code = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)]
    ).returncode
    if code != 0:
        sys.exit(f"[失败] 依赖安装失败，请检查网络后重试（退出码 {code}）")
    print("[1/5] 依赖安装完成")


def _mysql_reachable(db_url: str) -> bool:
    try:
        import pymysql

        m = re.match(
            r"mysql\+pymysql://([^:]+):([^@]+)@([^/:]+)(?::(\d+))?/(\w+)", db_url
        )
        if not m:
            return False
        user, pwd, host, port, db = (
            m.group(1),
            m.group(2),
            m.group(3),
            int(m.group(4) or 3306),
            m.group(5),
        )
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=pwd,
            database=db,
            connect_timeout=2,
        )
        conn.close()
        return True
    except Exception:
        return False


def ensure_env() -> str:
    if ENV_FILE.exists():
        print("[2/5] 使用现有 .env")
        return ENV_FILE.read_text(encoding="utf-8")
    template = ENV_EXAMPLE.read_text(encoding="utf-8")
    if _mysql_reachable("mysql+pymysql://root:password@127.0.0.1:3306/ai_recipe"):
        env_text = template
        print("[2/5] 检测到本地 MySQL，已生成 .env（MySQL 模式）")
    else:
        env_text = re.sub(
            r"(?m)^DB_URL=.*$", "DB_URL=sqlite:///./data/ai_recipe.db", template
        )
        print(
            "[2/5] 未检测到本地 MySQL，已生成 .env（默认 SQLite 开箱即用；如需 MySQL 请改 DB_URL）"
        )
    ENV_FILE.write_text(env_text, encoding="utf-8")
    return env_text


def _env_value(env_text: str, key: str, default: str) -> str:
    m = re.search(rf"^{key}=(.*)$", env_text, re.MULTILINE)
    return m.group(1).strip() if m else default


def precheck_db(db_url: str) -> None:
    if db_url.startswith("sqlite"):
        m = re.search(r"sqlite:///(.+)$", db_url)
        if m:
            db_path = Path(m.group(1))
            if not db_path.is_absolute():
                db_path = PROJECT_ROOT / db_path
            db_path.parent.mkdir(parents=True, exist_ok=True)
        print("[3/5] 数据库预检通过（SQLite）")
        return
    if db_url.startswith("mysql"):
        if not _mysql_reachable(db_url):
            sys.exit(
                "[失败] MySQL 不可达。请确认 MySQL 已启动、账号密码正确，"
                "或将 .env 的 DB_URL 改为 sqlite:///./data/ai_recipe.db 后重试"
            )
        print("[3/5] 数据库预检通过（MySQL）")
        return
    print("[3/5] 跳过数据库预检（自定义 DB_URL）")


def port_in_use(port: int) -> bool:
    """检测端口是否被占用：尝试 bind + listen，成功则说明端口空闲。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", port))
            s.listen(1)
            return False  # bind 成功 = 端口空闲
        except OSError:
            return True  # bind 失败 = 端口被占用


def find_free_port(start_port: int, max_attempts: int = 100) -> int:
    """从 start_port 开始向上查找空闲端口。"""
    for p in range(start_port, start_port + max_attempts):
        if not port_in_use(p):
            return p
    sys.exit(
        f"[失败] 端口 {start_port} ~ {start_port + max_attempts - 1} 均被占用，"
        "请手动修改 .env 中的 SERVER_PORT 后重试。"
    )


def import_seed() -> None:
    print("[4/5] 导入字典种子数据（幂等）...")
    code = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "resources" / "init_data" / "import_seed.py"),
        ],
        cwd=str(PROJECT_ROOT),
    ).returncode
    if code != 0:
        sys.exit("[失败] 种子数据导入失败，详见上方日志")
    print("[4/5] 种子数据就绪")


def _update_env_port(env_text: str, new_port: int) -> str:
    """将 .env 文本中的 SERVER_PORT 替换为新端口，保持其余配置不变。"""
    lines = env_text.splitlines()
    updated = False
    for i, line in enumerate(lines):
        if line.startswith("SERVER_PORT="):
            lines[i] = f"SERVER_PORT={new_port}"
            updated = True
            break
    if not updated:
        lines.append(f"SERVER_PORT={new_port}")
    return "\n".join(lines)


def _resolve_port(env_text: str) -> tuple[int, int]:
    """解析 .env 中的端口；若被占用则自动找空闲端口并写回 .env。
    返回 (原始端口, 实际端口)。"""
    original = int(_env_value(env_text, "SERVER_PORT", "8000"))
    port = original
    if port_in_use(port):
        port = find_free_port(port + 1)
        print(f"[警告] 端口 {original} 已被占用，已自动切换至空闲端口 {port}")
        env_text = _update_env_port(env_text, port)
        ENV_FILE.write_text(env_text, encoding="utf-8")
        print(f"[更新] .env 中 SERVER_PORT 已更新为 {port}（不影响数据库路径）")
    else:
        print(f"[端口] {port} 可用")
    return original, port


def start_vite_dev() -> subprocess.Popen | None:
    """启动 Vite 前端开发服务器（后台进程）。

    返回 Popen 对象，用于在主进程退出时清理。若 npm 不可用则返回 None。
    """
    frontend_dir = PROJECT_ROOT / "frontend"
    if not (frontend_dir / "package.json").exists():
        print("[前端] 未找到 frontend/package.json，跳过 Vite 启动")
        return None
    # 先确保依赖已安装
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("[前端] 检测到 node_modules 缺失，正在执行 npm install ...")
        install_code = subprocess.run(
            ["npm.cmd", "install"],
            cwd=str(frontend_dir),
            shell=True,
        ).returncode
        if install_code != 0:
            print("[警告] npm install 失败，Vite 可能无法启动")
    print("[前端] 启动 Vite 开发服务器 (http://localhost:5173) ...")
    try:
        proc = subprocess.Popen(
            ["npm.cmd", "run", "dev"],
            cwd=str(frontend_dir),
            shell=True,
        )
        return proc
    except Exception as exc:  # noqa: BLE001
        print(f"[警告] 启动 Vite 失败: {exc}")
        return None


def main() -> None:
    os.chdir(PROJECT_ROOT)
    sys.path.insert(
        0, str(PROJECT_ROOT)
    )  # 保证 uvicorn reload 的 worker 子进程可 import app
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("==== 家庭 AI 食谱推荐系统 · 一键启动 ====")
    ensure_deps()
    env_text = ensure_env()

    db_url = _env_value(env_text, "DB_URL", "sqlite:///./data/ai_recipe.db")
    host = _env_value(env_text, "SERVER_HOST", "0.0.0.0")
    debug = _env_value(env_text, "DEBUG", "True").lower() in ("true", "1", "yes")

    precheck_db(db_url)
    original_port, port = _resolve_port(env_text)

    import_seed()

    docs_url = f"http://127.0.0.1:{port}/docs"
    # 前端走 Vite 开发服务器（vite.config.ts 中已配置 /api 代理到后端）
    frontend_url = "http://localhost:5173/"
    vite_proc = start_vite_dev()
    # 等 Vite 启动后再打开浏览器（Vite 冷启动约 2~3 秒）
    threading.Timer(4.0, lambda: webbrowser.open(frontend_url)).start()
    if original_port != port:
        print(f"[5/5] 正在启动服务（端口已从 {original_port} 自动切换到 {port}）...")
    else:
        print(f"[5/5] 正在启动服务 ...")
    print(f"   前端页面: {frontend_url}")
    print(f"   API文档: {docs_url}（按 Ctrl+C 停止）")

    import uvicorn

    try:
        uvicorn.run("app.main:app", host=host, port=port, reload=debug)
    finally:
        if vite_proc is not None and vite_proc.poll() is None:
            vite_proc.terminate()


if __name__ == "__main__":
    main()

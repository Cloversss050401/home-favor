"""架构合规测试：按业务功能分包（app/modules/*）校验分层 import 依赖。

分层约定（见 docs/tech_architecture.md）：
router -> service -> repository -> models（各模块五件套）
clients 仅被 service 依赖；schemas / core / common 为公共横向能力。

校验规则（禁反向依赖）：
- router：不得 import 任何模块的 repository / models / clients / router（允许跨模块 service、schemas、common.deps）
- service：不得 import 任何模块的 router
- repository：不得 import 任何模块的 service / router / clients
- clients：不得 import 任何模块的 router / service / repository / models（允许 schemas）
- models：不得 import 任何 app.modules 业务代码（仅允许 app.core.db 的 Base）

模块内同层横向引用（如跨模块 service 互调）放行；
跨模块引用 repository（recipe.service 依赖多个模块 repository）在 service 层放行。
"""

import ast
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULES_DIR = PROJECT_ROOT / "app" / "modules"

# 各层 forbidden：模式 -> (匹配段位置, 匹配的段值集合)
# 样例模块路径 app.modules.family_member.repository
_ARR = "app.modules."


def _segments(mod: str) -> tuple[str, ...] | None:
    """拆解 app.modules 内部模块路径：返回 (业务模块, 层名, 其余...)。"""
    if not mod.startswith(_ARR):
        return None
    rest = mod[len(_ARR) :]
    parts = rest.split(".")
    if len(parts) < 2:
        return None
    return parts[0], parts[1], ".".join(parts[2:])


def iter_module_files():
    for path in sorted(MODULES_DIR.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        yield path


def extract_imports(py_file: Path) -> set[str]:
    """提取文件内全部 import 的绝对模块名。"""
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


def check_router(path: Path) -> list[str]:
    violations: list[str] = []
    for mod in extract_imports(path):
        segs = _segments(mod)
        if segs is None:
            continue
        _module, layer, _rest = segs
        if layer in ("repository", "models", "clients", "router"):
            violations.append(f"{path.relative_to(PROJECT_ROOT)} 违规 import {mod}")
    return violations


def check_service(path: Path) -> list[str]:
    violations: list[str] = []
    for mod in extract_imports(path):
        segs = _segments(mod)
        if segs is None:
            continue
        _module, layer, _rest = segs
        if layer == "router":
            violations.append(f"{path.relative_to(PROJECT_ROOT)} 违规 import {mod}")
    return violations


def check_repository(path: Path) -> list[str]:
    violations: list[str] = []
    for mod in extract_imports(path):
        segs = _segments(mod)
        if segs is None:
            continue
        _module, layer, _rest = segs
        if layer in ("service", "router", "clients"):
            violations.append(f"{path.relative_to(PROJECT_ROOT)} 违规 import {mod}")
    return violations


def check_clients(path: Path) -> list[str]:
    violations: list[str] = []
    for mod in extract_imports(path):
        segs = _segments(mod)
        if segs is None:
            continue
        _module, layer, _rest = segs
        if layer in ("router", "service", "repository", "models"):
            violations.append(f"{path.relative_to(PROJECT_ROOT)} 违规 import {mod}")
    return violations


def check_models(path: Path) -> list[str]:
    violations: list[str] = []
    for mod in extract_imports(path):
        if mod.startswith("app.modules"):
            violations.append(f"{path.relative_to(PROJECT_ROOT)} 违规 import {mod}")
    return violations


LAYER_CHECKS = {
    "router": check_router,
    "service": check_service,
    "repository": check_repository,
    "clients": check_clients,
    "models": check_models,
}

# 文件后缀名 -> 所属层：每个文件只按自身层做依赖检查
LAYER_BY_FILENAME = {
    "router.py": "router",
    "service.py": "service",
    "repository.py": "repository",
    "clients.py": "clients",
    "models.py": "models",
}


def collect_violations() -> dict[str, list[str]]:
    all_violations: dict[str, list[str]] = {k: [] for k in LAYER_CHECKS}
    for py_file in iter_module_files():
        layer = LAYER_BY_FILENAME.get(py_file.name)
        if layer is None:
            continue
        all_violations[layer].extend(LAYER_CHECKS[layer](py_file))
    return all_violations


def _assert_layer(layer: str, violations: dict[str, list[str]]) -> None:
    v = violations[layer]
    assert v == [], (
        f"{layer} 层存在反向依赖（详见 docs/tech_architecture.md 分层约束）:\n"
        + "\n".join(v)
    )


def test_router_does_not_import_repository_models_clients():
    _assert_layer("router", collect_violations())


def test_service_does_not_import_router():
    _assert_layer("service", collect_violations())


def test_repository_does_not_import_service_router_clients():
    _assert_layer("repository", collect_violations())


def test_clients_does_not_import_business_layers():
    _assert_layer("clients", collect_violations())


def test_models_only_import_orm_dependencies():
    _assert_layer("models", collect_violations())


def test_no_module_imports_old_src_package():
    """兜底：全项目禁止残留旧 src. 引用（post 重构完整性）。"""
    pattern = re.compile(
        r"\bsrc\.(?:config|controllers|services|repository|models|schemas|clients|utils|exceptions)\b"
    )
    for py_file in sorted(list(PROJECT_ROOT.rglob("*.py"))):
        rel = py_file.relative_to(PROJECT_ROOT)
        if ".venv" in rel.parts or ".deps" in rel.parts or ".git" in rel.parts:
            continue
        if rel.parts and rel.parts[0] == "scripts" and rel.name.startswith("_"):
            continue  # 一次性迁移/运维脚本不参与架构合规检查
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        m = pattern.search(text)
        if m:
            raise AssertionError(f"{rel} 仍引用旧包 {m.group(0)}")

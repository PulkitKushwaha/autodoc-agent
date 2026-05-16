import ast
from pathlib import Path

from autodoc.logger import get_logger
from autodoc.models.manifest import (
    ArgumentInfo,
    ClassInfo,
    FileInfo,
    FunctionInfo,
    ImportInfo,
)

logger = get_logger(__name__)

_SKIP_DIRS = {
    ".venv", "venv", "__pycache__", ".git",
    "node_modules", "dist", "build", ".eggs",
    "migrations", "alembic",
}


def parse_codebase(root: Path) -> list[FileInfo]:
    """Walk all .py files under root and extract AST metadata from each."""
    logger.info("Scanning for Python files under: %s", root)

    files = []
    skipped_dirs = 0
    skipped_syntax = 0

    for py_file in sorted(root.rglob("*.py")):
        if _should_skip(py_file, root):
            skipped_dirs += 1
            logger.debug("Skipped (excluded dir): %s", py_file)
            continue

        file_info = parse_file(py_file, root)

        if file_info is None:
            skipped_syntax += 1
            logger.warning("Skipped (syntax error): %s", py_file)
            continue

        logger.debug(
            "Parsed: %s — classes: %d, functions: %d, imports: %d",
            file_info.path,
            len(file_info.classes),
            len(file_info.functions),
            len(file_info.imports),
        )
        files.append(file_info)

    logger.info(
        "Parse complete — parsed: %d, skipped (dirs): %d, skipped (syntax): %d",
        len(files),
        skipped_dirs,
        skipped_syntax,
    )
    return files


def parse_file(path: Path, root: Path) -> FileInfo | None:
    """Parse a single .py file and return a FileInfo object."""
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        logger.debug("SyntaxError in %s: %s", path, e)
        return None

    relative = path.relative_to(root)
    module_name = _path_to_module_name(relative)

    return FileInfo(
        path=str(relative),
        module_name=module_name,
        docstring=ast.get_docstring(tree),
        classes=_extract_classes(tree),
        functions=_extract_top_level_functions(tree),
        imports=_extract_imports(tree),
        line_count=len(source.splitlines()),
    )


def _extract_classes(tree: ast.Module) -> list[ClassInfo]:
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(ClassInfo(
                name=node.name,
                bases=_extract_base_names(node.bases),
                docstring=ast.get_docstring(node),
                methods=_extract_methods(node),
                line_number=node.lineno,
            ))
    return classes


def _extract_methods(class_node: ast.ClassDef) -> list[FunctionInfo]:
    methods = []
    for node in ast.walk(class_node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.col_offset > class_node.col_offset:
                methods.append(_build_function_info(node, is_method=True))
    return methods


def _extract_top_level_functions(tree: ast.Module) -> list[FunctionInfo]:
    functions = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(_build_function_info(node, is_method=False))
    return functions


def _build_function_info(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    is_method: bool,
) -> FunctionInfo:
    args = [
        ArgumentInfo(
            name=arg.arg,
            annotation=ast.unparse(arg.annotation) if arg.annotation else None,
        )
        for arg in node.args.args
        if arg.arg not in ("self", "cls")
    ]
    return FunctionInfo(
        name=node.name,
        args=args,
        return_annotation=ast.unparse(node.returns) if node.returns else None,
        docstring=ast.get_docstring(node),
        line_number=node.lineno,
        is_method=is_method,
    )


def _extract_imports(tree: ast.Module) -> list[ImportInfo]:
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(ImportInfo(
                    module=alias.name,
                    is_from_import=False,
                ))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(ImportInfo(
                    module=node.module,
                    names=[alias.name for alias in node.names],
                    is_from_import=True,
                ))
    return imports


def _extract_base_names(bases: list[ast.expr]) -> list[str]:
    names = []
    for base in bases:
        try:
            names.append(ast.unparse(base))
        except Exception:
            pass
    return names


def _path_to_module_name(relative: Path) -> str:
    parts = list(relative.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].removesuffix(".py")
    return ".".join(parts)


def _should_skip(path: Path, root: Path) -> bool:
    return any(
        part in _SKIP_DIRS
        for part in path.relative_to(root).parts
    )

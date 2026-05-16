from autodoc.logger import get_logger
from autodoc.models.manifest import DependencyGraph, FileInfo

logger = get_logger(__name__)


def build_dependency_graph(files: list[FileInfo]) -> DependencyGraph:
    """
    Build an import dependency graph from parsed file data.

    Nodes are module names. An edge from A to B means module A
    imports something from module B. Only internal project modules
    are tracked — stdlib and third-party imports are excluded.
    """
    logger.info("Building dependency graph for %d modules", len(files))

    known_modules = {f.module_name for f in files}
    logger.debug("Known modules: %s", sorted(known_modules))

    edges: dict[str, list[str]] = {f.module_name: [] for f in files}

    for file in files:
        for imp in file.imports:
            target = _resolve_import(imp.module, known_modules)
            if target and target != file.module_name:
                if target not in edges[file.module_name]:
                    edges[file.module_name].append(target)
                    logger.debug("Edge: %s → %s", file.module_name, target)

    total_edges = sum(len(v) for v in edges.values())
    logger.info(
        "Dependency graph complete — %d nodes, %d edges",
        len(edges),
        total_edges,
    )
    return DependencyGraph(edges=edges)


def _resolve_import(module: str, known_modules: set[str]) -> str | None:
    """
    Check whether an import refers to a module within this project.

    Handles exact matches and partial prefix matches so that
    'from autodoc import config' correctly resolves to 'autodoc.config'.
    """
    if module in known_modules:
        return module

    for known in known_modules:
        if known.startswith(module + ".") or module.startswith(known + "."):
            return known

    return None

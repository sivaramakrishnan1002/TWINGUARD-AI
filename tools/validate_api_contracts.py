"""Validate the project's JSON-serialized OpenAPI YAML contracts offline."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = {
    ROOT / "docs/api/ai-service.yaml": {
        "/health": {"get"},
        "/layers": {"get"},
        "/forecast": {"post"},
        "/uncertainty": {"post"},
        "/impact": {"post"},
        "/route": {"post"},
        "/scenario": {"post"},
    },
    ROOT / "docs/api/backend.yaml": {
        "/twin/state": {"get"},
        "/scenarios": {"get", "post"},
        "/scenarios/{scenario_key}": {"get"},
        "/routes": {"post"},
        "/alerts": {"get"},
        "/shelters": {"get"},
    },
}
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


def _resolve_pointer(document: dict[str, Any], ref: str) -> Any:
    if not ref.startswith("#/"):
        raise ValueError(f"external OpenAPI reference is not allowed: {ref}")
    value: Any = document
    for part in ref[2:].split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or key not in value:
            raise ValueError(f"unresolved OpenAPI reference: {ref}")
        value = value[key]
    return value


def _check_refs(document: dict[str, Any], node: Any) -> None:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if ref is not None:
            if not isinstance(ref, str):
                raise ValueError("OpenAPI $ref must be a string")
            _resolve_pointer(document, ref)
        for value in node.values():
            _check_refs(document, value)
    elif isinstance(node, list):
        for value in node:
            _check_refs(document, value)


def validate_contract(path: Path, required: dict[str, set[str]]) -> dict[str, int | str]:
    # JSON is a strict subset of YAML 1.2 and avoids requiring a YAML package.
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("openapi") not in {"3.0.0", "3.0.1", "3.0.2", "3.0.3", "3.1.0", "3.1.1"}:
        raise ValueError(f"{path.name}: expected an OpenAPI 3.0/3.1 document")
    info = document.get("info")
    if not isinstance(info, dict) or not all(isinstance(info.get(k), str) and info[k] for k in ("title", "version")):
        raise ValueError(f"{path.name}: info.title and info.version are required")
    paths = document.get("paths")
    if not isinstance(paths, dict):
        raise ValueError(f"{path.name}: paths must be an object")
    for route, methods in required.items():
        if route not in paths:
            raise ValueError(f"{path.name}: required path missing: {route}")
        available = {m for m in paths[route] if m in HTTP_METHODS}
        if not methods.issubset(available):
            raise ValueError(f"{path.name}: {route} missing methods {sorted(methods - available)}")
    operation_count = 0
    for route, path_item in paths.items():
        if not isinstance(path_item, dict):
            raise ValueError(f"{path.name}: path item must be an object: {route}")
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue
            operation_count += 1
            if not isinstance(operation, dict) or not operation.get("operationId") or not operation.get("summary"):
                raise ValueError(f"{path.name}: {method.upper()} {route} needs operationId and summary")
            responses = operation.get("responses")
            if not isinstance(responses, dict) or not responses:
                raise ValueError(f"{path.name}: {method.upper()} {route} needs responses")
            if "requestBody" in operation and not operation["requestBody"].get("content"):
                raise ValueError(f"{path.name}: {method.upper()} {route} requestBody needs content")
    if not operation_count:
        raise ValueError(f"{path.name}: no operations found")
    _check_refs(document, document)
    return {"title": info["title"], "openapi": document["openapi"], "paths": len(paths), "operations": operation_count}


def validate_all() -> list[dict[str, int | str]]:
    return [validate_contract(path, required) for path, required in CONTRACTS.items()]


if __name__ == "__main__":
    try:
        for result in validate_all():
            print(f"PASS {result['title']}: OpenAPI {result['openapi']}, {result['paths']} paths, {result['operations']} operations")
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)

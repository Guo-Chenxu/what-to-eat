from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def _expand_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _dict_to_namespace(value)
    if isinstance(value, list):
        return [_expand_value(item) for item in value]
    if isinstance(value, str):
        return os.path.expandvars(value)
    return value


def _dict_to_namespace(data: dict[str, Any]) -> SimpleNamespace:
    ns = SimpleNamespace()
    for key, value in data.items():
        setattr(ns, key, _expand_value(value))
    return ns


def load_settings(path: Path = _CONFIG_PATH) -> SimpleNamespace:
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return _dict_to_namespace(raw)


settings = load_settings()

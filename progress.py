"""兼容层：老代码从 progress 导入，新代码用 repositories.store。"""
from __future__ import annotations

from repositories.store import (APP_NAME, SCHEMA, ProgressStore, resource_path,
                                today_str, user_data_dir)

__all__ = ["APP_NAME", "SCHEMA", "ProgressStore", "resource_path", "today_str", "user_data_dir"]

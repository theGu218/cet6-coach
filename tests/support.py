"""测试用临时目录：放在项目内（DSH 沙箱对 %TEMP% 的写入会拒绝，工作区可写）。

刻意不用 tempfile.TemporaryDirectory：Windows 下它退出时会 chmod 0700 再删，
在受限环境里会抛 PermissionError；这里直接建目录 + rmtree(ignore_errors=True)。
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

TMP_ROOT = Path(__file__).resolve().parent / ".tmp"
# 每次跑测试前清掉上一轮的临时目录（沙箱里单个目录有时删不掉，ignore_errors 兜底）
shutil.rmtree(TMP_ROOT, ignore_errors=True)


class _WorkspaceTemp:
    def __init__(self) -> None:
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.path = TMP_ROOT / f"t{uuid.uuid4().hex[:12]}"
        self.path.mkdir(parents=True, exist_ok=True)
        self.name = str(self.path)

    def __enter__(self) -> str:
        return self.name

    def __exit__(self, *_exc) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


def temp_dir() -> _WorkspaceTemp:
    return _WorkspaceTemp()

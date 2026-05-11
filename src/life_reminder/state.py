from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class SentStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> set[str]:
        if not self.path.exists():
            return set()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        items = data.get("sent", []) if isinstance(data, dict) else []
        return {str(item) for item in items}

    def has(self, key: str) -> bool:
        return key in self.load()

    def add(self, key: str) -> None:
        sent = self.load()
        sent.add(key)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps({"sent": sorted(sent)}, indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self.path)


@contextmanager
def file_lock(path: Path) -> Iterator[bool]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd: int | None = None
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        os.write(fd, str(os.getpid()).encode("ascii"))
        yield True
    except FileExistsError:
        yield False
    finally:
        if fd is not None:
            os.close(fd)
            try:
                path.unlink()
            except FileNotFoundError:
                pass

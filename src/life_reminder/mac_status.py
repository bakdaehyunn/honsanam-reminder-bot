from __future__ import annotations

import re
import shutil
import subprocess
import time


def collect_status() -> str:
    return "\n".join(
        [
            battery_status(),
            disk_status(),
            memory_status(),
            uptime_status(),
        ]
    )


def battery_status() -> str:
    proc = subprocess.run(["pmset", "-g", "batt"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5)
    match = re.search(r"(\d+)%", proc.stdout)
    if match:
        return f"배터리: {match.group(1)}%"
    return "배터리: 확인 실패"


def disk_status() -> str:
    usage = shutil.disk_usage("/")
    free_gb = usage.free / (1024**3)
    total_gb = usage.total / (1024**3)
    return f"디스크: {free_gb:.0f}GB 여유 / {total_gb:.0f}GB"


def memory_status() -> str:
    try:
        proc = subprocess.run(["vm_stat"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5)
        page_size = 16384
        free_pages = extract_vm_stat(proc.stdout, "Pages free")
        inactive_pages = extract_vm_stat(proc.stdout, "Pages inactive")
        speculative_pages = extract_vm_stat(proc.stdout, "Pages speculative")
        free_gb = (free_pages + inactive_pages + speculative_pages) * page_size / (1024**3)
        return f"메모리: 약 {free_gb:.1f}GB 여유"
    except Exception:
        return "메모리: 확인 실패"


def uptime_status() -> str:
    seconds = int(time.time() - boot_time())
    days, rest = divmod(seconds, 86400)
    hours = rest // 3600
    return f"부팅 후: {days}일 {hours}시간"


def boot_time() -> int:
    proc = subprocess.run(["sysctl", "-n", "kern.boottime"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5)
    match = re.search(r"sec = (\d+)", proc.stdout)
    if not match:
        return int(time.time())
    return int(match.group(1))


def extract_vm_stat(text: str, label: str) -> int:
    match = re.search(rf"{re.escape(label)}:\s+(\d+)\.", text)
    return int(match.group(1)) if match else 0

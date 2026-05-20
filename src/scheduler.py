"""定时扫描调度管理 — 更新 cron 作业"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
CRON_FILE = ROOT / "cron" / "jobs.json"
SCHEDULE_FILE = ROOT / "scan_schedule.json"
SCAN_JOB_ID = "32d053ee"


# ── 默认值 ────────────────────────────────────────────────────────────

def _default_schedule() -> dict:
    return {
        "time": "16:30",
        "days": "1-5",
        "tz": "Asia/Hong_Kong",
    }


# ── 加载 / 保存 ──────────────────────────────────────────────────────

def load_schedule() -> dict:
    """加载当前扫描时间配置，不存在则返回默认值。"""
    if SCHEDULE_FILE.exists():
        try:
            with open(SCHEDULE_FILE) as f:
                data = json.load(f)
            # 补齐可能缺失的键
            for k, v in _default_schedule().items():
                data.setdefault(k, v)
            return data
        except (json.JSONDecodeError, KeyError):
            pass
    return _default_schedule()


def save_schedule(schedule: dict) -> None:
    """保存扫描时间配置并同步到 cron 作业。"""
    s = _default_schedule()
    s.update(schedule)
    _validate(s)
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(s, f, indent=2)
    _sync_to_cron(s)


# ── 验证 ──────────────────────────────────────────────────────────────

def _validate(s: dict) -> None:
    """基本校验，不通过抛 ValueError。"""
    # 时间格式 HH:MM
    # 时间格式 HH:MM
    import re
    if not re.fullmatch(r"\d{2}:\d{2}", s["time"]):
        raise ValueError(f"无效时间: {s['time']}，应为 HH:MM 格式（如 09:30）")
    parts = s["time"].split(":")
    if not (0 <= int(parts[0]) <= 23) or not (0 <= int(parts[1]) <= 59):
        raise ValueError(f"无效时间: {s['time']}，小时 0-23，分钟 0-59")
    # days 格式：数字、逗号、连字符，如 1-5 或 1,3,5
    import re
    if not re.fullmatch(r"[0-6,\-]+", s["days"]):
        raise ValueError(f"无效星期: {s['days']}，应为 0-6（0=周日），如 1-5 或 1,3,5")


# ── 同步到 cron ───────────────────────────────────────────────────────

def _build_cron_expr(time_str: str, days_str: str) -> str:
    """HH:MM + days → cron 表达式"""
    h, m = time_str.split(":")
    return f"{int(m)} {int(h)} * * {days_str}"


def _sync_to_cron(schedule: dict) -> None:
    """将时间配置写回 cron/jobs.json 中的扫描作业。"""
    if not CRON_FILE.exists():
        return

    with open(CRON_FILE) as f:
        data = json.load(f)

    for job in data.get("jobs", []):
        if job.get("id") == SCAN_JOB_ID:
            job["schedule"]["kind"] = "cron"
            job["schedule"]["expr"] = _build_cron_expr(schedule["time"], schedule["days"])
            job["schedule"]["tz"] = schedule["tz"]
            job["schedule"]["atMs"] = None
            job["schedule"]["everyMs"] = None
            break

    with open(CRON_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── 便捷 CLI ──────────────────────────────────────────────────────────

def set_time(time_str: str) -> dict:
    """设置扫描时间并返回更新后的配置。"""
    s = load_schedule()
    s["time"] = time_str
    save_schedule(s)
    return s


def set_days(days_str: str) -> dict:
    """设置扫描日并返回更新后的配置。"""
    s = load_schedule()
    s["days"] = days_str
    save_schedule(s)
    return s


def set_timezone(tz: str) -> dict:
    """设置时区并返回更新后的配置。"""
    s = load_schedule()
    s["tz"] = tz
    save_schedule(s)
    return s


def describe(s: dict) -> str:
    """人类可读的描述。"""
    day_names = {"0": "日", "1": "一", "2": "二", "3": "三", "4": "四", "5": "五", "6": "六"}
    days_parsed = s["days"]
    for num, name in day_names.items():
        days_parsed = days_parsed.replace(num, name)
    return f"⏰ {s['time']} | 📅 周{days_parsed} | 🌍 {s['tz']}"

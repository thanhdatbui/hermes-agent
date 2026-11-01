"""Independent 24h Heartbeat Aggregator for Cron Watchdogs.
Runs at 00:00 UTC (07:00 VN), inspects state files, and emits daily health summary.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

HEALTH_DIR = Path(os.environ.get("CRON_HEALTH_DIR", "D:/Taadaa/runtime/cron_health"))


def load_scheduler_runs() -> Dict[str, Dict[str, Any]]:
    p = Path(os.environ.get("JOBS_CACHE_FILE", Path.home() / "AppData" / "Local" / "hermes" / "cron" / "jobs.json"))
    if not p.exists():
        fallback = Path("D:/Taadaa/Hermes/deploy/hermes-home/cron/jobs.json")
        p = fallback if fallback.exists() else p
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        jobs = data.get("jobs", data) if isinstance(data, dict) else data
        return {j["script"][:-3]: j for j in jobs if (j.get("script") or "").endswith(".py")}
    except Exception:
        return {}


JOBS_FILE = Path(os.environ.get(
    "JOBS_FILE",
    Path(__file__).resolve().parent / "cron" / "jobs.json",
))

WATCHDOG_SPECS = {
    "cron_stale_upload_watchdog": {"interval_h": 24, "chat": "-5435853713"},
    "farm_render_download_watchdog": {"interval_h": 6, "chat": "-5435853713"},
    "cron_hotmail_gpm_lifecycle_6h_report": {"interval_h": 6, "chat": "-5583559484"},
    "cron_gmail_gpm_2fa_6h_report": {"interval_h": 6, "chat": "-5256944036"},
    "cron_gpm_gmail_nurture_6h_report": {"interval_h": 12, "chat": "-5256944036"},
    "sync_onedrive_multicloud": {"interval_h": 6, "chat": "-5373649734"},
    "cron_chatgpt_web_pool_watchdog": {"interval_h": 6, "chat": "-5373649734"},
    "gate_compliance_watchdog": {"interval_h": 6, "chat": "-5373649734"},
}

def evaluate_heartbeat(now: datetime.datetime | None = None) -> Dict[str, Any]:
    sched_runs = load_scheduler_runs()
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
    results = []
    total = len(WATCHDOG_SPECS)
    ok_count = 0
    anom_count = 0
    stale_count = 0

    for name, spec in WATCHDOG_SPECS.items():
        state_file = HEALTH_DIR / f"{name}.json"
        sched_run = sched_runs.get(name, {})
        dt_sched = None
        for field in ("last_run_at", "last_run"):
            value = sched_run.get(field)
            if value:
                try:
                    dt_sched = datetime.datetime.fromisoformat(value)
                    if dt_sched.tzinfo is None:
                        dt_sched = dt_sched.replace(tzinfo=datetime.timezone.utc)
                    break
                except (TypeError, ValueError):
                    continue

        try:
            d = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
            last_end = None
            if d.get("last_end"):
                last_end = datetime.datetime.fromisoformat(d["last_end"])
                if last_end.tzinfo is None:
                    last_end = last_end.replace(tzinfo=datetime.timezone.utc)

            status = d.get("status", "UNKNOWN")
            anomalies = d.get("anomalies", [])

            if dt_sched is not None and (last_end is None or dt_sched > last_end):
                last_end = dt_sched
                if sched_run.get("last_status") == "ok":
                    status = "NOMINAL"
                    anomalies = []
                elif sched_run.get("last_status"):
                    status = "ANOMALY"

            if last_end is None:
                results.append({
                    "name": name,
                    "status": "NO_STATE",
                    "message": "Chưa có state hoặc lịch sử chạy hợp lệ",
                    "icon": "⚪"
                })
                continue

            age_h = round((now - last_end).total_seconds() / 3600.0, 1)
            max_age = spec["interval_h"] * 2 + 0.5

            if age_h > max_age:
                stale_count += 1
                results.append({
                    "name": name,
                    "status": "STALE",
                    "age_h": age_h,
                    "message": f"STALE: Lần cuối {age_h}h trước (vượt trần {max_age}h)",
                    "icon": "❌"
                })
            elif status == "ANOMALY":
                anom_count += 1
                results.append({
                    "name": name,
                    "status": "ANOMALY",
                    "age_h": age_h,
                    "message": f"ANOMALY: {len(anomalies)} sự cố chưa giải quyết",
                    "icon": "⚠️"
                })
            else:
                ok_count += 1
                results.append({
                    "name": name,
                    "status": "OK",
                    "age_h": age_h,
                    "message": f"Hoạt động tốt ({age_h}h trước)",
                    "icon": "✅"
                })
        except Exception as exc:
            anom_count += 1
            results.append({
                "name": name,
                "status": "CORRUPT",
                "message": f"File state bị hỏng: {exc}",
                "icon": "❌"
            })

    return {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total": total,
        "ok_count": ok_count,
        "anom_count": anom_count,
        "stale_count": stale_count,
        "results": results
    }

def render_heartbeat_markdown(hb: Dict[str, Any]) -> str:
    now_str = hb.get("generated_at", "N/A")
    total = hb.get("total", 0)
    ok_count = hb.get("ok_count", 0)
    anom_count = hb.get("anom_count", 0)
    stale_count = hb.get("stale_count", 0)
    summary = f"{ok_count}/{total} OK"
    if anom_count or stale_count:
        summary += f" · {anom_count} ANOMALY · {stale_count} STALE"

    lines = [
        f"💓 *[FARM CRON HEARTBEAT — 24H]*",
        f"⏰ Thời gian: {now_str} (09:00 VN)",
        f"🎯 Tổng quan: *{summary}*",
        "─────────────────────────────",
    ]
    for r in hb.get("results", []):
        lines.append(f"{r['icon']} `{r['name']}`: {r['message']}")
    lines.append("─────────────────────────────")
    lines.append("ℹ️ Chỉ gửi vào 02:00 UTC (09:00 VN) hàng ngày để xác nhận toàn bộ Watchdogs sống khỏe.")
    return "\n".join(lines)

def main():
    hb = evaluate_heartbeat()
    print(render_heartbeat_markdown(hb))

if __name__ == "__main__":
    main()

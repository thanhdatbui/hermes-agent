"""Watchdog script to monitor active device locks and alert on locks held too long."""

from __future__ import annotations

import datetime
import json
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path

DEFAULT_LOCK_ROOT = Path.home() / ".codex" / "device-locks"
ALERT_THRESHOLD_MINUTES = 120  # Cảnh báo nếu lock giữ lâu hơn 2 tiếng

# Nhóm Telegram nhận báo cáo riêng về Device Locks
DEVICE_LOCK_CHAT_ID = os.environ.get("DEVICE_LOCK_ALERT_CHAT_ID") or "-5518578446"


def get_telegram_bot_token() -> str | None:
    # Lấy token từ hermes config hoặc env
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if token:
        return token
    hermes_cfg_path = Path.home() / "AppData/Local/hermes/config.yaml"
    if hermes_cfg_path.exists():
        try:
            import yaml
            with open(hermes_cfg_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
                token = cfg.get("telegram", {}).get("bot_token") or cfg.get("telegram_token")
                if token:
                    return str(token)
        except Exception:
            pass
    # Fallback: đọc trực tiếp từ file .env của Hermes (token không được nạp vào env khi cron chạy)
    env_path = Path.home() / "AppData/Local/hermes/.env"
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if token:
                        return token
        except Exception:
            pass
    return None


def send_telegram_alert(text: str, chat_id: str = DEVICE_LOCK_CHAT_ID) -> bool:
    token = get_telegram_bot_token()
    if not token:
        print("[watchdog] TELEGRAM_BOT_TOKEN not found, outputting to console only:")
        print(text)
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[watchdog] Failed to send Telegram alert: {e}")
        return False


def scan_active_locks(lock_root: Path = DEFAULT_LOCK_ROOT) -> list[dict]:
    if not lock_root.exists():
        return []

    active_locks = []
    seen_machines = set()

    for p in lock_root.glob("machine_*.lock.json"):
        try:
            raw = p.read_text(encoding="utf-8")
            data = json.loads(raw)
            mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime)
            now = datetime.datetime.now()
            duration_minutes = int((now - mtime).total_seconds() / 60)

            # Support diverse schema: machine or stt or parse from filename machine_XX.lock.json
            machine = data.get("machine")
            if machine is None:
                machine = data.get("stt")
            if machine is None:
                m_match = re.search(r"machine_(\d+)", p.name)
                if m_match:
                    machine = int(m_match.group(1))

            if machine is not None:
                try:
                    m_val = int(machine)
                    if m_val < 1 or (m_val > 80 and not (201 <= m_val <= 280)):
                        continue
                except (ValueError, TypeError):
                    pass

            if machine in seen_machines:
                continue
            if machine is not None:
                seen_machines.add(machine)

            status = data.get("status", "unknown")
            project = data.get("project") or data.get("owner", "unknown")
            pid = data.get("pid", "?")
            command = data.get("command", "")
            serial = data.get("serial") or data.get("device_id", "")

            active_locks.append({
                "machine": machine,
                "serial": serial,
                "project": project,
                "status": status,
                "pid": pid,
                "duration_minutes": duration_minutes,
                "mtime": mtime.strftime("%H:%M %d/%m"),
                "file_path": str(p),
            })
        except Exception as e:
            print(f"[watchdog] Error reading {p}: {e}")

    return sorted(active_locks, key=lambda x: int(x["machine"]) if str(x["machine"]).isdigit() else str(x["machine"]))


def run_watchdog():
    # 0. Tự động dọn dẹp các lock đã hết hạn TTL hoặc dead-owner trước khi quét báo cáo
    reap_script = Path("D:/Taadaa/tiktok-luot nuoi acc/scripts/reap-dead-owner-locks.py")
    if reap_script.exists():
        try:
            py_bin = r"D:\Taadaa\python-envs\automation\Scripts\python.exe"
            if not Path(py_bin).exists():
                py_bin = sys.executable
            import subprocess
            subprocess.run([py_bin, "-B", str(reap_script)], timeout=60, capture_output=True, check=False)
        except Exception as e:
            print(f"[watchdog] Warning: failed to run reap script preflight: {e}")

    locks = scan_active_locks()
    if not locks:
        print("[watchdog] Healthy: No active device locks found.")
        return 0

    overdue_locks = [l for l in locks if l["duration_minutes"] >= ALERT_THRESHOLD_MINUTES]
    
    # Tạo nội dung báo cáo
    now_str = datetime.datetime.now().strftime("%H:%M %d/%m/%Y")
    lines = [
        f"🔒 <b>[DANH SÁCH MÁY ĐANG LOCK]</b> - <i>{now_str}</i>",
        f"Tổng số máy đang giữ lock: <b>{len(locks)}</b>",
        ""
    ]

    for l in locks:
        m_str = f"Máy {int(l['machine']):02d}" if isinstance(l['machine'], int) or str(l['machine']).isdigit() else f"Máy {l['machine']}"
        warning = " ⚠️ (QUÁ HẠN > 2H)" if l["duration_minutes"] >= ALERT_THRESHOLD_MINUTES else ""
        lines.append(f"• <b>[{m_str}]</b>: {l['project']} (PID {l['pid']})")
        lines.append(f"  └ Trạng thái: <code>{l['status']}</code> | Đã lock: <b>{l['duration_minutes']} phút</b> (từ {l['mtime']}){warning}")

    lines.append("")
    lines.append("👉 <i>Gõ \"Mở khóa máy XX\" hoặc \"Unlock all\" nếu đã xử lý xong.</i>")

    report_text = "\n".join(lines)
    print(report_text)

    # Gửi cập nhật báo cáo máy đang lock về Telegram bất kể quá hạn hay chưa
    if locks:
        send_telegram_alert(report_text)

    return 0


if __name__ == "__main__":
    sys.exit(run_watchdog())

#!/usr/bin/env python3
"""Silent Stale Watchdog for Hermes Phone Farm.

Monitors watchdog_state.json and farm_coordinator_phase.json per session.
Alerts only when execution is truly stuck (>10m for normal tools, >25m for canary).
Completely silent (no output, exit 0) when normal or within threshold.
Anti-spam: alerts at most once per stall incident per session (stale_alert_sent.json).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Ép UTF-8 cho stdout
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes"))
WATCHDOG_STATE_FILE = HERMES_HOME / "watchdog_state.json"
PHASE_FILE = HERMES_HOME / "farm_coordinator_phase.json"
ALERT_CACHE_FILE = HERMES_HOME / "stale_alert_sent.json"

CANARY_THRESHOLD_SECONDS = 1500.0   # 25 minutes for real device canary
DEFAULT_THRESHOLD_SECONDS = 600.0   # 10 minutes for normal code fix / inspect / tools
WORKER_TIMEOUT_SECONDS = 1200.0     # 20 minutes for worker execution

MAX_ACTIVE_AGE_SECONDS = 7200.0     # Ignore stale sessions older than 2 hours


def _load_json(path: Path) -> dict:
    for attempt in range(3):
        try:
            if not path.is_file():
                return {}
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                data = json.loads(content)
                return data if isinstance(data, dict) else {}
        except (PermissionError, OSError, json.JSONDecodeError):
            if attempt < 2:
                time.sleep(0.05)
                continue
            return {}
        except Exception:
            return {}
    return {}


def _save_json(path: Path, data: dict) -> None:
    tmp = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.parent / f"{path.name}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        if tmp and tmp.is_file():
            try:
                tmp.unlink()
            except OSError:
                pass


def main() -> int:
    try:
        watchdog_data = _load_json(WATCHDOG_STATE_FILE)
        watchdog_sessions = watchdog_data.get("sessions", {}) if isinstance(watchdog_data, dict) else {}
        # Hỗ trợ backward compatibility nếu watchdog_state là flat dict cũ
        if not watchdog_sessions and isinstance(watchdog_data, dict) and "last_beat" in watchdog_data:
            legacy_sid = str(watchdog_data.get("session_id") or "__default__")
            watchdog_sessions = {legacy_sid: watchdog_data}

        phase_data = _load_json(PHASE_FILE)
        phase_sessions = phase_data.get("sessions", {}) if isinstance(phase_data, dict) else {}

        if not isinstance(phase_sessions, dict) or not phase_sessions:
            if ALERT_CACHE_FILE.is_file():
                try:
                    ALERT_CACHE_FILE.unlink()
                except OSError:
                    pass
            return 0

        now = time.time()

        # Đọc anti-spam cache theo format per-session
        alert_cache = _load_json(ALERT_CACHE_FILE)
        alert_sessions = alert_cache.get("sessions")
        if not isinstance(alert_sessions, dict):
            alert_sessions = {}
            if "session_id" in alert_cache and "alerted_beat" in alert_cache:
                old_sid = str(alert_cache["session_id"])
                alert_sessions[old_sid] = {
                    "alerted_beat": alert_cache.get("alerted_beat"),
                    "alerted_at": alert_cache.get("alerted_at", now),
                    "elapsed": alert_cache.get("elapsed", 0),
                    "threshold": alert_cache.get("threshold", 600),
                }
            alert_cache = {"sessions": alert_sessions}

        cache_updated = False
        active_monitored_sids = set()

        # Lặp qua từng session đang ở phase WORKER_RUNNING hoặc ALERT
        for sid, sdata in phase_sessions.items():
            if not isinstance(sdata, dict):
                continue
            phase = sdata.get("phase")
            d_at = float(sdata.get("dispatched_at", 0) or sdata.get("updated_at", 0) or 0)
            if phase not in ("WORKER_RUNNING", "ALERT"):
                continue
            if now - d_at > MAX_ACTIVE_AGE_SECONDS:
                continue

            active_monitored_sids.add(sid)

            w_state = None
            matched_sid = sid
            tool = "unknown"
            incident_beat = 0.0
            elapsed = 0.0
            threshold = DEFAULT_THRESHOLD_SECONDS
            is_canary = False

            if phase == "WORKER_RUNNING":
                # Coordinator đang im lặng hợp pháp để chờ worker con làm việc.
                # BẮT BUỘC ưu tiên tìm session con có parent_session_id == sid trước
                child_candidates = [
                    (csid, cstate) for csid, cstate in watchdog_sessions.items()
                    if isinstance(cstate, dict) and cstate.get("parent_session_id") == sid
                ]
                if child_candidates:
                    child_candidates.sort(
                        key=lambda pair: pair[1].get("current_tool_start") or pair[1].get("last_beat") or 0,
                        reverse=True,
                    )
                    matched_sid, w_state = child_candidates[0]

                    current_tool_start = w_state.get("current_tool_start")
                    last_beat = w_state.get("last_beat")

                    if current_tool_start and isinstance(current_tool_start, (int, float)) and current_tool_start > 0:
                        elapsed = max(0.0, now - float(current_tool_start))
                        tool = w_state.get("current_tool") or "unknown"
                        incident_beat = float(current_tool_start)
                    elif last_beat and isinstance(last_beat, (int, float)) and last_beat > 0:
                        elapsed = max(0.0, now - float(last_beat))
                        tool = w_state.get("tool") or "unknown"
                        incident_beat = float(last_beat)
                    else:
                        continue

                    is_canary = bool(w_state.get("is_canary", False))
                    threshold = CANARY_THRESHOLD_SECONDS if is_canary else DEFAULT_THRESHOLD_SECONDS
                else:
                    # CHƯA CÓ child session (worker mới spawn hoặc chưa gọi tool):
                    # Ngưỡng chờ phải là WORKER_TIMEOUT_SECONDS = 1200.0 tính từ dispatched_at (thay vì 600s)
                    # để không bao giờ báo giả trước khi worker hết ngân sách 20 phút.
                    elapsed = max(0.0, now - d_at)
                    threshold = WORKER_TIMEOUT_SECONDS
                    tool = "worker_spawn"
                    incident_beat = d_at
                    matched_sid = sid
            else:
                # phase == "ALERT": Coordinator đang ở hiện trường, ngưỡng 600s áp dụng cho Coordinator bình thường
                w_state = watchdog_sessions.get(sid)
                if not w_state or not isinstance(w_state, dict):
                    continue

                current_tool_start = w_state.get("current_tool_start")
                last_beat = w_state.get("last_beat")

                if current_tool_start and isinstance(current_tool_start, (int, float)) and current_tool_start > 0:
                    elapsed = max(0.0, now - float(current_tool_start))
                    tool = w_state.get("current_tool") or "unknown"
                    incident_beat = float(current_tool_start)
                elif last_beat and isinstance(last_beat, (int, float)) and last_beat > 0:
                    elapsed = max(0.0, now - float(last_beat))
                    tool = w_state.get("tool") or "unknown"
                    incident_beat = float(last_beat)
                else:
                    continue

                is_canary = bool(w_state.get("is_canary", False))
                threshold = CANARY_THRESHOLD_SECONDS if is_canary else DEFAULT_THRESHOLD_SECONDS

            # Kiểm tra vượt ngưỡng
            if elapsed > threshold:
                cached_alert = alert_sessions.get(sid)
                if cached_alert and isinstance(cached_alert, dict):
                    cached_beat = cached_alert.get("alerted_beat")
                    if cached_beat is not None and abs(float(cached_beat) - incident_beat) < 5.0:
                        # Đã alert cho incident beat này rồi -> im lặng tuyệt đối
                        continue

                # Chưa alert -> ghi nhận cache và in cảnh báo
                alert_sessions[sid] = {
                    "alerted_beat": incident_beat,
                    "session_id": sid,
                    "matched_session_id": matched_sid,
                    "alerted_at": now,
                    "elapsed": elapsed,
                    "threshold": threshold,
                }
                cache_updated = True

                elapsed_minutes = elapsed / 60.0
                threshold_minutes = threshold / 60.0
                mode_desc = "Canary máy thật" if is_canary else "Thao tác thường"
                display_sid = sid if matched_sid == sid else f"{matched_sid} (parent: {sid})"

                now_iso = time.strftime("%Y-%m-%d %H:%M:%S")
                print(
                    f"⚠️ [CẢNH BÁO HERMES TREO - {now_iso}]\n"
                    f"Session `{display_sid}` đang im lặng {elapsed_minutes:.0f} phút (vượt ngưỡng {threshold_minutes:.0f}m)!\n"
                    f"- Tool: {tool}\n"
                    f"- Chế độ: {mode_desc}\n"
                    f"- Session ID: {display_sid}\n"
                    f"Vui lòng kiểm tra terminal hoặc can thiệp nếu cần."
                )
            else:
                # Trong ngưỡng: nếu có beat mới hơn alert cũ thì dọn cache
                cached_alert = alert_sessions.get(sid)
                if cached_alert and isinstance(cached_alert, dict):
                    cached_beat = cached_alert.get("alerted_beat")
                    if cached_beat is not None and incident_beat > float(cached_beat):
                        alert_sessions.pop(sid, None)
                        cache_updated = True

        # Dọn dẹp cache cho các session không còn active
        stale_alert_sids = [s for s in alert_sessions if s not in active_monitored_sids]
        if stale_alert_sids:
            for s in stale_alert_sids:
                alert_sessions.pop(s, None)
            cache_updated = True

        if cache_updated:
            if alert_sessions:
                _save_json(ALERT_CACHE_FILE, alert_cache)
            elif ALERT_CACHE_FILE.is_file():
                try:
                    ALERT_CACHE_FILE.unlink()
                except OSError:
                    pass

        return 0
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())

"""Farm Coordinator Guard Plugin for Hermes v2.0.

Two-Tier Enforcement (State Guard + Action Guard):
1. STATE GUARD (Per-session scoped):
   - Phase ALERT:
     * Investigative tools (read_file, search_files, patch, write_file, execute_code) are hard-blocked.
     * Only 1 inspect command (inspect_machine.py <N> or adb devices) allowed via terminal.
     * Any subsequent terminal call in the coordinator session is hard-blocked until delegate_task.
     * skill_view and delegate_task are always permitted.
   - Phase WORKER_RUNNING: Auto-expires after 20 minutes to prevent deadlock.
   - Phase CLOSEOUT: Terminal and tools open for 6 Gate (commit, rebase, push, docs, canary).
   - Phase IDLE: Normal operation for O(1) commands.

2. ACTION GUARD (Always active, even in IDLE):
   - Allowlist: O(1) ops (git status/diff/commit/push, py_compile, psutil, adb devices, inspect_machine)
   - Denylist: Long-running batch/automation scripts (.ps1, batch runners, playwright, reg, upload, checkmail)
     and multi-line python probe scripts (python -c with loops/subprocess/automations).
     MUST be dispatched via delegate_task; hard-blocked if attempted in coordinator session.
   - Escape Token: Subagents (parent_session_id in state.db OR TAADAA_WORKER=1 in process env)
     are never blocked.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

STATE_FILE = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes")) / "farm_coordinator_phase.json"
STATE_LOCK_FILE = STATE_FILE.with_suffix(".lock")
WORKER_TIMEOUT_SECONDS = 1200  # 20 minutes auto-reset to avoid deadlock
CLOSEOUT_TIMEOUT_SECONDS = 7200  # 2 hours auto-reset for CLOSEOUT phase
SESSION_EXPIRY_SECONDS = 7200  # 2 hours auto-cleanup for stale sessions

# --- INVESTIGATIVE TOOLS (Cấm tuyệt đối ở session Coordinator trong Phase ALERT) ---
INVESTIGATIVE_TOOLS = {
    "read_file",
    "search_files",
    "patch",
    "write_file",
    "execute_code",
}

# --- TẦNG 1: ALLOWLIST (O(1) commands - luôn cho qua khi không ở ALERT) ---
ALLOWLIST_PATTERNS = [
    r"^\s*git\s+(status|log|diff|add|commit|push|pull|fetch|stash|branch|checkout)\b",
    r"^\s*(ls|cat|head|tail|wc|grep|rg|pwd|echo|which|whoami)\b",
    r"\bpsutil\b",
    r"\btasklist\b",
    r"\bGet-Process\b",
    r"^\s*adb\s+devices\b",
    r"^\s*python\s+.*inspect_machine\.py\b",
    r"^\s*python\s+.*-m\s+py_compile\b",
    r"^\s*python\s+--version\b",
    r"^\s*claude\s+-p\b",  # Cho phép gọi Claude CLI tư vấn
]

# --- TẦNG 3: DENYLIST (Long-runners & Python probe cấm chạy ở session chính) ---
DENYLIST_PATTERNS = [
    r"\brun_.*batch.*\.ps1\b",
    r'(?:"[^"]*"|\x27[^\x27]*\x27|\S+)\.ps1\b',
    r"\bupload[_-]?video\b",
    r"\bupload_tik\b",
    r"\bcheckmail\b",
    r"\breg[_-]?(tiktok|gmail)\b",
    r"\bplaywright\b",
    r"\bpython\b.*\b(run_batch|batch_|run_all|check_live|s7_helper|untouched_proxies)\b",
    r"\bpython\s+-c\b.*(subprocess|playwright|while|for\s+.*in|openpyxl|adb|exec|importlib)\b",
    r"\bfor\b.*\bin\b.*;\s*do\b",
    r"\bwhile\s*\(\s*\$true\s*\)",
    r"\bgpm\b.*\b(proxy|auto|script)\b",
]


def _is_worker_session(session_id: str) -> bool:
    """Check if session is an autonomous worker subagent (escape token)."""
    if not session_id:
        return False
    if os.environ.get("TAADAA_WORKER") == "1":
        return True
    try:
        db_path = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes")) / "state.db"
        if db_path.is_file():
            with sqlite3.connect(str(db_path), timeout=2.0) as con:
                row = con.execute("SELECT parent_session_id FROM sessions WHERE id = ?", (session_id,)).fetchone()
                if row and row[0]:  # Có parent_session_id -> CHẮC CHẮN là Worker Subagent
                    return True
    except Exception as exc:
        logger.debug("[FARM_GUARD] Error querying worker status for session %s: %s", session_id, exc)
    return False


@contextmanager
def _state_lock():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd = None
    deadline = time.time() + 2.0
    while time.time() < deadline:
        try:
            if STATE_LOCK_FILE.exists():
                try:
                    if time.time() - STATE_LOCK_FILE.stat().st_mtime > 10:
                        STATE_LOCK_FILE.unlink()
                except OSError:
                    pass
            fd = os.open(str(STATE_LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            time.sleep(0.05)
        except Exception:
            break
    try:
        yield
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass
            try:
                if STATE_LOCK_FILE.exists():
                    STATE_LOCK_FILE.unlink()
            except OSError:
                pass


def _cleanup_sessions(sessions: Dict[str, Any], now: float) -> None:
    stale_keys = []
    for sid, sdata in sessions.items():
        if not isinstance(sdata, dict):
            stale_keys.append(sid)
            continue
        updated_at = sdata.get("updated_at") or sdata.get("dispatched_at") or sdata.get("closeout_at") or 0
        if now - updated_at > SESSION_EXPIRY_SECONDS:
            stale_keys.append(sid)
            continue

        # Per-session phase timeouts
        phase = sdata.get("phase")
        if phase == "WORKER_RUNNING":
            dispatched_at = sdata.get("dispatched_at", 0)
            if now - dispatched_at > WORKER_TIMEOUT_SECONDS:
                logger.info("[FARM_GUARD] WORKER_RUNNING timed out after 20m for session %s -> Resetting to IDLE", sid)
                sdata["phase"] = "IDLE"
                sdata["inspect_budget"] = 0
                sdata["updated_at"] = now
        elif phase == "CLOSEOUT":
            closeout_at = sdata.get("closeout_at", 0)
            if now - closeout_at > CLOSEOUT_TIMEOUT_SECONDS:
                logger.info("[FARM_GUARD] CLOSEOUT expired after 2h for session %s -> Resetting to IDLE", sid)
                sdata["phase"] = "IDLE"
                sdata["inspect_budget"] = 0
                sdata["updated_at"] = now

    for sid in stale_keys:
        sessions.pop(sid, None)


def _load_state_file() -> Dict[str, Any]:
    try:
        if STATE_FILE.is_file():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "sessions" not in data:
                        data = {"sessions": {}}
                    return data
    except Exception as exc:
        logger.debug("[FARM_GUARD] Error reading state file: %s", exc)
    return {"sessions": {}}


def _save_state_file(data: Dict[str, Any]) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp_file = STATE_FILE.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp_file.replace(STATE_FILE)
    except Exception as exc:
        logger.debug("[FARM_GUARD] Error writing state file: %s", exc)


def _get_session_state(session_id: str) -> Dict[str, Any]:
    key = session_id or "__default__"
    now = time.time()
    with _state_lock():
        data = _load_state_file()
        sessions = data.setdefault("sessions", {})
        _cleanup_sessions(sessions, now)
        if key not in sessions:
            sessions[key] = {
                "phase": "IDLE",
                "inspect_budget": 0,
                "dispatched_at": 0.0,
                "closeout_at": 0.0,
                "updated_at": now,
            }
        _save_state_file(data)
        return dict(sessions[key])


def _update_session_state(session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    key = session_id or "__default__"
    now = time.time()
    with _state_lock():
        data = _load_state_file()
        sessions = data.setdefault("sessions", {})
        _cleanup_sessions(sessions, now)
        current = sessions.setdefault(key, {
            "phase": "IDLE",
            "inspect_budget": 0,
            "dispatched_at": 0.0,
            "closeout_at": 0.0,
        })
        current.update(updates)
        current["updated_at"] = now
        _save_state_file(data)
        return dict(current)


# Backward-compatibility helpers
def _read_state(session_id: str = "") -> Dict[str, Any]:
    return _get_session_state(session_id)


def _write_state(state: Dict[str, Any], session_id: str = "") -> None:
    _update_session_state(session_id, state)


def _on_pre_llm_call(
    session_id: str = "",
    user_message: str = "",
    conversation_history: list = None,
    is_first_turn: bool = False,
    model: str = "",
    platform: str = "",
    **kwargs: Any,
) -> Optional[Dict[str, str]]:
    """Detect phase transitions from user message per session."""
    if not user_message:
        return None

    # Worker subagents are completely unconstrained
    if _is_worker_session(session_id):
        return None

    msg = user_message.strip()

    # Reset override
    if re.search(r"^/(reset_guard|guard_off|unblock)\b|reset\s+farm\s+guard", msg, re.IGNORECASE):
        _update_session_state(session_id, {
            "phase": "IDLE",
            "inspect_budget": 0,
        })
        logger.info("[FARM_GUARD] Guard manually reset to IDLE for session %s", session_id)
        return {"context": "[FARM GUARD]: Phase đã reset về IDLE."}

    # Closeout / Chốt phiên
    if re.search(r"chốt\s+phiên|đóng\s+phiên|chốt\s+session|/closeout|kết\s+thúc\s+phiên", msg, re.IGNORECASE):
        _update_session_state(session_id, {
            "phase": "CLOSEOUT",
            "inspect_budget": 0,
            "closeout_at": time.time(),
        })
        logger.info("[FARM_GUARD] Transition to CLOSEOUT phase for session %s", session_id)
        return {"context": "[FARM GUARD]: Đã chuyển sang Phase CLOSEOUT (Chốt phiên 6 Gate). Terminal đã mở khóa cho các lệnh git, canary và review."}

    # Farm Alert
    is_alert = bool(
        re.search(r"\[MÁY\s+\d+\]|\[FARM\s+ALERT|Farm\s+Alert|sự\s+cố\s+máy\s+\d+", msg, re.IGNORECASE)
    )
    if is_alert:
        _update_session_state(session_id, {
            "phase": "ALERT",
            "inspect_budget": 1,
            "alert_snippet": msg[:120],
        })
        logger.info("[FARM_GUARD] Transition to ALERT phase for session %s (budget=1)", session_id)
        return {
            "context": (
                "[FARM GUARD HARD CONSTRAINT]:\n"
                "Hệ thống đang ở Phase ALERT. Ngân sách inspect O(1) = 1 lệnh duy nhất (inspect_machine.py <N> hoặc adb devices).\n"
                "Toàn bộ tool đọc/tìm kiếm/sửa file (read_file, search_files, patch, write_file, execute_code) BỊ KHÓA.\n"
                "Sau khi inspect xong (hoặc nếu không inspect), CẤM TUYỆT ĐỐI Coordinator chạy terminal điều tra sâu (grep/log/probe/test) ở session chính.\n"
                "Mọi tool điều tra sẽ bị PRE-TOOL-USE HOOK CHẶN ĐỨNG.\n"
                "Hành động hợp lệ tiếp theo là gọi tool delegate_task(...) để Worker Subagent xử lý trong context riêng."
            )
        }

    # Nếu người dùng gửi tin nhắn hỏi đáp bình thường trong khi đang WORKER_RUNNING:
    # Cho phép chuyển về IDLE để tương tác nếu đã qua 5 phút
    sess_state = _get_session_state(session_id)
    if sess_state.get("phase") == "WORKER_RUNNING":
        dispatched_time = sess_state.get("dispatched_at", 0)
        if time.time() - dispatched_time > 300:
            _update_session_state(session_id, {"phase": "IDLE"})

    return None


def _on_pre_tool_call(
    tool_name: str = "",
    args: Any = None,
    task_id: str = "",
    session_id: str = "",
    **kwargs: Any,
) -> Optional[Dict[str, str]]:
    """Enforce State Guard (ALERT/WORKER) and Action Guard (Long-Runners) per session."""
    # TẦNG 2: ESCAPE TOKEN — Subagents (parent_session_id trong DB HOẶC TAADAA_WORKER=1)
    if _is_worker_session(session_id):
        return None

    # Khi Coordinator gọi delegate_task, chuyển trạng thái session sang WORKER_RUNNING
    if tool_name == "delegate_task":
        _update_session_state(session_id, {
            "phase": "WORKER_RUNNING",
            "dispatched_at": time.time(),
        })
        logger.info("[FARM_GUARD] delegate_task called -> Phase transitioned to WORKER_RUNNING for session %s", session_id)
        return None

    # Tool skill_view: luôn cho phép đọc skill để Coordinator nắm quy tắc
    if tool_name == "skill_view":
        return None

    sess_state = _get_session_state(session_id)
    phase = sess_state.get("phase", "IDLE")

    # 1. State Guard: Phase ALERT
    if phase == "ALERT":
        # Chặn toàn bộ Investigative Tools ở Phase ALERT
        if tool_name in INVESTIGATIVE_TOOLS:
            logger.warning("[FARM_GUARD] Blocked investigative tool '%s' in ALERT phase for session %s", tool_name, session_id)
            return {
                "action": "block",
                "message": (
                    f"⛔ [FARM GUARD - PHASE: ALERT] TOOL `{tool_name}` BỊ CHẶN BỞI PRE-TOOL-USE HOOK:\n"
                    "Coordinator CẤM TUYỆT ĐỐI tự ý đọc file, tìm kiếm code hoặc sửa file trong session chính khi có sự cố Farm!\n"
                    "Việc tự điều tra sẽ làm tràn context và chậm trễ phản ứng các máy khác.\n\n"
                    "HÀNH ĐỘNG BẮT BUỘC:\n"
                    "Gọi tool `delegate_task(goal=..., context=...)` ngay lập tức để Worker Subagent xử lý trong context riêng!"
                ),
            }

        # Kiểm tra tool terminal ở Phase ALERT: chỉ cho phép 1 lệnh O(1) thỏa inspect_machine.py hoặc adb devices
        if tool_name == "terminal":
            cmd = ""
            if isinstance(args, dict):
                cmd = (args.get("command") or "").strip()

            is_inspect = bool(re.search(r"inspect_machine\.py\s+\d+|adb\s+devices", cmd))
            budget = sess_state.get("inspect_budget", 0)
            if is_inspect and budget > 0:
                _update_session_state(session_id, {"inspect_budget": budget - 1})
                logger.info("[FARM_GUARD] Allowed 1 inspect command in ALERT phase, budget consumed for session %s", session_id)
                return None

            logger.warning("[FARM_GUARD] Blocked terminal in ALERT phase for session %s: %s", session_id, cmd[:80])
            return {
                "action": "block",
                "message": (
                    "⛔ [FARM GUARD - PHASE: ALERT] BỊ CHẶN BỞI PRE-TOOL-USE HOOK:\n"
                    "Bạn đã dùng hết ngân sách 1 lệnh inspect O(1) (hoặc lệnh này không phải inspect_machine.py/adb devices).\n"
                    "CẤM TUYỆT ĐỐI Coordinator chạy terminal điều tra sâu (grep/log/probe/test) ở session chính!\n\n"
                    "HÀNH ĐỘNG HỢP LỆ DUY NHẤT BÂY GIỜ LÀ: Gọi tool `delegate_task(goal=..., context=...)` ngay lập tức để Worker Subagent xử lý trong context riêng."
                ),
            }

    # 2. State Guard: Phase WORKER_RUNNING
    if phase == "WORKER_RUNNING":
        if tool_name == "terminal":
            cmd = ""
            if isinstance(args, dict):
                cmd = (args.get("command") or "").strip()
            is_benign = bool(re.search(r"^git\s+(status|diff|log)|psutil|python.*canary", cmd))
            if not is_benign:
                logger.warning("[FARM_GUARD] Blocked terminal in WORKER_RUNNING phase for session %s: %s", session_id, cmd[:80])
                return {
                    "action": "block",
                    "message": (
                        "⛔ [FARM GUARD - PHASE: WORKER_RUNNING] Worker subagent đang chạy trong background.\n"
                        "Coordinator KHÔNG ĐƯỢC tự ý chạy terminal điều tra tại session chính trong lúc worker đang làm việc."
                    ),
                }

    # 3. State Guard: Phase CLOSEOUT -> Cho phép toàn bộ 6 Gate
    if phase == "CLOSEOUT":
        return None

    # 4. Action Guard (Áp dụng cho IDLE hoặc các phase còn lại đối với terminal):
    if tool_name == "terminal":
        cmd = ""
        if isinstance(args, dict):
            cmd = (args.get("command") or "").strip()

        # Tầng 1: Allowlist O(1)
        if any(re.search(p, cmd, re.IGNORECASE) for p in ALLOWLIST_PATTERNS):
            return None

        # Tầng 3: Denylist (Long-runners & Python probe)
        if any(re.search(p, cmd, re.IGNORECASE) for p in DENYLIST_PATTERNS):
            logger.warning("[FARM_GUARD] Blocked LONG-RUNNER in session %s: %s", session_id, cmd[:80])
            return {
                "action": "block",
                "message": (
                    "⛔ [FARM GUARD - LONG-RUNNER BLOCKED] BỊ CHẶN BỞI PRE-TOOL-USE HOOK:\n"
                    f"Lệnh: `{cmd[:100]}`\n"
                    "Đây là script batch / automation dài hơi (hoặc python probe nhiều dòng). "
                    "CẤM TUYỆT ĐỐI chạy đồng bộ ở session chính vì sẽ làm treo phiên chat và tràn context (Context Bloat)!\n\n"
                    "HÀNH ĐỘNG BẮT BUỘC:\n"
                    "Gọi tool `delegate_task(goal=..., context=...)` để Worker Subagent xử lý trong background!"
                ),
            }

    return None


def register(ctx: Any) -> None:
    """Register lifecycle hooks with Hermes."""
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
    logger.info("[FARM_GUARD] farm-coordinator-guard (v2.0 Session-Scoped + Multi-Tool Lock) registered successfully")

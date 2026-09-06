"""Farm Coordinator Guard Plugin for Hermes v2.1.

Two-Tier Enforcement (State Guard + Action Guard) + WorkerToolGate:
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

3. WORKER TOOL GATE (Anti-Analysis Paralysis for Worker Subagents):
   - Escape token recognized via parent_session_id in state.db or TAADAA_WORKER=1.
   - READ_BUDGET = 3: read_file/search_files hard-blocked after 3 calls.
   - WRITE_DEADLINE = 4: reading hard-blocked if call_count >= 4 and write_count == 0.
   - write_file and patch are always permitted; test/compile tools permitted after patching.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

STATE_FILE = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes")) / "farm_coordinator_phase.json"
STATE_LOCK_FILE = STATE_FILE.with_suffix(".lock")
WATCHDOG_STATE_FILE = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes")) / "watchdog_state.json"
WATCHDOG_LOCK_FILE = WATCHDOG_STATE_FILE.with_suffix(".lock")
CLAUDE_LOCKOUT_FILE = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes")) / "claude_lockout.json"
CLAUDE_USAGE_FILE = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes")) / "claude_usage.json"
WORKER_TIMEOUT_SECONDS = 1200  # 20 minutes auto-reset to avoid deadlock
CLOSEOUT_TIMEOUT_SECONDS = 7200  # 2 hours auto-reset for CLOSEOUT phase
SESSION_EXPIRY_SECONDS = 7200  # 2 hours auto-cleanup for stale sessions

# --- WORKER TOOL GATE CONSTANTS & STATE ---
READ_BUDGET = int(os.environ.get("WORKER_READ_BUDGET", 3))
WRITE_DEADLINE = int(os.environ.get("WORKER_WRITE_DEADLINE", 4))
MAX_WORKER_CALLS = int(os.environ.get("WORKER_MAX_CALLS", 12))
POPUP_SELECTOR_PATTERN = re.compile(r"\b(?:popup|allowlist|survey|ads?|selector|advert)\b", re.IGNORECASE)


def is_monolith_smoke(path_str: str) -> bool:
    """Check if a path or command points to a monolith flow (*_smoke.py) at any directory depth."""
    if not path_str:
        return False
    norm = path_str.replace("\\", "/").lower()
    if "feed_swipe_smoke" in norm:
        return True
    if "_smoke.py" in norm and ("flows" in norm or "flow" in norm):
        return True
    parts = re.split(r"[/ \t\'\"]+", norm)
    if any(p.endswith("_smoke.py") for p in parts) and any("flow" in p for p in parts):
        return True
    return False


def is_safe_terminal_verify(cmd: str) -> bool:
    """Strictly validate safe verification commands for worker subagents.
    
    Rules:
    1. Cấm tuyệt đối chứa file monolith flow.
    2. Chặn đứng ký tự shell chaining, redirection, subshell, comment, background, env-expansion:
       ; & | # ` $ > < % \n \r \t
    3. Chỉ cho phép đúng 3 nhóm lệnh an toàn:
       - py_compile: python[3] -m py_compile <file> (file không được là monolith)
       - git status: git status [--short|-s] [<path>]
       - git diff: git diff [<path>] (cấm flag --output, --ext-diff, path không được là monolith)
    """
    if not cmd or not cmd.strip():
        return False
    cmd_clean = cmd.strip()

    if is_monolith_smoke(cmd_clean):
        return False

    FORBIDDEN_CHARS = [";", "&", "|", "#", "`", "$", ">", "<", "%", "\n", "\r", "\t"]
    if any(ch in cmd_clean for ch in FORBIDDEN_CHARS):
        return False

    try:
        tokens = shlex.split(cmd_clean, posix=False)
        tokens = [t.strip("\"'") for t in tokens if t.strip("\"'")]
    except Exception:
        return False

    if not tokens:
        return False

    t0 = Path(tokens[0]).stem.lower()

    if t0 == "git":
        if len(tokens) >= 2:
            sub = tokens[1].lower()
            if sub == "status":
                return True
            if sub == "diff":
                for tok in tokens[2:]:
                    t_low = tok.lower()
                    if t_low.startswith("--output") or t_low.startswith("--ext-diff") or t_low.startswith("--no-index"):
                        return False
                    if is_monolith_smoke(t_low):
                        return False
                return True
        return False

    if t0 == "python" or t0.startswith("python3"):
        if len(tokens) >= 3 and tokens[1] == "-m" and tokens[2] == "py_compile":
            for tok in tokens[3:]:
                if is_monolith_smoke(tok):
                    return False
            return True
        return False

    if t0 == "py_compile":
        return True

    return False

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


CLAUDE_5H_MAX_CALLS = int(os.environ.get("CLAUDE_5H_MAX_CALLS", 45))
CLAUDE_5H_THRESHOLD_PCT = float(os.environ.get("CLAUDE_5H_THRESHOLD_PCT", 0.85))
CLAUDE_5H_THRESHOLD_CALLS = int(CLAUDE_5H_MAX_CALLS * CLAUDE_5H_THRESHOLD_PCT)

WORKER_GATE_FILE = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes")) / "worker_gate_state.json"
WORKER_GATE_LOCK_FILE = WORKER_GATE_FILE.with_suffix(".lock")
_PARENT_SESSION_CACHE: Dict[str, Optional[str]] = {}
_CACHE_LOCK = threading.Lock()


def _get_parent_session_id(session_id: str) -> Optional[str]:
    """Get parent_session_id with in-memory caching to avoid redundant SQLite queries."""
    if not session_id:
        return None
    if os.environ.get("TAADAA_WORKER") == "1":
        return "env_worker"
    with _CACHE_LOCK:
        if session_id in _PARENT_SESSION_CACHE:
            return _PARENT_SESSION_CACHE[session_id]
        if len(_PARENT_SESSION_CACHE) > 500:
            _PARENT_SESSION_CACHE.clear()

    parent_id = None
    try:
        db_path = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes")) / "state.db"
        if db_path.is_file():
            with sqlite3.connect(str(db_path), timeout=2.0) as con:
                row = con.execute("SELECT parent_session_id FROM sessions WHERE id = ?", (session_id,)).fetchone()
                if row and row[0]:
                    parent_id = str(row[0])
    except Exception as exc:
        logger.debug("[FARM_GUARD] Error querying parent for session %s: %s", session_id, exc)

    with _CACHE_LOCK:
        _PARENT_SESSION_CACHE[session_id] = parent_id
    return parent_id


def _record_claude_usage(cmd: str, weight: int = 1) -> None:
    """Record Claude CLI call to usage tracker file atomically."""
    try:
        CLAUDE_USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data: Dict[str, Any] = {"calls": []}
        if CLAUDE_USAGE_FILE.is_file():
            try:
                with open(CLAUDE_USAGE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        calls = data.get("calls", [])
        now = time.time()
        calls.append({"ts": now, "cmd": cmd[:100], "weight": weight})
        week_ago = now - 7 * 86400
        data["calls"] = [c for c in calls if c.get("ts", 0) > week_ago]
        tmp = CLAUDE_USAGE_FILE.parent / f"{CLAUDE_USAGE_FILE.name}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, CLAUDE_USAGE_FILE)
    except Exception as exc:
        logger.debug("[FARM_GUARD] Error recording claude usage: %s", exc)


def _check_claude_cli_guard(cmd: str) -> Optional[Dict[str, Any]]:
    """Hard Guard: Enforce 85% 5h limit & Lockout protection on Claude CLI calls."""
    if not re.search(r"\bclaude\b", cmd, re.IGNORECASE):
        return None

    now = time.time()

    # 1. Check active lockout
    if CLAUDE_LOCKOUT_FILE.is_file():
        try:
            with open(CLAUDE_LOCKOUT_FILE, "r", encoding="utf-8") as f:
                lockout = json.load(f)
            locked_until = lockout.get("locked_until", 0)
            if now < locked_until:
                remain_min = max(1, int((locked_until - now) / 60))
                reset_str = lockout.get("reset_time_str", f"{remain_min}m nữa")
                return {
                    "action": "block",
                    "message": (
                        f"⛔ [CLAUDE CLI HARD GUARD - LOCKOUT ACTIVE]:\n"
                        f"Claude CLI đang bị Anthropic khóa session limit (resets {reset_str}, còn ~{remain_min} phút)!\n"
                        f"Lệnh `{cmd[:80]}` BỊ CHẶN ĐỨNG VẬT LÝ BỞI FARM GUARD.\n\n"
                        f"HÀNH ĐỘNG BẮT BUỘC: Fallback sang OmniRoute Review (:20129) qua model `review` hoặc `auto/claude-opus`."
                    ),
                }
            else:
                try:
                    CLAUDE_LOCKOUT_FILE.unlink()
                except OSError:
                    pass
        except Exception:
            pass

    # 2. Check usage tracker (5h window: max calls & threshold configurable)
    weight = 1
    if re.search(r"--model\s+opus", cmd, re.IGNORECASE):
        weight *= 2
    if re.search(r"--effort\s+max", cmd, re.IGNORECASE):
        weight *= 2

    if CLAUDE_USAGE_FILE.is_file():
        try:
            with open(CLAUDE_USAGE_FILE, "r", encoding="utf-8") as f:
                usage = json.load(f)
            calls = usage.get("calls", [])
            window_5h = now - 5 * 3600
            recent_calls = [c for c in calls if c.get("ts", 0) > window_5h]
            total_weight = sum(c.get("weight", 1) for c in recent_calls)

            if (total_weight + weight) >= CLAUDE_5H_THRESHOLD_CALLS:
                pct = int(CLAUDE_5H_THRESHOLD_PCT * 100)
                return {
                    "action": "block",
                    "message": (
                        f"⛔ [CLAUDE CLI HARD GUARD - {pct}% QUOTA EXCEEDED]:\n"
                        f"Claude CLI session usage đã đạt {total_weight}/{CLAUDE_5H_MAX_CALLS} calls "
                        f"(~{(total_weight/CLAUDE_5H_MAX_CALLS)*100:.0f}% >= {pct}%).\n"
                        f"Lệnh `{cmd[:80]}` (weight={weight}) BỊ CHẶN ĐỨNG VẬT LÝ để bảo vệ quota Claude Pro!\n\n"
                        f"HÀNH ĐỘNG BẮT BUỘC: Fallback sang OmniRoute Review (:20129) qua model `review` hoặc `auto/claude-opus`."
                    ),
                }
        except Exception:
            pass

    return None


def _is_worker_session(session_id: str) -> bool:
    """Check if session is an autonomous worker subagent (escape token). Cached for performance."""
    return bool(_get_parent_session_id(session_id))


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


@contextmanager
def _watchdog_lock():
    WATCHDOG_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd = None
    deadline = time.time() + 2.0
    while time.time() < deadline:
        try:
            if WATCHDOG_LOCK_FILE.exists():
                try:
                    if time.time() - WATCHDOG_LOCK_FILE.stat().st_mtime > 10:
                        WATCHDOG_LOCK_FILE.unlink()
                except OSError:
                    pass
            fd = os.open(str(WATCHDOG_LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            time.sleep(0.05)
        except Exception:
            break
    if fd is None:
        logger.warning("[FARM_GUARD] Timeout acquiring watchdog lock (%s), proceeding without lock", WATCHDOG_LOCK_FILE)
    try:
        yield
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass
            try:
                if WATCHDOG_LOCK_FILE.exists():
                    WATCHDOG_LOCK_FILE.unlink()
            except OSError:
                pass


def _load_watchdog_state() -> Dict[str, Any]:
    try:
        if WATCHDOG_STATE_FILE.is_file():
            with open(WATCHDOG_STATE_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    if isinstance(data, dict):
                        if "sessions" not in data or not isinstance(data["sessions"], dict):
                            data["sessions"] = {}
                        return data
    except Exception as exc:
        logger.debug("[FARM_GUARD] Error reading watchdog state: %s", exc)
    return {"sessions": {}, "updated_at": time.time()}


def _save_watchdog_state(data: Dict[str, Any]) -> None:
    tmp = None
    try:
        WATCHDOG_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        now = time.time()
        data["updated_at"] = now
        sessions = data.get("sessions", {})
        if isinstance(sessions, dict):
            stale_sids = [
                sid for sid, sdata in sessions.items()
                if isinstance(sdata, dict) and (now - (sdata.get("last_beat") or sdata.get("current_tool_start") or 0) > SESSION_EXPIRY_SECONDS)
            ]
            for sid in stale_sids:
                sessions.pop(sid, None)

        tmp = WATCHDOG_STATE_FILE.parent / f"{WATCHDOG_STATE_FILE.name}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, WATCHDOG_STATE_FILE)
    except Exception as exc:
        if tmp and tmp.is_file():
            try:
                tmp.unlink()
            except OSError:
                pass
        logger.debug("[FARM_GUARD] Error writing watchdog state: %s", exc)


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


def _load_worker_gate_state() -> Dict[str, Dict[str, int]]:
    """Load worker gate state from disk."""
    if not WORKER_GATE_FILE.is_file():
        return {}
    try:
        with open(WORKER_GATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_worker_gate_state(state_dict: Dict[str, Dict[str, int]]) -> None:
    """Save worker gate state to disk atomically with stale session cleanup."""
    tmp = None
    try:
        now = time.time()
        stale_sids = [
            sid for sid, sdata in state_dict.items()
            if isinstance(sdata, dict) and (now - sdata.get("updated_at", now) > SESSION_EXPIRY_SECONDS)
        ]
        for sid in stale_sids:
            state_dict.pop(sid, None)

        WORKER_GATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = WORKER_GATE_FILE.parent / f"{WORKER_GATE_FILE.name}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, ensure_ascii=False, indent=2)
        os.replace(tmp, WORKER_GATE_FILE)
    except Exception as exc:
        if tmp and tmp.is_file():
            try:
                tmp.unlink()
            except OSError:
                pass
        logger.debug("[FARM_GUARD] Error saving worker gate state: %s", exc)


@contextmanager
def _worker_gate_lock():
    WORKER_GATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd = None
    deadline = time.time() + 2.0
    while time.time() < deadline:
        try:
            if WORKER_GATE_LOCK_FILE.exists():
                try:
                    if time.time() - WORKER_GATE_LOCK_FILE.stat().st_mtime > 10:
                        WORKER_GATE_LOCK_FILE.unlink()
                except OSError:
                    pass
            fd = os.open(str(WORKER_GATE_LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            time.sleep(0.05)
        except Exception:
            break
    if fd is None:
        logger.warning("[FARM_GUARD] Timeout acquiring worker gate lock (%s), proceeding without lock", WORKER_GATE_LOCK_FILE)
    try:
        yield
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass
            try:
                if WORKER_GATE_LOCK_FILE.exists():
                    WORKER_GATE_LOCK_FILE.unlink()
            except OSError:
                pass


def check_worker_tool_gate(tool_name: str, session_id: str, args: Any = None) -> Optional[Dict[str, Any]]:
    """Enforce hard limits on Worker subagents to eliminate Analysis Paralysis.
    
    Rules:
    1. MAX_WORKER_CALLS (12): Hard stop worker after 12 calls (including blocked attempts).
    2. MONOLITH BLOCK: Cấm tuyệt đối read_file/search_files vào *_smoke.py (feed_swipe_smoke >22k lines).
    3. READ_BUDGET (3): Tối đa 3 lần đọc file/search.
    4. WRITE_DEADLINE (4): Nếu call_count >= 4 và write_count == 0, khóa công cụ đọc VÀ terminal probe, ép ghi code ngay.
    """
    if not session_id:
        return None
    with _worker_gate_lock():
        worker_states = _load_worker_gate_state()
        state = worker_states.setdefault(session_id, {"read_count": 0, "write_count": 0, "call_count": 0, "updated_at": time.time()})
        state["updated_at"] = time.time()

        # Luôn tăng call_count cho mỗi lượt gọi (kể cả lượt bị block) để chống loop vô tận
        state["call_count"] += 1

        # 0. Check Hard Budget Cap: Tối đa MAX_WORKER_CALLS (12)
        if state["call_count"] > MAX_WORKER_CALLS:
            _save_worker_gate_state(worker_states)
            return {
                "action": "block",
                "reason": (
                    f"⛔ [WORKER TOOL GATE - BUDGET EXHAUSTED]: "
                    f"Worker đã chạm trần ngân sách ({state['call_count'] - 1}/{MAX_WORKER_CALLS} tool calls)! "
                    "Mọi tool calls tiếp theo đã bị KHÓA CỨNG. "
                    "Bạn BẮT BUỘC phải dừng lại và xuất báo cáo kết quả / blocker ngay lập tức."
                ),
            }

        # 1. Monolith File Guard: Cấm đọc hoặc tìm kiếm trong các file monolith *_smoke.py
        fn_args = args if isinstance(args, dict) else {}
        target_path = str(fn_args.get("path") or fn_args.get("file_path") or fn_args.get("pattern") or "")
        if target_path and is_monolith_smoke(target_path):
            _save_worker_gate_state(worker_states)
            return {
                "action": "block",
                "reason": (
                    f"⛔ [WORKER TOOL GATE - MONOLITH BLOCKED]: "
                    f"Đường dẫn '{target_path}' là file flow monolith (>22.000 dòng)! "
                    "CẤM TUYỆT ĐỐI mở file flow monolith để điều tra. "
                    "Lỗi popup/selector BẮT BUỘC xử lý tại benign_popup_registry.py theo PATCH_CONTRACT."
                ),
            }

        READ_TOOLS = {"read_file", "search_files"}
        WRITE_TOOLS = {"write_file", "patch"}

        if tool_name in READ_TOOLS:
            # Check WRITE_DEADLINE: nếu đã qua WRITE_DEADLINE (turn 4 trở đi) mà write_count == 0
            if state["call_count"] >= WRITE_DEADLINE and state["write_count"] == 0:
                _save_worker_gate_state(worker_states)
                return {
                    "action": "block",
                    "reason": (
                        f"⛔ [WORKER TOOL GATE - WRITE DEADLINE]: "
                        f"Đã qua {state['call_count'] - 1} tool calls mà chưa có thao tác write_file/patch nào. "
                        "Mọi công cụ đọc đã bị KHÓA CỨNG. Bạn BẮT BUỘC phải ghi bản vá (write_file/patch) ngay lập tức!"
                    ),
                }
            # Check READ_BUDGET: tối đa 3 lần đọc file/search
            if state["read_count"] >= READ_BUDGET:
                _save_worker_gate_state(worker_states)
                return {
                    "action": "block",
                    "reason": (
                        f"⛔ [WORKER TOOL GATE - READ BUDGET EXHAUSTED]: "
                        f"Ngân sách đọc của Worker đã hết ({state['read_count']}/{READ_BUDGET}). "
                        "Bạn BẮT BUỘC phải gọi write_file hoặc patch ngay bây giờ theo patch_intent! "
                        "CẤM tiếp tục khảo sát lan man."
                    ),
                }
            state["read_count"] += 1

        elif tool_name in WRITE_TOOLS:
            state["write_count"] += 1

        elif tool_name == "terminal":
            cmd = str(fn_args.get("command") or "").strip()
            # Bịt lỗ hổng Monolith qua terminal
            if is_monolith_smoke(cmd):
                _save_worker_gate_state(worker_states)
                return {
                    "action": "block",
                    "reason": (
                        f"⛔ [WORKER TOOL GATE - MONOLITH TERMINAL BLOCKED]: "
                        f"Lệnh terminal chứa tham chiếu đến file flow monolith (>22.000 dòng)! "
                        "CẤM TUYỆT ĐỐI đọc hoặc thao tác trên file flow monolith. "
                        "Lỗi popup/selector BẮT BUỘC xử lý tại benign_popup_registry.py theo PATCH_CONTRACT."
                    ),
                }
            # Cưỡng chế nghiêm ngặt: Mọi lệnh terminal của Worker PHẢI là lệnh kiểm tra an toàn (py_compile, git status, git diff)
            if not is_safe_terminal_verify(cmd):
                _save_worker_gate_state(worker_states)
                return {
                    "action": "block",
                    "reason": (
                        f"⛔ [WORKER TOOL GATE - TERMINAL PROBE BLOCKED]: "
                        f"Lệnh '{cmd[:60]}' không nằm trong allowlist an toàn của Worker! "
                        "Worker fix alert chỉ được phép chạy: 'python -m py_compile <file>', 'git status', 'git diff'. "
                        "CẤM chạy script probe, inspect, print/cat/type file. "
                        "Hành động BẮT BUỘC là dùng patch hoặc write_file để ghi bản vá theo PATCH_CONTRACT."
                    ),
                }

        _save_worker_gate_state(worker_states)
    return None


def _on_pre_tool_call(
    tool_name: str = "",
    args: Any = None,
    task_id: str = "",
    session_id: str = "",
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    """Enforce State Guard (ALERT/WORKER) and Action Guard (Long-Runners) per session."""
    fn_name = tool_name or kwargs.get("function_name", "")
    fn_args = args if args is not None else kwargs.get("function_args", {})
    sess_id = session_id or kwargs.get("session_id", "")

    # Bắt Canary tại PRE-HOOK: ghi nhận ngay thời điểm bắt đầu chạy tool
    _record_watchdog_pre(session_id=sess_id, tool=fn_name, function_args=fn_args)

    # TẦNG 2: ESCAPE TOKEN — Subagents (parent_session_id trong DB HOẶC TAADAA_WORKER=1)
    if _is_worker_session(sess_id):
        gate_res = check_worker_tool_gate(fn_name, sess_id, fn_args)
        if gate_res:
            _record_watchdog_post(session_id=sess_id, tool=fn_name, status="blocked", function_args=fn_args)
            return gate_res
        return None

    # Khi Coordinator gọi delegate_task, kiểm tra goal và chuyển trạng thái session sang WORKER_RUNNING
    if fn_name == "delegate_task":
        dt_args = fn_args if isinstance(fn_args, dict) else {}
        goal_text = str(dt_args.get("goal") or "") + " " + str(dt_args.get("context") or "")
        if is_monolith_smoke(goal_text) and POPUP_SELECTOR_PATTERN.search(goal_text):
            _record_watchdog_post(session_id=sess_id, tool=fn_name, status="blocked", function_args=fn_args)
            return {
                "action": "block",
                "reason": (
                    "⛔ [COORDINATOR GUARD - MONOLITH DISPATCH BLOCKED]: "
                    "Goal hoặc context của delegate_task đang trỏ vào file flow monolith (*_smoke.py) cho lỗi popup/selector! "
                    "Đây là nguyên nhân chính gây ra Worker analysis paralysis (37 phút cạn 35 tool calls). "
                    "BẮT BUỘC soạn PATCH_CONTRACT chỉ định file đích nhẹ 'python_runner/flows/benign_popup_registry.py' trước khi dispatch."
                ),
            }
        _update_session_state(sess_id, {
            "phase": "WORKER_RUNNING",
            "dispatched_at": time.time(),
        })
        logger.info("[FARM_GUARD] delegate_task called -> Phase transitioned to WORKER_RUNNING for session %s", sess_id)
        return None

    # Tool skill_view: luôn cho phép đọc skill để Coordinator nắm quy tắc
    if fn_name == "skill_view":
        return None

    sess_state = _get_session_state(sess_id)
    phase = sess_state.get("phase", "IDLE")

    # 1. State Guard: Phase ALERT
    if phase == "ALERT":
        # Chặn toàn bộ Investigative Tools ở Phase ALERT
        if fn_name in INVESTIGATIVE_TOOLS:
            logger.warning("[FARM_GUARD] Blocked investigative tool '%s' in ALERT phase for session %s", fn_name, sess_id)
            _record_watchdog_post(session_id=sess_id, tool=fn_name, status="blocked", function_args=fn_args)
            return {
                "action": "block",
                "message": (
                    f"⛔ [FARM GUARD - PHASE: ALERT] TOOL `{fn_name}` BỊ CHẶN BỞI PRE-TOOL-USE HOOK:\n"
                    "Coordinator CẤM TUYỆT ĐỐI tự ý đọc file, tìm kiếm code hoặc sửa file trong session chính khi có sự cố Farm!\n"
                    "Việc tự điều tra sẽ làm tràn context và chậm trễ phản ứng các máy khác.\n\n"
                    "HÀNH ĐỘNG BẮT BUỘC:\n"
                    "Gọi tool `delegate_task(goal=..., context=...)` ngay lập tức để Worker Subagent xử lý trong context riêng!"
                ),
            }

        # Kiểm tra tool terminal ở Phase ALERT: chỉ cho phép 1 lệnh O(1) thỏa inspect_machine.py hoặc adb devices
        if fn_name == "terminal":
            cmd = ""
            if isinstance(fn_args, dict):
                cmd = (fn_args.get("command") or "").strip()

            is_inspect = bool(re.search(r"inspect_machine\.py\s+\d+|adb\s+devices", cmd))
            budget = sess_state.get("inspect_budget", 0)
            if is_inspect and budget > 0:
                _update_session_state(sess_id, {"inspect_budget": budget - 1})
                logger.info("[FARM_GUARD] Allowed 1 inspect command in ALERT phase, budget consumed for session %s", sess_id)
                return None

            logger.warning("[FARM_GUARD] Blocked terminal in ALERT phase for session %s: %s", sess_id, cmd[:80])
            _record_watchdog_post(session_id=sess_id, tool=fn_name, status="blocked", function_args=fn_args)
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
        if fn_name == "terminal":
            cmd = ""
            if isinstance(fn_args, dict):
                cmd = (fn_args.get("command") or "").strip()
            is_benign = bool(re.search(r"^git\s+(status|diff|log)|psutil|python.*canary", cmd))
            if not is_benign:
                logger.warning("[FARM_GUARD] Blocked terminal in WORKER_RUNNING phase for session %s: %s", sess_id, cmd[:80])
                _record_watchdog_post(session_id=sess_id, tool=fn_name, status="blocked", function_args=fn_args)
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
    if fn_name == "terminal":
        cmd = ""
        if isinstance(fn_args, dict):
            cmd = (fn_args.get("command") or "").strip()

        # Check Claude CLI Hard Guard (85% Limit & Lockout Protection)
        claude_guard_res = _check_claude_cli_guard(cmd)
        if claude_guard_res:
            logger.warning("[FARM_GUARD] Blocked Claude CLI by quota/lockout guard: %s", cmd[:80])
            _record_watchdog_post(session_id=sess_id, tool=fn_name, status="blocked", function_args=fn_args)
            return claude_guard_res

        # Tầng 1: Allowlist O(1)
        if any(re.search(p, cmd, re.IGNORECASE) for p in ALLOWLIST_PATTERNS):
            return None

        # Tầng 3: Denylist (Long-runners & Python probe)
        if any(re.search(p, cmd, re.IGNORECASE) for p in DENYLIST_PATTERNS):
            logger.warning("[FARM_GUARD] Blocked LONG-RUNNER in session %s: %s", sess_id, cmd[:80])
            _record_watchdog_post(session_id=sess_id, tool=fn_name, status="blocked", function_args=fn_args)
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


def _record_watchdog_pre(
    session_id: str,
    tool: str,
    function_args: Any,
) -> None:
    try:
        sid = session_id or "__default__"
        now = time.time()
        is_canary = bool(re.search(r'\b(canary|recoverytestswipes|run-feed-session)\b', str(function_args), re.IGNORECASE))
        parent_sid = _get_parent_session_id(sid)

        with _watchdog_lock():
            data = _load_watchdog_state()
            sessions = data.setdefault("sessions", {})
            sess = sessions.setdefault(sid, {})
            sess["last_beat"] = now
            sess["last_beat_iso"] = datetime.now().isoformat()
            sess["current_tool"] = tool
            sess["current_tool_start"] = now
            sess["is_canary"] = is_canary
            sess["status"] = "running"
            if parent_sid:
                sess["parent_session_id"] = parent_sid
            _save_watchdog_state(data)
    except Exception as exc:
        logger.debug("[FARM_GUARD] Error recording watchdog pre beat: %s", exc)


def _record_watchdog_post(
    session_id: str,
    tool: str,
    status: Optional[str],
    function_args: Any,
) -> None:
    try:
        sid = session_id or "__default__"
        now = time.time()
        is_canary = bool(re.search(r'\b(canary|recoverytestswipes|run-feed-session)\b', str(function_args), re.IGNORECASE))

        with _watchdog_lock():
            data = _load_watchdog_state()
            sessions = data.setdefault("sessions", {})
            sess = sessions.setdefault(sid, {})
            sess["last_beat"] = now
            sess["last_beat_iso"] = datetime.now().isoformat()
            sess["status"] = status or "success"
            sess["current_tool"] = None
            sess["current_tool_start"] = None
            sess["tool"] = tool
            if is_canary:
                sess["is_canary"] = True
            elif "is_canary" not in sess:
                sess["is_canary"] = False
            _save_watchdog_state(data)
    except Exception as exc:
        logger.debug("[FARM_GUARD] Error recording watchdog post beat: %s", exc)


def _on_post_tool_call(
    tool_name: str = "",
    args: Any = None,
    result: Any = None,
    session_id: str = "",
    status: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Record heartbeat after every tool call for stale watchdog monitoring."""
    fn_name = tool_name or kwargs.get("function_name", "")
    fn_args = args if args is not None else kwargs.get("function_args", {})
    sess_id = session_id or kwargs.get("session_id", "")
    st = status if status is not None else kwargs.get("status", "success")

    _record_watchdog_post(
        session_id=sess_id,
        tool=fn_name,
        status=st,
        function_args=fn_args,
    )

    if st != "blocked":
        cmd_str = ""
        if isinstance(fn_args, dict):
            cmd_str = (fn_args.get("command") or fn_args.get("cmd") or "").strip()
        else:
            cmd_str = str(fn_args)
        if re.search(r"\bclaude\b", cmd_str, re.IGNORECASE):
            _record_claude_usage(cmd_str)


def register(ctx: Any) -> None:
    """Register lifecycle hooks with Hermes."""
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
    ctx.register_hook("post_tool_call", _on_post_tool_call)
    logger.info("[FARM_GUARD] farm-coordinator-guard (v2.1 Session-Scoped + Multi-Tool Lock + Stale Watchdog) registered successfully")

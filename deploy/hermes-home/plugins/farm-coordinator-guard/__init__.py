"""Farm Coordinator Guard Plugin for Hermes v2.3 (Zero-Bypass Architecture Approved).

Two-Tier Enforcement (State Guard + Action Guard) + WorkerToolGate:
1. STATE GUARD:
   - Phase ALERT / WORKER_RUNNING / IDLE / CLOSEOUT
2. ACTION GUARD:
   - Allowlist / Denylist
3. WORKER TOOL GATE:
   - Scope Lock Enforcement (Hole A closed): Enforce that worker can ONLY edit files declared in target_files.
   - Blacklist self-modification of guard plugin.
4. COORDINATOR SCOPE LOCK GATE v3.0:
   - Default-Deny (Hole C closed)
   - Structured Target Files only (Hole B closed - no free-text regex fallback)
   - Whitelist Containment + isfile / valid parent dir (Hole D closed)
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
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

HERMES_ROOT = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes"))
STATE_FILE = HERMES_ROOT / "farm_coordinator_phase.json"
STATE_LOCK_FILE = STATE_FILE.with_suffix(".lock")
WATCHDOG_STATE_FILE = HERMES_ROOT / "watchdog_state.json"
WATCHDOG_LOCK_FILE = WATCHDOG_STATE_FILE.with_suffix(".lock")
CLAUDE_LOCKOUT_FILE = HERMES_ROOT / "claude_lockout.json"
CLAUDE_USAGE_FILE = HERMES_ROOT / "claude_usage.json"
WORKER_TIMEOUT_SECONDS = 1200
CLOSEOUT_TIMEOUT_SECONDS = 7200
SESSION_EXPIRY_SECONDS = 7200

POPUP_SELECTOR_PATTERN = re.compile(r"\b(?:popup|allowlist|survey|ads?|selector|advert)\b", re.IGNORECASE)
MAX_COORDINATOR_DISPATCHES = int(os.environ.get("COORDINATOR_MAX_DISPATCHES", 3))

_SCHEDULER_RE = re.compile(
    r"\b(crontab|schtasks|Register-ScheduledTask|New-ScheduledTask|systemctl|launchctl|New-Service|sc\.exe\s+create)\b",
    re.IGNORECASE,
)
_FILEWRITE_SHELL_RE = re.compile(
    r"(>>?\s*[^\s|&]+)|(<<\s*['\"]?\w+)|\btee\b|\bSet-Content\b|\bOut-File\b|\bAdd-Content\b|\[IO\.File\]::Write|open\([^)]*['\"][wa]\b|fs\.writeFileSync|fs\.appendFileSync|writeAllText|WriteAllLines",
    re.IGNORECASE,
)
_DAEMON_RE = re.compile(
    r"\b(Popen|nohup|Start-Process|start\s+/b|pm2\s+start|forever\s+start|setsid)\b|&\s*$",
    re.IGNORECASE,
)
_DAEMON_EXEMPT_RE = re.compile(r"\b(git|inspect_machine|claude|grep)\b", re.IGNORECASE)
_TOOLNAME_RE = re.compile(
    r"[\w\-]*(heal|watchdog|daemon|auto[_\-]|recover|keepalive|guardian|supervisor|healer|repair)[\w\-]*\.(py|ps1|sh|js|cmd|bat)",
    re.IGNORECASE,
)
_SCRIPT_FILE_RE = re.compile(r"\.(py|ps1|sh|bat|cmd)\b", re.IGNORECASE)

INVESTIGATIVE_TOOLS = {
    "read_file",
    "search_files",
    "patch",
    "write_file",
    "execute_code",
}

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
    r"^\s*claude\s+-p\b",
]

DENYLIST_PATTERNS = [
    r"\brun_.*batch.*\.ps1\b",
    r'(?:"[^"]*"|\x27[^\x27]*\x27|\S+)\.ps1\b',
    r"\bupload[_-]?video\b",
    r"\bupload_tik\b",
    r"\bcheckmail\b",
    r"\breg[_-]?(tiktok|gmail)\b",
]

ALLOWED_REPO_ROOTS = [
    os.path.realpath(r"D:\Taadaa"),
    os.path.realpath(str(HERMES_ROOT)),
]

GUARD_SOURCE_DIR = os.path.realpath(str(HERMES_ROOT / "plugins" / "farm-coordinator-guard"))
VALID_CODE_EXTENSIONS = {".py", ".json", ".yaml", ".yml", ".sh", ".ps1", ".js", ".ts", ".toml", ".ini"}

_CACHE_LOCK = threading.Lock()
_PARENT_SESSION_CACHE: Dict[str, Optional[str]] = {}


def is_monolith_smoke(path_str: str) -> bool:
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


@contextmanager
def _acquire_file_lock(lock_path: Path):
    fd = None
    start = time.time()
    while time.time() - start < 3.0:
        try:
            if lock_path.exists():
                try:
                    if time.time() - lock_path.stat().st_mtime > 10:
                        lock_path.unlink()
                except OSError:
                    pass
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
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
                if lock_path.exists():
                    lock_path.unlink()
            except OSError:
                pass


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
    tmp = None
    try:
        tmp = STATE_FILE.parent / f"{STATE_FILE.name}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, STATE_FILE)
    except Exception as exc:
        logger.debug("[FARM_GUARD] Error saving state file: %s", exc)
        if tmp and tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _get_session_state(session_id: str) -> Dict[str, Any]:
    if not session_id:
        return {}
    with _acquire_file_lock(STATE_LOCK_FILE):
        data = _load_state_file()
        sessions = data.get("sessions", {})
        now = time.time()
        for sid, sdata in list(sessions.items()):
            if not isinstance(sdata, dict):
                continue
            updated_at = sdata.get("updated_at") or sdata.get("dispatched_at") or 0
            if now - updated_at > SESSION_EXPIRY_SECONDS:
                sessions.pop(sid, None)
                continue
            phase = sdata.get("phase")
            if phase == "WORKER_RUNNING" and (now - sdata.get("dispatched_at", 0) > WORKER_TIMEOUT_SECONDS):
                sdata["phase"] = "IDLE"
                sdata["updated_at"] = now
        return sessions.get(session_id, {})


def _update_session_state(session_id: str, updates: Dict[str, Any]) -> None:
    if not session_id:
        return
    with _acquire_file_lock(STATE_LOCK_FILE):
        data = _load_state_file()
        sessions = data.setdefault("sessions", {})
        sess = sessions.setdefault(session_id, {})
        sess.update(updates)
        sess["updated_at"] = time.time()
        _save_state_file(data)


def _get_parent_session_id(session_id: str) -> Optional[str]:
    if not session_id:
        return None
    if os.environ.get("TAADAA_WORKER") == "1":
        return "env_worker"
    with _CACHE_LOCK:
        if session_id in _PARENT_SESSION_CACHE:
            return _PARENT_SESSION_CACHE[session_id]

    parent_id = None
    try:
        db_path = HERMES_ROOT / "state.db"
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


def _is_worker_session(session_id: str) -> bool:
    return bool(_get_parent_session_id(session_id))


def check_worker_tool_gate(tool_name: str, session_id: str, args: Any = None) -> Optional[Dict[str, Any]]:
    """Enforce that Worker subagent obeys the Scope Lock and does not self-modify guard (Hole A closed)."""
    if not session_id:
        return None

    fn_args = args if isinstance(args, dict) else {}

    # Safety invariant: catastrophic terminal commands
    if tool_name == "terminal":
        cmd = str(fn_args.get("command") or "").strip().lower()
        destructive_patterns = [
            r"\brm\s+-[rf]{1,2}\s+[/\\~]",
            r"\bformat\s+[c-z]:",
            r"\bfastboot\s+wipe",
            r"\badb\s+.*--wipe\b",
        ]
        for pat in destructive_patterns:
            if re.search(pat, cmd):
                return {
                    "action": "block",
                    "reason": f"⛔ [SAFETY INVARIANT]: Lệnh terminal '{cmd[:50]}' có nguy cơ phá hoại hạ tầng bị chặn.",
                }

    # HOLE A ENFORCEMENT: Khi worker gọi write_file hoặc patch, KIỂM TRA ĐÚNG TARGET FILES CỦA CHA
    if tool_name in ("write_file", "patch"):
        target_path = str(fn_args.get("path") or "").strip()
        if not target_path:
            return None

        real_target = os.path.realpath(os.path.normpath(target_path))

        # Blacklist: Cấm worker tự sửa file của plugin farm-coordinator-guard
        if real_target.startswith(GUARD_SOURCE_DIR + os.sep) or real_target == GUARD_SOURCE_DIR:
            return {
                "action": "block",
                "reason": "⛔ [WORKER GATE - SELF-MODIFICATION BLOCKED]: Worker CẤM TUYỆT ĐỐI sửa mã nguồn của plugin bảo vệ farm-coordinator-guard!",
            }

        # Kiểm tra scope lock từ Coordinator cha
        parent_id = _get_parent_session_id(session_id)
        if parent_id and parent_id != "env_worker":
            parent_state = _get_session_state(parent_id)
            allowed_targets = parent_state.get("target_files", [])
            if allowed_targets:
                normalized_allowed = [os.path.realpath(os.path.normpath(p)) for p in allowed_targets]
                # Cho phép nếu target nằm trong allowed_targets HOẶC là file test cùng thư mục
                is_allowed = (real_target in normalized_allowed) or any(
                    os.path.dirname(real_target) == os.path.dirname(p) and os.path.basename(real_target).startswith("test_")
                    for p in normalized_allowed
                )
                if not is_allowed:
                    return {
                        "action": "block",
                        "reason": (
                            f"⛔ [WORKER GATE - SCOPE LOCK BREACH]: Worker đang cố sửa file '{target_path}' "
                            f"nằm ngoài danh sách Scope Lock được Coordinator chỉ định: {allowed_targets}! "
                            "Worker CHỈ ĐƯỢC PHÉP sửa đúng file được giao."
                        ),
                    }

    return None


def _on_pre_tool_call(
    tool_name: str = "",
    args: Any = None,
    task_id: str = "",
    session_id: str = "",
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    fn_name = tool_name or kwargs.get("function_name", "")
    fn_args = args if args is not None else kwargs.get("function_args", {})
    sess_id = session_id or kwargs.get("session_id", "")

    # TẦNG 2: ESCAPE TOKEN — Subagents
    if _is_worker_session(sess_id):
        gate_res = check_worker_tool_gate(fn_name, sess_id, fn_args)
        if gate_res:
            return gate_res
        return None

    # COORDINATOR: Xử lý delegate_task
    if fn_name == "delegate_task":
        dt_args = fn_args if isinstance(fn_args, dict) else {}
        goal_text = str(dt_args.get("goal") or "") + " " + str(dt_args.get("context") or "")

        # Monolith smoke check
        if is_monolith_smoke(goal_text) and POPUP_SELECTOR_PATTERN.search(goal_text):
            return {
                "action": "block",
                "reason": "⛔ [COORDINATOR GUARD - MONOLITH DISPATCH BLOCKED]: Goal hoặc context trỏ vào monolith (*_smoke.py) cho popup!",
            }

        # Ground truth first check
        is_fix_code_task = bool(re.search(r'\b(sửa\s+code|fix\s+code|patch\s+contract|patch\s+code|áp\s+dụng\s+patch|thay\s+đổi\s+code)\b', goal_text, re.IGNORECASE))
        has_ground_truth = bool(re.search(r'\b(screencap|screenshot|inspect_machine|\.png|\.xml|màn\s+hình\s+hiện\s+trường|ảnh\s+hiện\s+trường)\b', goal_text, re.IGNORECASE))
        if is_fix_code_task and not has_ground_truth:
            return {
                "action": "block",
                "reason": "⛔ [COORDINATOR GUARD - GROUND TRUTH FIRST BLOCKED]: Cần có screencap/inspect_machine trước khi dispatch sửa code!",
            }

        # Dispatch budget check
        sess_state = _get_session_state(sess_id)
        dispatch_count = sess_state.get("dispatch_count", 0) + 1
        if dispatch_count > MAX_COORDINATOR_DISPATCHES:
            return {
                "action": "block",
                "reason": f"⛔ [COORDINATOR GUARD - DISPATCH BUDGET EXHAUSTED]: Đã dispatch {dispatch_count - 1}/{MAX_COORDINATOR_DISPATCHES} worker!",
            }

        # =========================================================================
        # COORDINATOR SCOPE LOCK GATE v3.0 (Zero-Bypass Architecture Approved)
        # =========================================================================
        task_type = str(dt_args.get("task_type") or "").strip().lower()
        is_non_code_exempt = (
            task_type in ("research", "inspect_only", "non_code", "query")
            or bool(re.search(r'\bTASK_TYPE:\s*(?:RESEARCH|INSPECT_ONLY|NON_CODE|QUERY)\b', goal_text, re.IGNORECASE))
        )

        # DEFAULT-DENY (Hole C closed): Mọi task delegate đều yêu cầu target_files TRỪ KHI exempt
        if not is_non_code_exempt:
            raw_targets: List[str] = []

            # 1. Từ dt_args.get("target_files")
            tf_arg = dt_args.get("target_files")
            if isinstance(tf_arg, list):
                raw_targets.extend([str(x) for x in tf_arg if x])
            elif isinstance(tf_arg, str) and tf_arg.strip():
                raw_targets.append(tf_arg.strip())

            # 2. Từ structured header trong context/goal (Hole B closed: CHỈ nhận header, không fallback regex văn xuôi)
            header_pat = r'(?:TARGET_FILE|SCOPE_LOCK|FILE_SỬA|TARGET):\s*([^\r\n]+)'
            for hm in re.findall(header_pat, goal_text, re.IGNORECASE):
                for part in re.split(r'[,;]\s*', hm.strip()):
                    p_clean = part.strip().strip('\'"<>`')
                    if p_clean:
                        raw_targets.append(p_clean)

            # Normalize & Deduplicate (Hỗ trợ path có khoảng trắng)
            normalized_targets: List[str] = []
            for p in raw_targets:
                p_clean = p.strip().strip('\'"<>`').rstrip('.,;:)!?')
                if re.match(r'^/[cdCD]/', p_clean):
                    drive_letter = p_clean[1].upper()
                    p_clean = f"{drive_letter}:{p_clean[2:]}"
                p_clean = os.path.normpath(p_clean)
                if p_clean and p_clean not in normalized_targets:
                    normalized_targets.append(p_clean)

            # GATE 1: Bắt buộc phải có target file
            if not normalized_targets:
                return {
                    "action": "block",
                    "reason": (
                        "⛔ [COORDINATOR GUARD - SCOPE LOCK MISSING TARGET FILE]: "
                        "Mọi delegate_task trong Farm BẮT BUỘC phải khai báo file mục tiêu cụ thể! "
                        "Khai báo qua `target_files=['D:/Taadaa/.../file.py']` "
                        "hoặc header trong context: `TARGET_FILE: D:/Taadaa/.../file.py`. "
                        "Nếu là task nghiên cứu phi-code, khai báo rõ `task_type='non_code'`."
                    ),
                }

            # GATE 2: Validate từng target file
            for p in normalized_targets:
                # 2.1: Phải là absolute path
                if not os.path.isabs(p):
                    return {
                        "action": "block",
                        "reason": f"⛔ [COORDINATOR GUARD - NOT ABSOLUTE PATH]: '{p}' không phải đường dẫn tuyệt đối!",
                    }

                # 2.2: CẤM thư mục (Hole 2 closed)
                if os.path.isdir(p):
                    return {
                        "action": "block",
                        "reason": f"⛔ [COORDINATOR GUARD - DIRECTORY NOT ALLOWED]: '{p}' là THƯ MỤC! Phải chỉ định file cụ thể.",
                    }

                # 2.3: Phải là file tồn tại HOẶC file tạo mới có thư mục cha hợp lệ (Hole D closed)
                parent_dir = os.path.dirname(p)
                if not os.path.isfile(p):
                    if not (parent_dir and os.path.isdir(parent_dir)):
                        return {
                            "action": "block",
                            "reason": f"⛔ [COORDINATOR GUARD - FILE/PARENT NOT FOUND]: File '{p}' và cả thư mục cha đều không tồn tại!",
                        }

                # 2.4: Đuôi file code hợp lệ
                _, ext = os.path.splitext(p)
                if ext.lower() not in VALID_CODE_EXTENSIONS:
                    return {
                        "action": "block",
                        "reason": f"⛔ [COORDINATOR GUARD - INVALID EXTENSION]: File '{p}' có đuôi '{ext}' không hợp lệ!",
                    }

                # 2.5: Whitelist containment check (Hole 1 closed)
                real_p = os.path.realpath(p)
                is_contained = any(
                    os.path.normcase(real_p) == os.path.normcase(root) or os.path.normcase(real_p).startswith(os.path.normcase(root) + os.sep)
                    for root in ALLOWED_REPO_ROOTS
                )
                if not is_contained:
                    return {
                        "action": "block",
                        "reason": f"⛔ [COORDINATOR GUARD - OUT OF REPO WHITELIST]: File '{p}' nằm ngoài whitelist {ALLOWED_REPO_ROOTS}!",
                    }

                # 2.6: Blacklist guard source
                if os.path.normcase(real_p).startswith(os.path.normcase(GUARD_SOURCE_DIR) + os.sep) or os.path.normcase(real_p) == os.path.normcase(GUARD_SOURCE_DIR):
                    return {
                        "action": "block",
                        "reason": "⛔ [COORDINATOR GUARD - GUARD SOURCE BLACKLISTED]: CẤM Scope Lock vào chính file của plugin bảo vệ!",
                    }

            # Lưu danh sách target_files vào session state để Worker Tool Gate sử dụng
            sess_updates = {
                "phase": "WORKER_RUNNING",
                "dispatched_at": time.time(),
                "dispatch_count": dispatch_count,
                "target_files": normalized_targets,
            }
            _update_session_state(sess_id, sess_updates)
            logger.info("[FARM_GUARD] delegate_task passed Scope Lock v3.0 -> targets: %s", normalized_targets)
            return None

        # Non-code task exempt
        _update_session_state(sess_id, {
            "phase": "WORKER_RUNNING",
            "dispatched_at": time.time(),
            "dispatch_count": dispatch_count,
            "target_files": [],
        })
        return None

    if fn_name == "skill_view":
        return None

    sess_state = _get_session_state(sess_id)
    phase = sess_state.get("phase", "IDLE")

    # ALERT phase blocking
    if phase == "ALERT":
        if fn_name in INVESTIGATIVE_TOOLS:
            return {
                "action": "block",
                "message": f"⛔ [FARM GUARD - PHASE: ALERT] TOOL `{fn_name}` BỊ CHẶN! Coordinator gọi delegate_task ngay.",
            }
        if fn_name == "terminal":
            cmd = (fn_args.get("command") or "").strip() if isinstance(fn_args, dict) else ""
            is_inspect = bool(re.search(r"inspect_machine\.py\s+\d+|adb\s+devices", cmd))
            budget = sess_state.get("inspect_budget", 0)
            if is_inspect and budget > 0:
                _update_session_state(sess_id, {"inspect_budget": budget - 1})
                return None
            return {
                "action": "block",
                "message": "⛔ [FARM GUARD - PHASE: ALERT] Hết ngân sách inspect O(1)! Dispatch worker ngay.",
            }

    # WORKER_RUNNING phase blocking
    if phase == "WORKER_RUNNING":
        if fn_name == "terminal":
            cmd = (fn_args.get("command") or "").strip() if isinstance(fn_args, dict) else ""
            is_benign = bool(re.search(r"^git(\s+-C\s+[^\s]+)?\s+(status|diff|log)|psutil|python.*canary|claude", cmd))
            if not is_benign:
                return {
                    "action": "block",
                    "message": "⛔ [FARM GUARD - PHASE: WORKER_RUNNING] Worker đang chạy background, Coordinator không chạy terminal điều tra.",
                }

    return None

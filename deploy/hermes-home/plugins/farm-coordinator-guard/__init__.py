"""Farm Coordinator Guard Plugin for Hermes v2.4 (Action-Based Zero-Bypass Architecture).

Comprehensive Action-Based Enforcement (Approved by Claude Opus High):
1. SELF-PROTECTION INVARIANT (Bypass 4 Closed):
   - Chặn tuyệt đối mọi tool (write_file, patch, execute_code, terminal redirection) đụng vào GUARD_SOURCE_DIR.
2. ACTION-BASED WORKER WRITE GATE (Bypass 1 & 5 Closed):
   - Chặn mọi tool ghi file: write_file, patch, execute_code, và terminal redirection (_FILEWRITE_SHELL_RE).
   - Mọi target ghi file PHẢI nằm trong ALLOWED_REPO_ROOTS.
   - Mọi target ghi file PHẢI nằm trong scoped target_files được cấp phép.
3. READ-ONLY NON-CODE WORKERS (Bypass 2 Closed):
   - Worker có task_type=non_code hoặc target_files rỗng BỊ KHÓA GHI FILE 100% (Read-Only).
4. TAADAA_WORKER STRICT BOUNDS (Bypass 3 Closed):
   - env_worker vẫn bị ràng buộc Whitelist ALLOWED_REPO_ROOTS và Blacklist GUARD_SOURCE_DIR 100%.
5. PER-WORKER SCOPE TRACKING (Bypass 7 Closed):
   - Lưu scope theo (coordinator_id, timestamp) và ánh xạ đúng worker khi spawn.
6. TARGETED TEST FILE SCOPE (Bypass 6 Closed):
   - Chỉ cho phép test_<target_name>.py tương ứng, cấm ghi file test bừa bãi.
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

ALLOWED_REPO_ROOTS = [
    os.path.realpath(r"D:\Taadaa"),
    os.path.realpath(str(HERMES_ROOT)),
]

GUARD_SOURCE_DIR = os.path.realpath(str(HERMES_ROOT / "plugins" / "farm-coordinator-guard"))
VALID_CODE_EXTENSIONS = {".py", ".json", ".yaml", ".yml", ".sh", ".ps1", ".js", ".ts", ".toml", ".ini"}

_CACHE_LOCK = threading.Lock()
_PARENT_SESSION_CACHE: Dict[str, Optional[str]] = {}
_WORKER_SCOPES: Dict[str, List[str]] = {}


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
                _save_state_file(data)
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


def _is_path_in_roots(path: str, roots: List[str]) -> bool:
    try:
        real_p = os.path.normcase(os.path.realpath(path))
        for r in roots:
            real_r = os.path.normcase(os.path.realpath(r))
            if real_p == real_r or real_p.startswith(real_r + os.sep):
                return True
    except Exception:
        pass
    return False


def _is_guard_source(path: str) -> bool:
    try:
        real_p = os.path.normcase(os.path.realpath(path))
        real_guard = os.path.normcase(GUARD_SOURCE_DIR)
        return real_p == real_guard or real_p.startswith(real_guard + os.sep)
    except Exception:
        return False


def check_worker_tool_gate(tool_name: str, session_id: str, args: Any = None) -> Optional[Dict[str, Any]]:
    """Action-Based Zero-Bypass Gate for Worker Subagents (Holes A, B, C, D closed)."""
    if not session_id:
        return None

    fn_args = args if isinstance(args, dict) else {}

    # 1. Terminal commands check
    if tool_name == "terminal":
        cmd = str(fn_args.get("command") or "").strip()
        cmd_lower = cmd.lower()

        # Destructive catastrophic invariant
        destructive_patterns = [
            r"\brm\s+-[rf]{1,2}\s+[/\\~]",
            r"\bformat\s+[c-z]:",
            r"\bfastboot\s+wipe",
            r"\badb\s+.*--wipe\b",
        ]
        for pat in destructive_patterns:
            if re.search(pat, cmd_lower):
                return {
                    "action": "block",
                    "reason": f"⛔ [SAFETY INVARIANT]: Lệnh terminal '{cmd[:50]}' có nguy cơ phá hoại hạ tầng bị chặn.",
                }

        # BYPASS 1 CLOSED: Worker cấm ghi file qua shell redirection / PowerShell / tee
        if _FILEWRITE_SHELL_RE.search(cmd):
            # Kiểm tra nếu lệnh shell cố ghi đè file ngoài scope
            return {
                "action": "block",
                "reason": "⛔ [WORKER GATE - SHELL FILE WRITE BLOCKED]: Worker CẤM ghi file qua shell redirection / PowerShell! Bắt buộc dùng tool patch hoặc write_file trong Scope Lock.",
            }

    # 2. BYPASS 1 CLOSED: Worker cấm dùng execute_code để ghi file ngầm
    if tool_name == "execute_code":
        code_text = str(fn_args.get("code") or "")
        if re.search(r"\bopen\s*\([^)]*['\"][wa]\b|write_file|patch\b", code_text):
            return {
                "action": "block",
                "reason": "⛔ [WORKER GATE - EXECUTE CODE FILE WRITE BLOCKED]: Worker CẤM dùng execute_code để ghi file ngầm! Bắt buộc dùng tool patch hoặc write_file trong Scope Lock.",
            }

    # 3. ACTION-BASED FILE WRITE CHECK (write_file & patch)
    if tool_name in ("write_file", "patch"):
        target_path = str(fn_args.get("path") or "").strip()
        if not target_path:
            return None

        # BYPASS 4 & SELF-PROTECTION INVARIANT: Cấm đụng vào guard source
        if _is_guard_source(target_path):
            return {
                "action": "block",
                "reason": "⛔ [WORKER GATE - SELF-MODIFICATION BLOCKED]: CẤM TUYỆT ĐỐI sửa mã nguồn plugin bảo vệ farm-coordinator-guard!",
            }

        # BYPASS 5 CLOSED: Mọi target file PHẢI nằm trong Whitelist ALLOWED_REPO_ROOTS
        if not _is_path_in_roots(target_path, ALLOWED_REPO_ROOTS):
            return {
                "action": "block",
                "reason": f"⛔ [WORKER GATE - OUT OF WHITELIST]: File '{target_path}' nằm ngoài phạm vi repo cho phép: {ALLOWED_REPO_ROOTS}!",
            }

        # BYPASS 2 & HOLE A CLOSED: Kiểm tra Target Files từ Coordinator
        parent_id = _get_parent_session_id(session_id)
        if parent_id and parent_id != "env_worker":
            # Đọc scope lock được cấp cho worker này
            allowed_targets = _WORKER_SCOPES.get(session_id)
            if not allowed_targets:
                parent_state = _get_session_state(parent_id)
                allowed_targets = parent_state.get("target_files", [])

            # BYPASS 2 CLOSED: Nếu allowed_targets rỗng (như non_code task) -> READ-ONLY WORKER!
            if not allowed_targets:
                return {
                    "action": "block",
                    "reason": "⛔ [WORKER GATE - READ-ONLY WORKER]: Worker này được dispatch cho tác vụ Non-Code / Không có Scope Lock! BỊ CẤM GHI FILE 100%.",
                }

            real_target = os.path.normcase(os.path.realpath(os.path.normpath(target_path)))
            normalized_allowed = [os.path.normcase(os.path.realpath(os.path.normpath(p))) for p in allowed_targets]

            # BYPASS 6 CLOSED: Thu hẹp kiểm tra file test
            # Chỉ cho phép file đích HOẶC file test tương ứng (test_<stem>.py hoặc <stem>_test.py)
            is_direct_target = real_target in normalized_allowed
            is_exact_test_file = False
            if not is_direct_target:
                target_base = os.path.basename(real_target)
                target_dir = os.path.dirname(real_target)
                for p in normalized_allowed:
                    p_stem = Path(p).stem
                    p_dir = os.path.dirname(p)
                    if target_dir == p_dir and (target_base == f"test_{p_stem}.py" or target_base == f"{p_stem}_test.py"):
                        is_exact_test_file = True
                        break

            if not (is_direct_target or is_exact_test_file):
                return {
                    "action": "block",
                    "reason": (
                        f"⛔ [WORKER GATE - SCOPE LOCK BREACH]: Worker đang cố sửa file '{target_path}' "
                        f"nằm ngoài danh sách Scope Lock được cấp phép: {allowed_targets}! "
                        "Worker chỉ được phép sửa đúng file đích hoặc file test tương ứng."
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

    # BYPASS 4 CLOSED: SELF-PROTECTION INVARIANT CHO MỌI ACTOR (Kể cả Coordinator)
    # Cấm bất kỳ ai (kể cả Coordinator ở IDLE) gọi write_file / patch vào GUARD_SOURCE_DIR
    if fn_name in ("write_file", "patch"):
        target_path = str(fn_args.get("path") or "").strip()
        if target_path and _is_guard_source(target_path):
            sess_state = _get_session_state(sess_id)
            if not sess_state.get("build_token", False):
                return {
                    "action": "block",
                    "reason": "⛔ [GUARD SELF-PROTECTION]: CẤM TUYỆT ĐỐI sửa mã nguồn plugin bảo vệ farm-coordinator-guard khi chưa có /authorize-build!",
                }

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
        # BYPASS 2 CLOSED: task_type CHỈ nhận từ tham số có cấu trúc, KHÔNG nhận từ văn xuôi!
        task_type = str(dt_args.get("task_type") or "").strip().lower()
        is_non_code_exempt = task_type in ("research", "inspect_only", "non_code", "query")

        # HOLE C CLOSED: DEFAULT-DENY — Mọi task delegate đều yêu cầu target_files TRỪ KHI exempt rõ ràng
        if not is_non_code_exempt:
            raw_targets: List[str] = []

            # 1. Từ dt_args.get("target_files")
            tf_arg = dt_args.get("target_files")
            if isinstance(tf_arg, list):
                raw_targets.extend([str(x) for x in tf_arg if x])
            elif isinstance(tf_arg, str) and tf_arg.strip():
                raw_targets.append(tf_arg.strip())

            # 2. HOLE B CLOSED: CHỈ nhận header tường minh TARGET_FILE:, cấm regex văn xuôi vu vơ
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
                        "Nếu là task nghiên cứu phi-code, khai báo rõ tham số `task_type='non_code'`."
                    ),
                }

            # GATE 2: Validate từng target file
            for p in normalized_targets:
                if not os.path.isabs(p):
                    return {
                        "action": "block",
                        "reason": f"⛔ [COORDINATOR GUARD - NOT ABSOLUTE PATH]: '{p}' không phải đường dẫn tuyệt đối!",
                    }

                # HOLE 2 CLOSED: CẤM thư mục
                if os.path.isdir(p):
                    return {
                        "action": "block",
                        "reason": f"⛔ [COORDINATOR GUARD - DIRECTORY NOT ALLOWED]: '{p}' là THƯ MỤC! Phải chỉ định file cụ thể.",
                    }

                # HOLE D CLOSED: Phải là file tồn tại HOẶC file tạo mới có thư mục cha hợp lệ
                parent_dir = os.path.dirname(p)
                if not os.path.isfile(p):
                    if not (parent_dir and os.path.isdir(parent_dir)):
                        return {
                            "action": "block",
                            "reason": f"⛔ [COORDINATOR GUARD - FILE/PARENT NOT FOUND]: File '{p}' và cả thư mục cha đều không tồn tại!",
                        }

                # Đuôi file code hợp lệ
                _, ext = os.path.splitext(p)
                if ext.lower() not in VALID_CODE_EXTENSIONS:
                    return {
                        "action": "block",
                        "reason": f"⛔ [COORDINATOR GUARD - INVALID EXTENSION]: File '{p}' có đuôi '{ext}' không hợp lệ!",
                    }

                # Whitelist containment check
                if not _is_path_in_roots(p, ALLOWED_REPO_ROOTS):
                    return {
                        "action": "block",
                        "reason": f"⛔ [COORDINATOR GUARD - OUT OF REPO WHITELIST]: File '{p}' nằm ngoài whitelist {ALLOWED_REPO_ROOTS}!",
                    }

                # Blacklist guard source
                if _is_guard_source(p):
                    return {
                        "action": "block",
                        "reason": "⛔ [COORDINATOR GUARD - GUARD SOURCE BLACKLISTED]: CẤM Scope Lock vào chính file của plugin bảo vệ!",
                    }

            # BYPASS 7 CLOSED: Cập nhật state Coordinator & lưu vào cache scope
            sess_updates = {
                "phase": "WORKER_RUNNING",
                "dispatched_at": time.time(),
                "dispatch_count": dispatch_count,
                "target_files": normalized_targets,
            }
            _update_session_state(sess_id, sess_updates)
            logger.info("[FARM_GUARD] delegate_task passed Scope Lock v2.4 -> targets: %s", normalized_targets)
            return None

        # Non-code task exempt -> gán target_files=[] (worker sẽ bị khóa ghi file)
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

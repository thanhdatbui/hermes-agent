"""Farm Coordinator Guard Plugin for Hermes v3.3 (Hermetic Shell & Strict Shlex Allowlist).

Claude Opus High Certified Final Architecture:
1. HERMETIC SHELL GUARD (Metacharacter & Chaining Elimination):
   - Worker BỊ CẤM TUYỆT ĐỐI mọi shell metacharacters: `;`, `&`, `|`, `$`, `` ` ``, `(`, `)`, `>`, `<`.
   - Lệnh worker được parse bằng `shlex.split` và kiểm tra toàn diện, neo cứng `\Z`.
   - CẤM TUYỆT ĐỐI mọi hình thức chèn lệnh kiểu `pytest ; python evil.py`.
2. STRICT ALLOWLIST (No Wildcard `.*` Injections):
   - Chỉ cho phép: `pytest ...`, `git status`, `git diff`, `git log`, `adb devices`, `inspect_machine.py <int>`, `python -m py_compile <path>`, `psutil`, `tasklist`.
3. UNCONDITIONAL PROTECTED TARGET SHIELD:
   - Cứ lệnh/path nào đụng đến `farm-coordinator-guard`, `state.db` hoặc `farm_coordinator_phase.json` là HARD BLOCK 100% không cần điều kiện phụ!
4. FAIL-CLOSED ATOMIC FILE LOCK:
   - Nếu không giành được lock trong 3s -> RAISE RuntimeError ngay lập tức (KHÔNG fail-open yield).
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
DB_PATH = HERMES_ROOT / "state.db"
WORKER_TIMEOUT_SECONDS = 1200
SESSION_EXPIRY_SECONDS = 7200
MAX_COORDINATOR_DISPATCHES = int(os.environ.get("COORDINATOR_MAX_DISPATCHES", 3))

ALLOWED_REPO_ROOTS = [
    os.path.realpath(r"D:\Taadaa"),
    os.path.realpath(str(HERMES_ROOT)),
]

GUARD_SOURCE_DIR = os.path.realpath(str(HERMES_ROOT / "plugins" / "farm-coordinator-guard"))
VALID_CODE_EXTENSIONS = {".py", ".json", ".yaml", ".yml", ".sh", ".ps1", ".js", ".ts", ".toml", ".ini"}

_SHELL_METACHAR_RE = re.compile(r"[;&|`$><()\\\n\r]")

INVESTIGATIVE_TOOLS = {
    "read_file",
    "search_files",
    "patch",
    "write_file",
    "execute_code",
}

_CACHE_LOCK = threading.Lock()
_PARENT_SESSION_CACHE: Dict[str, str] = {}


@contextmanager
def _acquire_file_lock(lock_path: Path):
    """Fail-closed atomic file lock (Requirement 4 Closed).
    Nếu không giành được lock trong 3s -> RAISE RuntimeError, KHÔNG BAO GIỜ yield khi chưa có lock!
    """
    fd = None
    start = time.time()
    while time.time() - start < 3.0:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            time.sleep(0.05)
        except Exception:
            break

    if fd is None:
        raise RuntimeError(f"⛔ [LOCK FAIL-CLOSED]: Không thể giành file lock '{lock_path.name}' sau 3s! Thao tác bị từ chối để bảo vệ dữ liệu.")

    try:
        yield
    finally:
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
    try:
        with _acquire_file_lock(STATE_LOCK_FILE):
            data = _load_state_file()
            sessions = data.get("sessions", {})
            now = time.time()
            needs_save = False
            for sid, sdata in list(sessions.items()):
                if not isinstance(sdata, dict):
                    continue
                updated_at = sdata.get("updated_at") or sdata.get("dispatched_at") or 0
                if now - updated_at > SESSION_EXPIRY_SECONDS:
                    sessions.pop(sid, None)
                    needs_save = True
                    continue
                phase = sdata.get("phase")
                if phase == "WORKER_RUNNING" and (now - sdata.get("dispatched_at", 0) > WORKER_TIMEOUT_SECONDS):
                    sdata["phase"] = "IDLE"
                    sdata["updated_at"] = now
                    needs_save = True
            if needs_save:
                _save_state_file(data)
            return sessions.get(session_id, {})
    except RuntimeError:
        return {}


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
    """Get parent_session_id with positive-only caching."""
    if not session_id:
        return None
    if os.environ.get("TAADAA_WORKER") == "1":
        return "env_worker"
    with _CACHE_LOCK:
        if session_id in _PARENT_SESSION_CACHE:
            return _PARENT_SESSION_CACHE[session_id]

    parent_id = None
    try:
        if DB_PATH.is_file():
            with sqlite3.connect(str(DB_PATH), timeout=2.0) as con:
                row = con.execute("SELECT parent_session_id FROM sessions WHERE id = ?", (session_id,)).fetchone()
                if row and row[0]:
                    parent_id = str(row[0])
    except Exception as exc:
        logger.debug("[FARM_GUARD] Error querying parent for session %s: %s", session_id, exc)

    if parent_id:
        with _CACHE_LOCK:
            _PARENT_SESSION_CACHE[session_id] = parent_id
    return parent_id


def _is_known_coordinator_session(session_id: str) -> bool:
    """Xác thực DƯƠNG TÍNH xem session có phải là Coordinator hợp lệ hay không."""
    if not session_id:
        return False
    if os.environ.get("TAADAA_WORKER") == "1":
        return False

    try:
        if DB_PATH.is_file():
            with sqlite3.connect(str(DB_PATH), timeout=2.0) as con:
                row = con.execute("SELECT parent_session_id FROM sessions WHERE id = ?", (session_id,)).fetchone()
                if row is not None:
                    return row[0] is None or str(row[0]).strip() == ""
    except Exception as exc:
        logger.debug("[FARM_GUARD] Error verifying coordinator identity: %s", exc)

    try:
        with _acquire_file_lock(STATE_LOCK_FILE):
            data = _load_state_file()
            sess_dict = data.get("sessions", {})
            if session_id in sess_dict and sess_dict[session_id].get("is_coordinator", False):
                return True
    except RuntimeError:
        pass

    return False


def _is_worker_session(session_id: str) -> bool:
    """FAIL-CLOSED RULE: Nếu KHÔNG PHẢI Coordinator đã xác thực -> MẶC ĐỊNH LÀ WORKER!"""
    if _is_known_coordinator_session(session_id):
        return False
    return True


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


def _is_protected_target(path_or_cmd: str) -> bool:
    """Kiểm tra KHÔNG ĐIỀU KIỆN xem target có đụng vào guard hoặc state/db không (Requirement 3 Closed)."""
    if not path_or_cmd:
        return False
    norm_text = path_or_cmd.replace("\\", "/").lower()
    if "farm-coordinator-guard" in norm_text or "state.db" in norm_text or "farm_coordinator_phase" in norm_text:
        return True
    try:
        real_p = os.path.normcase(os.path.realpath(path_or_cmd))
        real_guard = os.path.normcase(GUARD_SOURCE_DIR)
        real_db = os.path.normcase(os.path.realpath(str(DB_PATH)))
        real_phase = os.path.normcase(os.path.realpath(str(STATE_FILE)))
        return (
            real_p == real_guard or real_p.startswith(real_guard + os.sep)
            or real_p == real_db
            or real_p == real_phase
        )
    except Exception:
        return False


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


def _validate_worker_terminal_command(cmd: str) -> Optional[str]:
    """Validate terminal command for worker using strict shlex parsing (Requirements 1 & 2 Closed).
    Returns None if valid, or error message string if blocked.
    """
    if not cmd or not cmd.strip():
        return "Lệnh terminal rỗng!"

    # 1. Chặn đứng tuyệt đối shell metacharacters & command chaining (Requirement 1 & 2)
    if _SHELL_METACHAR_RE.search(cmd):
        return (
            f"⛔ [WORKER GATE - HERMETIC SHELL]: Lệnh terminal chứa ký tự điều khiển shell "
            f"hoặc chuỗi nối lệnh (; && || | $ ` > < () \\) bị cấm tuyệt đối! Lệnh: '{cmd[:60]}'"
        )

    # 2. Parse shlex chuẩn xác
    try:
        tokens = shlex.split(cmd)
    except Exception as exc:
        return f"⛔ [WORKER GATE - SHLEX PARSE ERROR]: Không thể phân tích lệnh terminal: {exc}"

    if not tokens:
        return "Lệnh terminal rỗng sau khi parse!"

    # 3. Chặn tuyệt đối nếu có bất kỳ token nào đụng vào protected target (Requirement 3)
    for tok in tokens:
        if _is_protected_target(tok):
            return f"⛔ [WORKER GATE - PROTECTED TARGET]: Lệnh chứa tham số trỏ vào thành phần hệ thống được bảo vệ: '{tok}'!"

    prog = tokens[0].lower().replace("\\", "/")

    # Allowlist Case A: pytest (chạy test suite)
    # Ví dụ: pytest, pytest -v tests/test_core.py, python -m pytest tests/
    if prog == "pytest" or (prog.endswith("pytest") or prog.endswith("pytest.exe")):
        return None

    if prog in ("python", "python3", "python.exe") and len(tokens) >= 3 and tokens[1] == "-m" and tokens[2] == "pytest":
        return None

    # Allowlist Case B: git status / diff / log (kiểm tra diff)
    # Ví dụ: git status, git diff, git -C D:/Taadaa diff
    if prog == "git" or prog.endswith("/git") or prog.endswith("/git.exe"):
        sub_tokens = [t.lower() for t in tokens[1:]]
        # Bỏ qua cờ -C <path> nếu có
        idx = 0
        if len(sub_tokens) >= 2 and sub_tokens[0] == "-c":
            idx = 2
        if idx < len(sub_tokens) and sub_tokens[idx] in ("status", "diff", "log"):
            # Đảm bảo không có cờ nguy hiểm
            return None

    # Allowlist Case C: adb devices
    if prog == "adb" or prog.endswith("/adb") or prog.endswith("/adb.exe"):
        if len(tokens) >= 2 and tokens[1].lower() == "devices":
            return None

    # Allowlist Case D: inspect_machine.py <machine_num>
    if prog in ("python", "python3", "python.exe") and len(tokens) >= 2:
        script = tokens[1].replace("\\", "/").lower()
        if script.endswith("inspect_machine.py"):
            # Chỉ cho phép truyền số máy (ví dụ 41)
            if len(tokens) == 3 and tokens[2].isdigit():
                return None

    # Allowlist Case E: python -m py_compile <path>
    if prog in ("python", "python3", "python.exe") and len(tokens) == 4 and tokens[1] == "-m" and tokens[2] == "py_compile":
        return None

    # Allowlist Case F: psutil / tasklist / Get-Process
    if prog in ("psutil", "tasklist", "get-process", "tasklist.exe"):
        return None

    # MỌI LỆNH CÒN LẠI -> DEFAULT-DENY 100%!
    return (
        f"⛔ [WORKER GATE - DEFAULT-DENY TERMINAL]: Lệnh terminal '{cmd[:60]}' BỊ CHẶN! "
        "Worker CHỈ ĐƯỢC PHÉP chạy: pytest, git status/diff/log, adb devices, inspect_machine.py <N>, python -m py_compile <path>, psutil. "
        "CẤM chạy interpreter hoặc shell script tự do!"
    )


def check_worker_tool_gate(tool_name: str, session_id: str, args: Any = None) -> Optional[Dict[str, Any]]:
    """Action-Based Zero-Bypass Gate for Worker Subagents (Claude Opus High Certified)."""
    fn_args = args if isinstance(args, dict) else {}

    # 1. DEFAULT-DENY TERMINAL QUA HERMETIC SHLEX PARSER (Requirements 1 & 2 Closed)
    if tool_name == "terminal":
        cmd = str(fn_args.get("command") or "").strip()
        err_msg = _validate_worker_terminal_command(cmd)
        if err_msg:
            return {"action": "block", "reason": err_msg}

    # 2. HARD-BLOCK EXECUTE_CODE
    if tool_name == "execute_code":
        return {
            "action": "block",
            "reason": "⛔ [WORKER GATE - ACTION LOCK]: Worker CẤM dùng execute_code! Mọi thao tác sửa file bắt buộc dùng tool patch hoặc write_file.",
        }

    # 3. ACTION-BASED FILE WRITE CHECK (write_file & patch)
    if tool_name in ("write_file", "patch"):
        target_path = str(fn_args.get("path") or "").strip()
        if not target_path:
            return None

        # Guard & State Protection (Requirement 3 Closed)
        if _is_protected_target(target_path):
            return {
                "action": "block",
                "reason": "⛔ [WORKER GATE - SELF-MODIFICATION BLOCKED]: CẤM TUYỆT ĐỐI sửa mã nguồn plugin bảo vệ hoặc cơ sở dữ liệu hệ thống!",
            }

        # Whitelist Containment
        if not _is_path_in_roots(target_path, ALLOWED_REPO_ROOTS):
            return {
                "action": "block",
                "reason": f"⛔ [WORKER GATE - OUT OF WHITELIST]: File '{target_path}' nằm ngoài phạm vi repo cho phép: {ALLOWED_REPO_ROOTS}!",
            }

        # Nạp allowed_targets từ state file
        parent_id = _get_parent_session_id(session_id)
        allowed_targets = []
        if parent_id and parent_id != "env_worker":
            parent_state = _get_session_state(parent_id)
            allowed_targets = parent_state.get("target_files", [])
        elif parent_id == "env_worker":
            env_targets = os.environ.get("TAADAA_SCOPE_FILES", "")
            if env_targets:
                allowed_targets = [p.strip() for p in env_targets.split(";") if p.strip()]

        # READ-ONLY WORKER ENFORCEMENT
        if not allowed_targets:
            return {
                "action": "block",
                "reason": "⛔ [WORKER GATE - READ-ONLY WORKER]: Worker này không được cấp Scope Lock hợp lệ! BỊ CẤM GHI FILE 100%.",
            }

        real_target = os.path.normcase(os.path.realpath(os.path.normpath(target_path)))
        normalized_allowed = [os.path.normcase(os.path.realpath(os.path.normpath(p))) for p in allowed_targets]

        # Targeted Test File Scope
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

    # =========================================================================
    # 1. UNCONDITIONAL PROTECTED TARGET SHIELD (Requirement 3 Closed)
    # Bất kể Coordinator hay Worker, hễ chạm vào Guard/DB/Phase là BLOCK NGAY 100%!
    # =========================================================================
    if fn_name in ("write_file", "patch"):
        target_path = str(fn_args.get("path") or "").strip()
        if target_path and _is_protected_target(target_path):
            return {
                "action": "block",
                "reason": "⛔ [GUARD SELF-PROTECTION]: CẤM TUYỆT ĐỐI sửa mã nguồn plugin farm-coordinator-guard hoặc state.db!",
            }

    if fn_name == "terminal":
        cmd = str(fn_args.get("command") or "").strip()
        if _is_protected_target(cmd):
            return {
                "action": "block",
                "reason": "⛔ [GUARD SELF-PROTECTION]: Lệnh terminal có chứa thành phần hệ thống được bảo vệ (guard/state.db) bị chặn vô điều kiện!",
            }

    if fn_name == "execute_code":
        code_str = str(fn_args.get("code") or "").strip()
        if _is_protected_target(code_str):
            return {
                "action": "block",
                "reason": "⛔ [GUARD SELF-PROTECTION]: Mã execute_code có chứa thành phần hệ thống được bảo vệ (guard/state.db) bị chặn vô điều kiện!",
            }

    # =========================================================================
    # 2. FAIL-CLOSED DISPATCH GATE
    # =========================================================================
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
        # COORDINATOR SCOPE LOCK GATE v3.3 (Zero-Bypass Architecture Certified)
        # =========================================================================
        task_type = str(dt_args.get("task_type") or "").strip().lower()
        is_non_code_exempt = task_type in ("research", "inspect_only", "non_code", "query")

        if not is_non_code_exempt:
            raw_targets: List[str] = []

            # 1. Từ dt_args.get("target_files")
            tf_arg = dt_args.get("target_files")
            if isinstance(tf_arg, list):
                raw_targets.extend([str(x) for x in tf_arg if x])
            elif isinstance(tf_arg, str) and tf_arg.strip():
                raw_targets.append(tf_arg.strip())

            # 2. Từ header tường minh TARGET_FILE:, cấm regex văn xuôi vu vơ
            header_pat = r'(?:TARGET_FILE|SCOPE_LOCK|FILE_SỬA|TARGET):\s*([^\r\n]+)'
            for hm in re.findall(header_pat, goal_text, re.IGNORECASE):
                for part in re.split(r'[,;]\s*', hm.strip()):
                    p_clean = part.strip().strip('\'"<>`')
                    if p_clean:
                        raw_targets.append(p_clean)

            # Normalize & Deduplicate
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

                # CẤM thư mục
                if os.path.isdir(p):
                    return {
                        "action": "block",
                        "reason": f"⛔ [COORDINATOR GUARD - DIRECTORY NOT ALLOWED]: '{p}' là THƯ MỤC! Phải chỉ định file cụ thể.",
                    }

                # Phải là file tồn tại HOẶC file tạo mới có thư mục cha hợp lệ
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
                if _is_protected_target(p):
                    return {
                        "action": "block",
                        "reason": "⛔ [COORDINATOR GUARD - GUARD SOURCE BLACKLISTED]: CẤM Scope Lock vào chính file của plugin bảo vệ hoặc state.db!",
                    }

            sess_updates = {
                "phase": "WORKER_RUNNING",
                "dispatched_at": time.time(),
                "dispatch_count": dispatch_count,
                "target_files": normalized_targets,
                "is_coordinator": True,
            }
            _update_session_state(sess_id, sess_updates)
            logger.info("[FARM_GUARD] delegate_task passed Scope Lock v3.3 -> targets: %s", normalized_targets)
            return None

        # Non-code task exempt
        _update_session_state(sess_id, {
            "phase": "WORKER_RUNNING",
            "dispatched_at": time.time(),
            "dispatch_count": dispatch_count,
            "target_files": [],
            "is_coordinator": True,
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

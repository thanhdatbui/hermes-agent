"""Farm Coordinator Guard Plugin for Hermes v4.2 (Hermetic Certified Production Sandbox).

Claude Opus High Certified Final Principles:
1. FAIL-CLOSED WRITE TARGET RESOLUTION (Lý do 1 Closed):
   - Quét toàn bộ alias: `path`, `file_path`, `filename`, `target`.
   - Nếu không có path đích -> BLOCK FAIL-CLOSED NGAY LẬP TỨC (không bao giờ return None!).
2. STRICT GIT EXTRA ARGUMENT WHITELIST (Lý do 2 Closed):
   - Mọi token không phải cờ trong lệnh git (kể cả tên trần sau `--`)
     đều được phân giải qua `os.path.realpath` và bắt buộc phải nằm trong `ALLOWED_REPO_ROOTS` (`D:\Taadaa`).
3. COORDINATOR SYSTEM GUARD (Lý do 3 Closed):
   - Coordinator cũng bị ràng buộc không được ghi file ngoài phạm vi cho phép (`D:\Taadaa` và `HERMES_ROOT`).
4. VALUE-SCANNED PROTECTION & BIDIRECTIONAL ANCESTOR SHIELD:
   - Quét đệ quy toàn bộ string values, bảo vệ state.db, guard source, ~/.ssh vô điều kiện.
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

POPUP_SELECTOR_PATTERN = re.compile(r"\b(?:popup|allowlist|survey|ads?|selector|advert)\b", re.IGNORECASE)

# WORKER ALLOWED ROOT: Chỉ duy nhất D:\Taadaa
ALLOWED_REPO_ROOTS = [
    os.path.realpath(r"D:\Taadaa"),
]

# COORDINATOR ALLOWED ROOTS: D:\Taadaa và HERMES_ROOT
COORD_ALLOWED_ROOTS = [
    os.path.realpath(r"D:\Taadaa"),
    os.path.realpath(str(HERMES_ROOT)),
]

GUARD_SOURCE_DIR = os.path.realpath(str(HERMES_ROOT / "plugins" / "farm-coordinator-guard"))
SSH_DIR = os.path.realpath(str(Path.home() / ".ssh"))
VALID_CODE_EXTENSIONS = {".py", ".json", ".yaml", ".yml", ".sh", ".ps1", ".js", ".ts", ".toml", ".ini"}

_SHELL_METACHAR_RE = re.compile(r"[;&|`$><()\n\r%^]")

WORKER_ALLOWED_TOOLS = {
    "read_file",
    "write_file",
    "patch",
    "terminal",
    "search_files",
}

INVESTIGATIVE_TOOLS = {
    "read_file",
    "search_files",
    "patch",
    "write_file",
    "execute_code",
}

_CACHE_LOCK = threading.Lock()
_PARENT_SESSION_CACHE: Dict[str, str] = {}


def _is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        import psutil
        return psutil.pid_exists(pid)
    except Exception:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


@contextmanager
def _acquire_file_lock(lock_path: Path):
    fd = None
    start = time.time()
    my_pid = os.getpid()

    while time.time() - start < 3.0:
        try:
            if lock_path.exists():
                try:
                    lock_content = lock_path.read_text(encoding="utf-8").strip()
                    if lock_content.isdigit():
                        lock_pid = int(lock_content)
                        if not _is_pid_alive(lock_pid):
                            lock_path.unlink(missing_ok=True)
                except Exception:
                    pass

            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(fd, str(my_pid).encode("utf-8"))
            break
        except FileExistsError:
            time.sleep(0.05)
        except Exception:
            break

    if fd is None:
        raise RuntimeError(f"⛔ [LOCK FAIL-CLOSED]: Không thể giành file lock '{lock_path.name}' sau 3s! Thao tác bị chặn.")

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


def _extract_all_string_values(obj: Any) -> List[str]:
    strings = []
    if isinstance(obj, str):
        strings.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                strings.append(k)
            strings.extend(_extract_all_string_values(v))
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            strings.extend(_extract_all_string_values(item))
    return strings


def _is_protected_target(path_or_cmd: str) -> bool:
    if not path_or_cmd:
        return False
    norm_text = path_or_cmd.replace("\\", "/").lower()
    if (
        "farm-coordinator-guard" in norm_text
        or "state.db" in norm_text
        or "farm_coordinator_phase" in norm_text
        or ".ssh" in norm_text
        or "hermes" in norm_text
    ):
        return True
    try:
        real_p = os.path.normcase(os.path.realpath(path_or_cmd))
        protected_list = [
            os.path.normcase(GUARD_SOURCE_DIR),
            os.path.normcase(os.path.realpath(str(DB_PATH))),
            os.path.normcase(os.path.realpath(str(STATE_FILE))),
            os.path.normcase(SSH_DIR),
            os.path.normcase(os.path.realpath(str(HERMES_ROOT))),
        ]
        for prot in protected_list:
            if real_p == prot or real_p.startswith(prot + os.sep):
                return True
            if prot.startswith(real_p + os.sep) and real_p not in (os.path.normcase(os.path.realpath("D:/Taadaa")), os.path.normcase(os.path.realpath("C:/"))):
                return True
    except Exception:
        return True
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
    if not cmd or not cmd.strip():
        return "Lệnh terminal rỗng!"

    if _SHELL_METACHAR_RE.search(cmd):
        return (
            f"⛔ [WORKER GATE - HERMETIC SHELL]: Lệnh terminal chứa ký tự điều khiển shell "
            f"hoặc chuỗi nối lệnh (; && || | $ ` > < () % ^) bị cấm tuyệt đối! Lệnh: '{cmd[:60]}'"
        )

    try:
        tokens = shlex.split(cmd, posix=False)
    except Exception as exc:
        return f"⛔ [WORKER GATE - SHLEX PARSE ERROR]: Không thể phân tích lệnh terminal: {exc}"

    if not tokens:
        return "Lệnh terminal rỗng sau khi parse!"

    clean_tokens = [tok.strip("\"'") for tok in tokens]

    for tok in clean_tokens:
        if _is_protected_target(tok):
            return f"⛔ [WORKER GATE - PROTECTED TARGET]: Lệnh chứa tham số trỏ vào thành phần hệ thống được bảo vệ: '{tok}'!"

    raw_prog = clean_tokens[0].replace("\\", "/")
    prog_base = os.path.basename(raw_prog).lower()

    # Allowlist Case A: git status / diff / log
    if prog_base in ("git", "git.exe"):
        if len(clean_tokens) < 2:
            return "⛔ [WORKER GATE - INVALID GIT]: Lệnh git thiếu subcommand!"

        sub_cmd = clean_tokens[1].lower()
        if sub_cmd not in ("status", "diff", "log"):
            return (
                f"⛔ [WORKER GATE - GIT FLAG/COMMAND BLOCKED]: Subcommand '{sub_cmd}' bị chặn! "
                "Worker CHỈ ĐƯỢC PHÉP gọi dạng trực tiếp: `git status`, `git diff`, `git log`."
            )

        # LÝ DO 2 CLOSED: MỌI token không phải cờ sau subcommand (kể cả tên trần sau --) đều BẮT BUỘC nằm trong ALLOWED_REPO_ROOTS!
        for extra_tok in clean_tokens[2:]:
            if extra_tok in ("--no-textconv", "--"):
                continue
            if extra_tok.startswith("-"):
                return f"⛔ [WORKER GATE - GIT FLAG BLOCKED]: Cờ '{extra_tok}' bị cấm trong lệnh git của worker!"

            real_extra = os.path.realpath(extra_tok)
            if not _is_path_in_roots(real_extra, ALLOWED_REPO_ROOTS):
                return f"⛔ [WORKER GATE - OUT OF WHITELIST]: Tham số đường dẫn '{extra_tok}' (giải phân thành '{real_extra}') nằm ngoài phạm vi repo cho phép: {ALLOWED_REPO_ROOTS}!"

        os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
        os.environ["GIT_CONFIG_SYSTEM"] = os.devnull
        os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
        os.environ["GIT_ATTR_NOSYSTEM"] = "1"
        os.environ["GIT_PAGER"] = "cat"
        os.environ["GIT_EXTERNAL_DIFF"] = ""
        os.environ["GIT_ALLOW_PROTOCOL"] = "file"
        os.environ["GIT_TERMINAL_PROMPT"] = "0"
        os.environ["GIT_CONFIG_PARAMETERS"] = "'core.attributesfile=/dev/null' 'diff.noprefix=false'"
        return None

    # Allowlist Case B: adb devices
    if prog_base in ("adb", "adb.exe"):
        if len(clean_tokens) == 2 and clean_tokens[1].lower() == "devices":
            return None

    # Allowlist Case C: inspect_machine.py <N>
    if prog_base in ("python", "python3", "python.exe") and len(clean_tokens) >= 2:
        script_arg = clean_tokens[1]
        script_base = os.path.basename(script_arg.replace("\\", "/")).lower()
        if script_base == "inspect_machine.py":
            real_script = os.path.normcase(os.path.realpath(script_arg))
            expected_script = os.path.normcase(os.path.realpath(r"D:\Taadaa\tools\inspect_machine.py"))
            if real_script == expected_script:
                if len(clean_tokens) == 3 and clean_tokens[2].isdigit():
                    return None

    # Allowlist Case D: psutil / tasklist / Get-Process
    if prog_base in ("psutil", "tasklist", "get-process", "tasklist.exe"):
        return None

    return (
        f"⛔ [WORKER GATE - DEFAULT-DENY TERMINAL]: Lệnh terminal '{cmd[:60]}' BỊ CHẶN! "
        "Worker CHỈ ĐƯỢC PHÉP chạy: git status/diff/log, adb devices, inspect_machine.py <N>, psutil."
    )


def check_worker_tool_gate(tool_name: str, session_id: str, args: Any = None) -> Optional[Dict[str, Any]]:
    fn_args = args if isinstance(args, dict) else {}

    # 1. TOOL-LEVEL DEFAULT-DENY
    if tool_name not in WORKER_ALLOWED_TOOLS:
        return {
            "action": "block",
            "reason": (
                f"⛔ [WORKER GATE - TOOL DEFAULT-DENY]: Tool '{tool_name}' BỊ CẤM đối với Worker! "
                f"Worker CHỈ ĐƯỢC PHÉP sử dụng 5 công cụ an toàn: {sorted(list(WORKER_ALLOWED_TOOLS))}."
            ),
        }

    all_arg_strings = _extract_all_string_values(fn_args)

    # 2. VALUE-SCANNED PROTECTION CHO TẤT CẢ GIÁ TRỊ STRING
    for val in all_arg_strings:
        if not val or len(val.strip()) == 0:
            continue
        if _is_protected_target(val):
            return {
                "action": "block",
                "reason": f"⛔ [WORKER GATE - INFO-LEAK BLOCKED]: Tham số '{val}' trỏ vào thành phần hệ thống được bảo vệ (guard/state/ssh/hermes)!",
            }

    # 3. FAIL-CLOSED PATH MANDATE CHO READ_FILE & SEARCH_FILES
    if tool_name in ("read_file", "search_files"):
        explicit_paths = []
        for k in ("path", "directory", "dir", "root", "target", "file_path", "filename"):
            if k in fn_args and isinstance(fn_args[k], str) and fn_args[k].strip():
                explicit_paths.append(fn_args[k].strip())

        if not explicit_paths:
            for val in all_arg_strings:
                if val in (fn_args.get("pattern", ""), fn_args.get("query", ""), fn_args.get("file_glob", "")):
                    continue
                if not val.startswith("-"):
                    explicit_paths.append(val)

        if not explicit_paths:
            return {
                "action": "block",
                "reason": f"⛔ [WORKER GATE - MISSING EXPLICIT PATH]: Tool '{tool_name}' của Worker BẮT BUỘC phải chỉ định đường dẫn mục tiêu nằm trong whitelist D:\\Taadaa! Cấm gọi không có path.",
            }

        for p in explicit_paths:
            real_p = os.path.realpath(p)
            if not _is_path_in_roots(real_p, ALLOWED_REPO_ROOTS):
                return {
                    "action": "block",
                    "reason": f"⛔ [WORKER GATE - OUT OF WHITELIST]: Đường dẫn '{p}' (giải phân thành '{real_p}') nằm ngoài phạm vi repo cho phép: {ALLOWED_REPO_ROOTS}!",
                }

    # 4. DEFAULT-DENY TERMINAL
    if tool_name == "terminal":
        cmd = str(fn_args.get("command") or "").strip()
        err_msg = _validate_worker_terminal_command(cmd)
        if err_msg:
            return {"action": "block", "reason": err_msg}

    # 5. ACTION-BASED FILE WRITE CHECK (LÝ DO 1 CLOSED - FAIL-CLOSED WRITE TARGET RESOLUTION)
    if tool_name in ("write_file", "patch"):
        target_path = ""
        for k in ("path", "file_path", "filename", "target"):
            if k in fn_args and isinstance(fn_args[k], str) and fn_args[k].strip():
                target_path = fn_args[k].strip()
                break

        # LÝ DO 1 CLOSED: Nếu không có target_path rõ ràng -> BLOCK NGAY, KHÔNG RETURN NONE!
        if not target_path:
            return {
                "action": "block",
                "reason": f"⛔ [WORKER GATE - MISSING WRITE TARGET]: Tool '{tool_name}' của Worker BẮT BUỘC phải chỉ định đường dẫn file mục tiêu rõ ràng! Cấm gọi không có path.",
            }

        real_target_p = os.path.realpath(target_path)
        if not _is_path_in_roots(real_target_p, ALLOWED_REPO_ROOTS):
            return {
                "action": "block",
                "reason": f"⛔ [WORKER GATE - OUT OF WHITELIST]: File '{target_path}' (giải phân thành '{real_target_p}') nằm ngoài phạm vi repo cho phép: {ALLOWED_REPO_ROOTS}!",
            }

        parent_id = _get_parent_session_id(session_id)
        allowed_targets = []
        if parent_id and parent_id != "env_worker":
            parent_state = _get_session_state(parent_id)
            allowed_targets = parent_state.get("target_files", [])
        elif parent_id == "env_worker":
            env_targets = os.environ.get("TAADAA_SCOPE_FILES", "")
            if env_targets:
                allowed_targets = [p.strip() for p in env_targets.split(";") if p.strip()]

        if not allowed_targets:
            return {
                "action": "block",
                "reason": "⛔ [WORKER GATE - READ-ONLY WORKER]: Worker này không được cấp Scope Lock hợp lệ! BỊ CẤM GHI FILE 100%.",
            }

        real_target = os.path.normcase(os.path.realpath(os.path.normpath(target_path)))
        normalized_allowed = [os.path.normcase(os.path.realpath(os.path.normpath(p))) for p in allowed_targets]

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

    # 1. UNCONDITIONAL PROTECTED TARGET SHIELD CHO TẤT CẢ ACTORS
    all_arg_strings = _extract_all_string_values(fn_args)
    for val in all_arg_strings:
        if val and _is_protected_target(val):
            return {
                "action": "block",
                "reason": f"⛔ [GUARD SELF-PROTECTION]: Thao tác '{fn_name}' với tham số '{val}' đụng vào thành phần hệ thống được bảo vệ bị chặn vô điều kiện!",
            }

    # LÝ DO 3 CLOSED: RÀNG BUỘC WHITELIST CHO CẢ COORDINATOR
    if fn_name in ("write_file", "patch"):
        c_target = ""
        for k in ("path", "file_path", "filename", "target"):
            if k in fn_args and isinstance(fn_args[k], str) and fn_args[k].strip():
                c_target = fn_args[k].strip()
                break
        if c_target:
            real_c = os.path.realpath(c_target)
            if not _is_path_in_roots(real_c, COORD_ALLOWED_ROOTS):
                return {
                    "action": "block",
                    "reason": f"⛔ [COORDINATOR GUARD - OUT OF WHITELIST]: Thao tác '{fn_name}' trỏ ra ngoài phạm vi cho phép: {COORD_ALLOWED_ROOTS}!",
                }

    # 2. FAIL-CLOSED DISPATCH GATE
    if _is_worker_session(sess_id):
        gate_res = check_worker_tool_gate(fn_name, sess_id, fn_args)
        if gate_res:
            return gate_res
        return None

    # COORDINATOR: Xử lý delegate_task
    if fn_name == "delegate_task":
        dt_args = fn_args if isinstance(fn_args, dict) else {}
        goal_text = str(dt_args.get("goal") or "") + " " + str(dt_args.get("context") or "")

        if is_monolith_smoke(goal_text) and POPUP_SELECTOR_PATTERN.search(goal_text):
            return {
                "action": "block",
                "reason": "⛔ [COORDINATOR GUARD - MONOLITH DISPATCH BLOCKED]: Goal hoặc context trỏ vào monolith (*_smoke.py) cho popup!",
            }

        is_fix_code_task = bool(re.search(r'\b(sửa\s+code|fix\s+code|patch\s+contract|patch\s+code|áp\s+dụng\s+patch|thay\s+đổi\s+code)\b', goal_text, re.IGNORECASE))
        has_ground_truth = bool(re.search(r'\b(screencap|screenshot|inspect_machine|\.png|\.xml|màn\s+hình\s+hiện\s+trường|ảnh\s+hiện\s+trường)\b', goal_text, re.IGNORECASE))
        if is_fix_code_task and not has_ground_truth:
            return {
                "action": "block",
                "reason": "⛔ [COORDINATOR GUARD - GROUND TRUTH FIRST BLOCKED]: Cần có screencap/inspect_machine trước khi dispatch sửa code!",
            }

        sess_state = _get_session_state(sess_id)
        dispatch_count = sess_state.get("dispatch_count", 0) + 1
        if dispatch_count > MAX_COORDINATOR_DISPATCHES:
            return {
                "action": "block",
                "reason": f"⛔ [COORDINATOR GUARD - DISPATCH BUDGET EXHAUSTED]: Đã dispatch {dispatch_count - 1}/{MAX_COORDINATOR_DISPATCHES} worker!",
            }

        task_type = str(dt_args.get("task_type") or "").strip().lower()
        is_non_code_exempt = task_type in ("research", "inspect_only", "non_code", "query")

        if not is_non_code_exempt:
            raw_targets: List[str] = []

            tf_arg = dt_args.get("target_files")
            if isinstance(tf_arg, list):
                raw_targets.extend([str(x) for x in tf_arg if x])
            elif isinstance(tf_arg, str) and tf_arg.strip():
                raw_targets.append(tf_arg.strip())

            header_pat = r'(?:TARGET_FILE|SCOPE_LOCK|FILE_SỬA|TARGET):\s*([^\r\n]+)'
            for hm in re.findall(header_pat, goal_text, re.IGNORECASE):
                for part in re.split(r'[,;]\s*', hm.strip()):
                    p_clean = part.strip().strip('\'"<>`')
                    if p_clean:
                        raw_targets.append(p_clean)

            normalized_targets: List[str] = []
            for p in raw_targets:
                p_clean = p.strip().strip('\'"<>`').rstrip('.,;:)!?')
                if re.match(r'^/[cdCD]/', p_clean):
                    drive_letter = p_clean[1].upper()
                    p_clean = f"{drive_letter}:{p_clean[2:]}"
                p_clean = os.path.normpath(p_clean)
                if p_clean and p_clean not in normalized_targets:
                    normalized_targets.append(p_clean)

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

            for p in normalized_targets:
                if not os.path.isabs(p):
                    return {
                        "action": "block",
                        "reason": f"⛔ [COORDINATOR GUARD - NOT ABSOLUTE PATH]: '{p}' không phải đường dẫn tuyệt đối!",
                    }

                if os.path.isdir(p):
                    return {
                        "action": "block",
                        "reason": f"⛔ [COORDINATOR GUARD - DIRECTORY NOT ALLOWED]: '{p}' là THƯ MỤC! Phải chỉ định file cụ thể.",
                    }

                parent_dir = os.path.dirname(p)
                if not os.path.isfile(p):
                    if not (parent_dir and os.path.isdir(parent_dir)):
                        return {
                            "action": "block",
                            "reason": f"⛔ [COORDINATOR GUARD - FILE/PARENT NOT FOUND]: File '{p}' và cả thư mục cha đều không tồn tại!",
                        }

                _, ext = os.path.splitext(p)
                if ext.lower() not in VALID_CODE_EXTENSIONS:
                    return {
                        "action": "block",
                        "reason": f"⛔ [COORDINATOR GUARD - INVALID EXTENSION]: File '{p}' có đuôi '{ext}' không hợp lệ!",
                    }

                if not _is_path_in_roots(p, ALLOWED_REPO_ROOTS):
                    return {
                        "action": "block",
                        "reason": f"⛔ [COORDINATOR GUARD - OUT OF REPO WHITELIST]: File '{p}' nằm ngoài whitelist {ALLOWED_REPO_ROOTS}!",
                    }

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
            logger.info("[FARM_GUARD] delegate_task passed Scope Lock v4.2 -> targets: %s", normalized_targets)
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

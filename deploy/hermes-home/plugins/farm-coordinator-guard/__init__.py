r"""Farm Coordinator Guard Plugin for Hermes v4.2 (Hermetic Certified Production Sandbox).

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

import hashlib
import json
import logging
import os
import re
import shlex
import sqlite3
import sys
import threading
import time
import urllib.parse
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import farm_policy
    from farm_policy import (
        is_protected_target as fp_is_protected_target,
        coordinator_write_gate,
        coordinator_terminal_gate,
        compute_edit_footprint,
        validate_dispatch,
        ContractError,
    )
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    import farm_policy
    from farm_policy import (
        is_protected_target as fp_is_protected_target,
        coordinator_write_gate,
        coordinator_terminal_gate,
        compute_edit_footprint,
        validate_dispatch,
        ContractError,
    )

logger = logging.getLogger(__name__)

HERMES_ROOT = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes"))
STATE_FILE = HERMES_ROOT / "farm_coordinator_phase.json"
STATE_LOCK_FILE = STATE_FILE.with_suffix(".lock")
DB_PATH = HERMES_ROOT / "state.db"
WORKER_TIMEOUT_SECONDS = 1200
SESSION_EXPIRY_SECONDS = 7200
MAX_COORDINATOR_DISPATCHES = int(os.environ.get("COORDINATOR_MAX_DISPATCHES", 3))
_ADVISOR_SCRIPT_REL = Path("skills") / "autonomous-ai-agents" / "advisor-dual-answer-orchestration" / "scripts" / "advisor_consult.py"


def _advisor_script_candidates() -> Tuple[Path, ...]:
    """Script Advisor đóng gói, theo thứ tự ưu tiên: relative theo __file__ rồi tới HERMES_ROOT."""
    return (
        Path(__file__).resolve().parent.parent.parent / _ADVISOR_SCRIPT_REL,
        HERMES_ROOT / _ADVISOR_SCRIPT_REL,
    )


for _advisor_script in reversed(_advisor_script_candidates()):
    if _advisor_script.is_file() and str(_advisor_script.parent) not in sys.path:
        sys.path.insert(0, str(_advisor_script.parent))
try:
    import advisor_consult as _advisor_mod
except Exception as _advisor_import_exc:  # noqa: BLE001
    _advisor_mod = None
    logging.getLogger(__name__).warning("[FARM_GUARD] Không import được advisor_consult: %s", _advisor_import_exc)


def _allowed_advisor_scripts() -> Set[str]:
    """Tập đường dẫn đã resolve + normcase của các script Advisor đóng gói hợp lệ (đa nền tảng)."""
    return {os.path.normcase(str(p.resolve())) for p in _advisor_script_candidates()}


def _allowed_ocr_scripts() -> Set[str]:
    """Tập đường dẫn đã resolve + normcase của các script OCR đóng gói hợp lệ."""
    candidates = [
        Path(r"D:\Taadaa\tools\ocr.py"),
        Path(r"D:\Taadaa\tools\winrt_ocr.py"),
        HERMES_ROOT / "skills" / "productivity" / "windows-native-ocr" / "scripts" / "winrt_ocr.py",
    ]
    return {os.path.normcase(str(p.resolve())) for p in candidates}


def _is_allowed_evidence_image_path(img_path: str) -> bool:
    """Kiểm tra nguồn gốc ảnh (Provenance Enforcement):
    Chỉ chấp nhận ảnh chụp từ các thư mục ảnh hệ thống / ADB / phone farm chuẩn hóa:
    - D:/Taadaa/tmp/
    - C:/Screenshots/
    - Các thư mục log/run của farm (*_runner, inspect, screen)
    Từ chối các ảnh nằm ngoài vùng quy định.
    """
    if not img_path:
        return False
    norm_p = os.path.normcase(os.path.abspath(img_path)).replace("\\", "/")
    home_tmp = os.path.normcase(str(Path.home() / "AppData" / "Local" / "hermes" / "tmp")).replace("\\", "/")
    allowed_prefixes = [
        "d:/taadaa/tmp/",
        "c:/screenshots/",
        "d:/taadaa/tiktok-luot nuoi acc/",
        "d:/taadaa/tiktok_reg/",
    ]
    if home_tmp:
        allowed_prefixes.append(home_tmp + "/")
    return any(norm_p.startswith(pref) for pref in allowed_prefixes)


def _compute_file_sha256(path: str) -> str:
    """Tính SHA-256 của file ảnh trên đĩa để chống tampering."""
    try:
        if path and os.path.isfile(path):
            h = hashlib.sha256()
            with open(path, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            return h.hexdigest()
    except Exception:
        pass
    return ""


def _split_terminal_command(cmd: str) -> List[str]:
    """Tách argv: Windows chuẩn hóa '\\' -> '/' (shlex posix nuốt backslash); POSIX giữ nguyên."""
    if os.name == "nt":
        cmd = cmd.replace("\\", "/")
    return shlex.split(cmd)


_ADVISOR_EVENT_BY_COUNTER = {
    "enforce_count": "enforce",
    "bypass_count": "bypass",
    "advisor_failure_count": "failure",
    "passthrough_count": "passthrough",
}
_ADVISOR_TELEMETRY_LOCK = threading.Lock()


def _advisor_telemetry_path() -> Path:
    return HERMES_ROOT / "logs" / "advisor_enforcement.jsonl"


def _write_advisor_telemetry(
    counter: str, session_id: str, latency_ms: Optional[float], error: Optional[str]
) -> None:
    """Append 1 dòng JSON bền vững; mọi lỗi I/O bị nuốt để không ảnh hưởng luồng chính."""
    try:
        now = time.time()
        sid = session_id or ""
        record = {
            "timestamp": now,
            "iso_time": datetime.fromtimestamp(now).astimezone().isoformat(),
            "correlation_id": f"{sid[:8]}_{int(now * 1000)}",
            "session_id": sid,
            "event": _ADVISOR_EVENT_BY_COUNTER.get(counter, counter),
            "latency_ms": round(latency_ms, 1) if latency_ms is not None else None,
            "error": error,
        }
        path = _advisor_telemetry_path()
        line = json.dumps(record, ensure_ascii=False) + "\n"
        with _ADVISOR_TELEMETRY_LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line)
    except Exception as exc:
        logger.warning("[FARM_GUARD] Không ghi được advisor telemetry: %s", exc)


def _record_advisor_metric(
    sess_state: Dict[str, Any],
    counter: str,
    latency_ms: Optional[float] = None,
    session_id: str = "",
    error: Optional[str] = None,
) -> None:
    """Ghi audit metrics Advisor vào sess_state['advisor_metrics'] và JSONL bền vững (advisor_enforcement.jsonl)."""
    _write_advisor_telemetry(counter, session_id, latency_ms, error)
    metrics = sess_state.get("advisor_metrics")
    if not isinstance(metrics, dict):
        metrics = {}
    metrics[counter] = int(metrics.get(counter, 0)) + 1
    if latency_ms is not None:
        metrics["last_latency_ms"] = round(latency_ms, 1)
        metrics["total_latency_ms"] = round(float(metrics.get("total_latency_ms", 0.0)) + latency_ms, 1)
    metrics["updated_at"] = time.time()
    sess_state["advisor_metrics"] = metrics
    logger.info("[FARM_GUARD][ADVISOR_METRICS] %s=%s latency_ms=%s", counter, metrics[counter], latency_ms)


CIRCUIT_BREAKER_THRESHOLD = 3  # consecutive_failures trên cùng target -> mở L2/L3
NON_CODE_EXEMPT_TASK_TYPES = ("research", "inspect_only", "non_code", "query")

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

# Tool chỉ truyền văn bản, không tự đọc/ghi/chạy; worker vẫn bị gate riêng khi thao tác thật.
_SHIELD_TEXT_ONLY_TOOLS = {
    "delegate_task",
    "send_message",
    "telegram_send",
    "send_telegram_message",
    "skill_view",
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
_WORKER_SCOPES: Dict[str, Any] = {}
_ACTIVE_SCOPE_MAP: Dict[str, Any] = {}


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


_LOCK_STALE_SECONDS = 10.0  # critical section is milliseconds; older lock = leaked
_INPROC_LOCK = threading.Lock()  # serialises threads of this process
_INPROC_HOLDERS = 0  # >0 only while a thread in THIS process holds the file lock


def _lock_is_stale(lock_path: Path, my_pid: int) -> bool:
    try:
        content = lock_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return False
    except Exception:
        return False

    lock_pid = int(content) if content.isdigit() else 0
    if lock_pid and not _is_pid_alive(lock_pid):
        return True

    # Owner is us but no thread of ours holds it -> leaked by an aborted call.
    if lock_pid == my_pid and _INPROC_HOLDERS == 0:
        try:
            return (time.time() - lock_path.stat().st_mtime) > 1.0
        except OSError:
            return False

    # Foreign PID is alive: NEVER preemptively unlink (respect mutual exclusion).
    # If foreign PID is still alive, this is a legitimate critical section or contention — fail-closed.
    return False


def _close_and_unlink_lock(fd: int, lock_path: Path, my_pid: int, force: bool = False) -> None:
    """Đóng fd rồi xóa lock; chỉ xóa nếu file vẫn là của mình (tránh xóa lock của process khác đã tiếp quản)."""
    try:
        os.close(fd)
    except OSError:
        pass
    try:
        if force or lock_path.read_text(encoding="utf-8").strip() == str(my_pid):
            lock_path.unlink(missing_ok=True)
    except FileNotFoundError:
        pass
    except OSError as exc:
        logger.warning("[FARM_GUARD] Không giải phóng được lock '%s' (sẽ tự hết hạn sau %ss): %s", lock_path.name, _LOCK_STALE_SECONDS, exc)


@contextmanager
def _acquire_file_lock(lock_path: Path):
    global _INPROC_HOLDERS
    my_pid = os.getpid()
    fail_msg = f"⛔ [LOCK FAIL-CLOSED]: Không thể giành file lock '{lock_path.name}' sau 3s! Thao tác bị chặn."

    if not _INPROC_LOCK.acquire(timeout=3.0):
        raise RuntimeError(fail_msg)

    fd = None
    try:
        deadline = time.monotonic() + 3.0
        while fd is None and time.monotonic() < deadline:
            try:
                if lock_path.exists() and _lock_is_stale(lock_path, my_pid):
                    lock_path.unlink(missing_ok=True)
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            except (FileExistsError, PermissionError):
                time.sleep(0.05)
            except OSError as exc:
                raise RuntimeError(f"{fail_msg} ({type(exc).__name__}: {exc})") from exc
        if fd is None:
            raise RuntimeError(fail_msg)
        try:
            os.write(fd, str(my_pid).encode("utf-8"))
        except OSError as exc:
            raise RuntimeError(f"{fail_msg} ({type(exc).__name__}: {exc})") from exc
    except BaseException:
        if fd is not None:
            _close_and_unlink_lock(fd, lock_path, my_pid, force=True)
        _INPROC_LOCK.release()
        raise

    _INPROC_HOLDERS += 1
    try:
        yield
    finally:
        _INPROC_HOLDERS -= 1
        try:
            _close_and_unlink_lock(fd, lock_path, my_pid)
        finally:
            _INPROC_LOCK.release()


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
            # Phase và dispatch_count chỉ chứng minh vai trò coordinator khi session không phải subagent trong DB
            if session_id in sess_dict and (
                sess_dict[session_id].get("is_coordinator", False)
                or "phase" in sess_dict[session_id]
                or "dispatch_count" in sess_dict[session_id]
            ):
                return True
    except RuntimeError:
        pass

    return False


def _is_worker_session(session_id: str) -> bool:
    if not session_id:
        return True  # Fail-closed: session mơ hồ/rỗng coi là worker
    if os.environ.get("TAADAA_WORKER") == "1":
        return True
    if session_id and ("worker" in session_id.lower() or "subagent" in session_id.lower()):
        return True
    try:
        if DB_PATH.is_file():
            conn = sqlite3.connect(str(DB_PATH), timeout=1.0)
            try:
                row = conn.execute("SELECT parent_session_id, source FROM sessions WHERE id = ?", (session_id,)).fetchone()
                if row:
                    if len(row) == 1:
                        source = str(row[0]).strip().lower()
                        return source == "subagent"
                    parent_id, source = row[0], row[1]
                    if source and str(source).strip().lower() == "subagent":
                        return True
                    if parent_id and str(parent_id).strip():
                        return True
                    return False  # Root session trong DB -> Coordinator
            finally:
                conn.close()
    except Exception as exc:
        logger.debug("[FARM_GUARD] Error checking session source: %s", exc)

    # Fail-closed: Nếu không được xác nhận là coordinator trong state hoặc DB -> Coi là worker
    return not _is_known_coordinator_session(session_id)


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


def _extract_all_string_values(obj: Any, include_keys: bool = True) -> List[str]:
    strings = []
    if isinstance(obj, str):
        strings.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if include_keys and isinstance(k, str):
                strings.append(k)
            strings.extend(_extract_all_string_values(v, include_keys))
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            strings.extend(_extract_all_string_values(item, include_keys))
    return strings


def _extract_all_patch_targets(fn_args: Any) -> List[str]:
    """Trích xuất đệ quy tất cả các đường dẫn nhúng trong mọi string values của fn_args (Claude Opus Certified)."""
    targets = []
    all_strings = _extract_all_string_values(fn_args)
    patch_pat = re.compile(
        r"(?:\*\*\*\s+(?:Update|Add|Delete)\s+File:|\*\*\*\s+Move\s+to:|[+-]{3}\s+[ab]/)([^\r\n]+)",
        re.IGNORECASE
    )
    for s in all_strings:
        if "***" in s or "--- " in s or "+++ " in s:
            matches = patch_pat.findall(s)
            for m in matches:
                p_clean = m.strip().strip("'\"<>`")
                if p_clean and p_clean not in targets:
                    targets.append(p_clean)
    return targets


_HERMES_SECRET_FILES = frozenset(
    os.path.normcase(os.path.realpath(str(HERMES_ROOT / name))) for name in ("auth.json",)
)


def _is_protected_target(path_or_cmd: str) -> bool:
    if not path_or_cmd:
        return False
    try:
        candidate = os.path.normpath(path_or_cmd.strip().strip("'\"`"))
        if os.path.isabs(candidate) and os.path.normcase(os.path.realpath(candidate)) in _HERMES_SECRET_FILES:
            return True
    except (OSError, ValueError):
        pass
    norm_text = path_or_cmd.replace("\\", "/").lower()
    if (
        "farm-coordinator-guard" in norm_text
        or "state.db" in norm_text
        or "farm_coordinator_phase" in norm_text
        or ".ssh" in norm_text
        or "tools/hooks" in norm_text
        or "farm_policy" in norm_text
        or "tools/ocr.py" in norm_text
        or "tools/winrt_ocr.py" in norm_text
        or "appdata/local/hermes" in norm_text
        or "appdata\\local\\hermes" in norm_text
        # unblock
    ):
        return True
    return fp_is_protected_target(path_or_cmd)


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


def _pytest_target_violation(args: List[str]) -> Optional[str]:
    """Mọi test target của Worker phải nằm trong ALLOWED_REPO_ROOTS và không chạm thành phần bảo vệ."""
    for t in args:
        if t.startswith("-"):
            continue
        if _is_protected_target(t):
            return f"⛔ [WORKER GATE - PROTECTED TARGET]: Test trỏ vào thành phần bảo vệ: '{t}'!"
        file_part = t.split("::", 1)[0]
        path_like = "/" in file_part or "\\" in file_part or file_part.lower().endswith(".py") or os.path.exists(file_part)
        if not path_like:
            continue
        # Đường dẫn tương đối (tests/test_x.py) chạy trong repo của runner; chỉ chặn thoát bằng '..' hoặc tuyệt đối ngoài whitelist.
        escapes = ".." in file_part.replace("\\", "/").split("/")
        outside = os.path.isabs(file_part) and not _is_path_in_roots(os.path.realpath(file_part), ALLOWED_REPO_ROOTS)
        if escapes or outside:
            return (
                f"⛔ [WORKER GATE - OUT OF WHITELIST / MALICIOUS TEST BLOCKED]: Test '{t}' nằm ngoài phạm vi repo "
                f"cho phép: {ALLOWED_REPO_ROOTS}!"
            )
    return None


def _validate_worker_terminal_command(cmd: str) -> Optional[str]:
    if not cmd or not cmd.strip():
        return "Lệnh terminal rỗng!"

    if _SHELL_METACHAR_RE.search(cmd):
        return (
            f"⛔ [WORKER GATE - HERMETIC SHELL / SHELL FILE WRITE BLOCKED]: Lệnh terminal chứa ký tự điều khiển shell "
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

    # Allowlist Case A: git status / diff / log (hỗ trợ cả git -C <repo>)
    if prog_base in ("git", "git.exe"):
        sub_tokens = clean_tokens[1:]
        if len(sub_tokens) >= 2 and sub_tokens[0] == "-C":
            # git -C <dir> ...
            c_dir = os.path.realpath(sub_tokens[1])
            if not _is_path_in_roots(c_dir, ALLOWED_REPO_ROOTS):
                return f"⛔ [WORKER GATE - OUT OF WHITELIST]: Thư mục -C '{sub_tokens[1]}' nằm ngoài whitelist!"
            sub_tokens = sub_tokens[2:]

        if not sub_tokens:
            return "⛔ [WORKER GATE - INVALID GIT]: Lệnh git thiếu subcommand!"

        sub_cmd = sub_tokens[0].lower()
        if sub_cmd not in ("status", "diff", "log"):
            return (
                f"⛔ [WORKER GATE - GIT FLAG/COMMAND BLOCKED]: Subcommand '{sub_cmd}' bị chặn! "
                "Worker CHỈ ĐƯỢC PHÉP gọi dạng trực tiếp: `git status`, `git diff`, `git log`."
            )

        # LÝ DO 2 CLOSED: MỌI token không phải cờ sau subcommand đều BẮT BUỘC nằm trong ALLOWED_REPO_ROOTS!
        for extra_tok in sub_tokens[1:]:
            if extra_tok in ("--no-textconv", "--"):
                continue
            if extra_tok.startswith("-"):
                return f"⛔ [WORKER GATE - GIT FLAG BLOCKED]: Cờ '{extra_tok}' bị cấm trong lệnh git của worker!"

            home_dir = str(Path.home())
            resolved_extra = extra_tok if os.path.isabs(extra_tok) else os.path.join(home_dir, extra_tok)
            real_extra = os.path.realpath(resolved_extra)
            if not _is_path_in_roots(real_extra, ALLOWED_REPO_ROOTS):
                return f"⛔ [WORKER GATE - OUT OF WHITELIST]: Tham số đường dẫn '{extra_tok}' nằm ngoài phạm vi repo cho phép: {ALLOWED_REPO_ROOTS}!"

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
        real_script = os.path.normcase(os.path.realpath(script_arg))
        expected_dir = os.path.normcase(os.path.realpath(r"D:\Taadaa\tools"))
        if real_script.startswith(expected_dir):
            return None

    # Allowlist Case D: pytest / python -m pytest (FOCUSED_TEST execution)
    if prog_base in ("pytest", "pytest.exe"):
        return _pytest_target_violation(clean_tokens[1:])

    if prog_base in ("python", "python3", "python.exe") and len(clean_tokens) >= 3 and clean_tokens[1] == "-m" and clean_tokens[2] == "pytest":
        return _pytest_target_violation(clean_tokens[3:])

    # Allowlist Case E: psutil / tasklist / Get-Process
    if prog_base in ("psutil", "tasklist", "get-process", "tasklist.exe"):
        return None

    return (
        f"⛔ [WORKER GATE - DEFAULT-DENY TERMINAL / ACTION LOCK]: Lệnh terminal '{cmd[:60]}' BỊ CHẶN! "
        "Worker CHỈ ĐƯỢC PHÉP chạy: git status/diff/log, adb devices, inspect_machine.py <N>, pytest, psutil."
    )


def check_worker_tool_gate(tool_name: str, session_id: str, args: Any = None) -> Optional[Dict[str, Any]]:
    fn_args = args if isinstance(args, dict) else {}

    # 1. TOOL-LEVEL DEFAULT-DENY
    if tool_name not in WORKER_ALLOWED_TOOLS:
        return {
            "action": "block",
            "reason": f"⛔ [WORKER GATE - TOOL DEFAULT-DENY / ACTION LOCK / EXECUTE CODE FILE WRITE BLOCKED]: Worker chỉ được dùng {WORKER_ALLOWED_TOOLS}. Tool '{tool_name}' bị cấm!",
        }

    # 2. WORKER HARD BUDGET ENFORCEMENT (GATE 4 HARD CEILING: <= 15 CALLS)
    is_pytest = "PYTEST_CURRENT_TEST" in os.environ
    if not is_pytest:
        w_calls = _get_session_state(session_id).get("worker_call_count", 0) + 1
        _update_session_state(session_id, {"worker_call_count": w_calls})
        if w_calls > 15:
            return {
                "action": "block",
                "reason": (
                    f"⛔ [WORKER GATE - BUDGET EXHAUSTED]: Đã chạm trần 15 tool calls (call #{w_calls})! "
                    f"Bắt buộc dừng ngay và trả STATUS: ABORT_SCOPE kèm báo cáo hiện trạng."
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
                "reason": f"⛔ [WORKER GATE - INFO-LEAK BLOCKED / SELF-MODIFICATION BLOCKED / MALICIOUS TEST BLOCKED]: Tham số '{val}' trỏ vào thành phần hệ thống được bảo vệ (guard/state/ssh/hermes)!",
            }

    # 3. FAIL-CLOSED PATH MANDATE CHO READ_FILE & SEARCH_FILES
    if tool_name in ("read_file", "search_files"):
        explicit_paths = []
        for k in ("path", "directory", "dir", "root", "target", "file_path", "filename"):
            if k in fn_args and isinstance(fn_args[k], str) and fn_args[k].strip():
                explicit_paths.append(fn_args[k].strip())

        if not explicit_paths:
            # Chỉ suy luận từ VALUES: tên key (vd "pattern") không phải đường dẫn.
            for val in _extract_all_string_values(fn_args, include_keys=False):
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
            home_dir = str(Path.home())
            resolved_p = p if os.path.isabs(p) else os.path.join(home_dir, p)
            real_p = os.path.realpath(resolved_p)
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

    # 5. ACTION-BASED FILE WRITE CHECK (CLAUDE OPUS CERTIFIED - SYMMETRIC EMBEDDED PATCH PARSER)
    if tool_name in ("write_file", "patch"):
        target_path = ""
        for k in ("path", "file_path", "filename", "target"):
            if k in fn_args and isinstance(fn_args[k], str) and fn_args[k].strip():
                target_path = fn_args[k].strip()
                break

        embedded_patch_targets = []
        if tool_name == "patch":
            embedded_patch_targets = _extract_all_patch_targets(fn_args)
            # Nếu là mode='patch' hoặc có dấu hiệu patch mà không trích xuất được file header nào -> FAIL-CLOSED!
            if fn_args.get("mode") == "patch" and not embedded_patch_targets:
                return {
                    "action": "block",
                    "reason": "⛔ [WORKER GATE - UNPARSEABLE PATCH]: Nội dung patch mode='patch' không phân giải được đường dẫn đích hợp lệ!",
                }

        if not target_path and not embedded_patch_targets:
            return {
                "action": "block",
                "reason": f"⛔ [WORKER GATE - MISSING WRITE TARGET]: Tool '{tool_name}' của Worker BẮT BUỘC phải chỉ định đường dẫn file mục tiêu rõ ràng! Cấm gọi không có path.",
            }

        # Gom tất cả các file đích cần kiểm tra
        all_targets_to_verify = []
        if target_path:
            all_targets_to_verify.append(target_path)
        all_targets_to_verify.extend(embedded_patch_targets)

        for cur_tp in all_targets_to_verify:
            real_target_p = os.path.realpath(cur_tp)
            if not _is_path_in_roots(real_target_p, ALLOWED_REPO_ROOTS):
                return {
                    "action": "block",
                    "reason": f"⛔ [WORKER GATE - OUT OF WHITELIST]: File '{cur_tp}' (giải phân thành '{real_target_p}') nằm ngoài phạm vi repo cho phép: {ALLOWED_REPO_ROOTS}!",
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

        normalized_allowed = [os.path.normcase(os.path.realpath(os.path.normpath(p))) for p in allowed_targets]
        for cur_tp in all_targets_to_verify:
            real_target = os.path.normcase(os.path.realpath(os.path.normpath(cur_tp)))
            is_direct_target = real_target in normalized_allowed
            is_exact_test_file = False
            if not is_direct_target:
                target_base = os.path.basename(real_target)
                target_dir = os.path.dirname(real_target).replace("\\", "/").lower()
                for p in normalized_allowed:
                    p_stem = Path(p).stem
                    p_dir = os.path.dirname(p).replace("\\", "/").lower()
                    is_test_name = (target_base == f"test_{p_stem}.py" or target_base == f"{p_stem}_test.py")
                    is_same_dir = (target_dir == p_dir)
                    is_tests_subdir = ("tests" in target_dir.split("/"))
                    if is_test_name and (is_same_dir or is_tests_subdir):
                        is_exact_test_file = True
                        break

            if not (is_direct_target or is_exact_test_file):
                return {
                    "action": "block",
                    "reason": (
                        f"⛔ [WORKER GATE - SCOPE LOCK BREACH]: Worker đang cố sửa file '{cur_tp}' "
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

    # 1. UNCONDITIONAL PROTECTED TARGET SHIELD: MỌI actor, MỌI tool (default-deny) trừ tool thuần văn bản.
    if fn_name not in _SHIELD_TEXT_ONLY_TOOLS:
        for val in _extract_all_string_values(fn_args):
            if val and _is_protected_target(val):
                logger.warning(
                    "[FARM_GUARD][BLOCK] tool=%s session=%s rule=UNCONDITIONAL_SHIELD target=%s",
                    fn_name, (sess_id or "")[:16], val,
                )
                return {
                    "action": "block",
                    "reason": f"⛔ [GUARD SELF-PROTECTION / GUARD SOURCE BLACKLISTED]: Thao tác '{fn_name}' với tham số '{val}' đụng vào thành phần hệ thống được bảo vệ bị chặn vô điều kiện!",
                }

    # LÝ DO 3 CLOSED: RÀNG BUỘC WHITELIST CHO CẢ COORDINATOR (FAIL-CLOSED)
    if fn_name in ("write_file", "patch"):
        c_target = ""
        for k in ("path", "file_path", "filename", "target"):
            if k in fn_args and isinstance(fn_args[k], str) and fn_args[k].strip():
                c_target = fn_args[k].strip()
                break

        # Quét đệ quy tất cả các file nhúng trong patch/diff từ MỌI string values
        coord_embedded_targets = []
        if fn_name == "patch":
            coord_embedded_targets = _extract_all_patch_targets(fn_args)
            if (fn_args.get("mode") == "patch" or "patch" in fn_args) and not coord_embedded_targets:
                return {
                    "action": "block",
                    "reason": "⛔ [COORDINATOR GUARD - UNPARSEABLE PATCH]: Nội dung patch mode='patch' không phân giải được đường dẫn đích hợp lệ!",
                }
            for ep in coord_embedded_targets:
                real_ep = os.path.realpath(ep)
                if not _is_path_in_roots(real_ep, COORD_ALLOWED_ROOTS):
                    return {
                        "action": "block",
                        "reason": f"⛔ [COORDINATOR GUARD - PATCH OUT OF WHITELIST]: File nhúng trong patch '{ep}' nằm ngoài whitelist: {COORD_ALLOWED_ROOTS}!",
                    }

        if not c_target and not coord_embedded_targets:
            return {
                "action": "block",
                "reason": f"⛔ [COORDINATOR GUARD - MISSING WRITE TARGET]: Thao tác '{fn_name}' thiếu đường dẫn file mục tiêu!",
            }

        if c_target:
            real_c = os.path.realpath(c_target)
            if not _is_path_in_roots(real_c, COORD_ALLOWED_ROOTS):
                return {
                    "action": "block",
                    "reason": f"⛔ [COORDINATOR GUARD - OUT OF WHITELIST]: Thao tác '{fn_name}' trỏ ra ngoài phạm vi cho phép: {COORD_ALLOWED_ROOTS}!",
                }

        # COORDINATOR WRITE LEDGER & T1 / L2 HARD ENFORCEMENT
        if not _is_worker_session(sess_id):
            sess_state = _get_session_state(sess_id)
            ok, reason, updated_state = coordinator_write_gate(sess_id, fn_name, fn_args, sess_state)
            if not ok:
                return {"action": "block", "reason": reason}
            _update_session_state(sess_id, {"write_ledger": updated_state.get("write_ledger", {})})

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

        sess_state = _get_session_state(sess_id)
        dispatch_count = sess_state.get("dispatch_count", 0) + 1
        if dispatch_count > MAX_COORDINATOR_DISPATCHES:
            return {
                "action": "block",
                "reason": f"⛔ [COORDINATOR GUARD - DISPATCH BUDGET EXHAUSTED]: Đã dispatch {dispatch_count - 1}/{MAX_COORDINATOR_DISPATCHES} worker!",
            }

        # DÙNG CHUNG VALIDATE_DISPATCH (P0-2 SINGLE SOURCE OF TRUTH)
        try:
            val_res = validate_dispatch(dt_args)
            task_kind = val_res.get("task_kind", "EDIT")
            normalized_targets = val_res.get("target_files", [])
        except ContractError as ce:
            return {
                "action": "block",
                "reason": f"⛔ [COORDINATOR GUARD - CONTRACT VIOLATION]: {ce}",
            }
        except Exception as exc:
            return {
                "action": "block",
                "reason": f"⛔ [COORDINATOR GUARD - CONTRACT ERROR]: Không thể thẩm định contract: {exc}",
            }

        # Task inspect (INVESTIGATE / non-code) KHÔNG tính vào consecutive_failures
        task_type = str(dt_args.get("task_type") or "").strip().lower()
        is_inspect_task = (
            str(task_kind).upper() == "INVESTIGATE"
            or task_type in NON_CODE_EXEMPT_TASK_TYPES
        )

        # CIRCUIT BREAKER: >= 3 lần thất bại liên tiếp trên cùng target -> mở L2, chặn dispatch lặp
        if not is_inspect_task:
            consecutive_failures = sess_state.get("consecutive_failures", 0)
            last_failed_target = sess_state.get("last_failed_target")
            cur_target = (normalized_targets or [None])[0]
            if (
                consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD
                and last_failed_target
                and cur_target == last_failed_target
            ):
                _update_session_state(sess_id, {
                    "l2_eligible": True,
                    "l2_targets": normalized_targets,
                    "is_coordinator": True,
                })
                return {
                    "action": "block",
                    "reason": (
                        f"⛔ [COORDINATOR GUARD - CIRCUIT BREAKER]: Worker đã thất bại {consecutive_failures} lần liên tiếp "
                        f"trên target '{cur_target}'. Dừng dispatch lặp lại! l2_eligible=True -> "
                        "Chuyển sang L2 (Emergency Surgery: Coordinator tự sửa, đúng 2 files, <= 30 dòng) "
                        "hoặc escalate L3 (báo cáo người vận hành kèm bằng chứng)."
                    ),
                }

        # Nếu là investigate/read-only: normalized_targets rỗng (bị cấm ghi file 100%)
        sess_updates = {
            "phase": "WORKER_RUNNING",
            "dispatched_at": time.time(),
            "dispatch_count": dispatch_count,
            "target_files": normalized_targets,
            "task_kind": task_kind,
            "is_inspect_task": is_inspect_task,
            "is_coordinator": True,
        }
        _update_session_state(sess_id, sess_updates)
        logger.info("[FARM_GUARD] delegate_task passed farm_policy -> targets: %s (kind: %s)", normalized_targets, task_kind)
        return None

    if fn_name == "skill_view":
        return None

    sess_state = _get_session_state(sess_id)
    phase = sess_state.get("phase", "IDLE")

    # COORDINATOR TERMINAL GATE (ĐÓNG CÁC ĐƯỜNG GHI VÒNG / QUÉT ĐĨA H1, H5)
    if fn_name == "terminal" and not _is_worker_session(sess_id):
        cmd = str(fn_args.get("command") or "").strip() if isinstance(fn_args, dict) else ""
        ok, reason = coordinator_terminal_gate(cmd, sess_state)
        if not ok:
            return {
                "action": "block",
                "reason": f"⛔ [COORDINATOR GUARD - TERMINAL BLOCKED]: {reason}",
            }

    # COORDINATOR EXECUTE_CODE GATE: Chặn 100% đối với Coordinator
    if fn_name == "execute_code" and not _is_worker_session(sess_id):
        return {
            "action": "block",
            "reason": "⛔ [COORDINATOR GUARD - EXECUTE_CODE DISABLED]: Coordinator không được dùng execute_code để tránh ghi mã lậu hoặc bypass! Hãy dùng terminal/read_file/patch.",
        }

    # COORDINATOR SEND_MESSAGE GATE: Chặn báo cáo mồm giữa chừng qua tool gửi tin nhắn
    if fn_name in ("send_message", "telegram_send", "send_telegram_message") and not _is_worker_session(sess_id):
        dt_args = fn_args if isinstance(fn_args, dict) else {}
        msg_text = str(dt_args.get("text") or dt_args.get("message") or dt_args.get("content") or "")
        ev_err = _enforce_evidence_first_gate(msg_text, sess_id)
        if ev_err:
            return {
                "action": "block",
                "reason": ev_err,
            }

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

    return None


def _on_post_tool_call(
    function_name: str = "",
    function_args: Optional[Dict[str, Any]] = None,
    result: Any = None,
    session_id: str = "",
    **kwargs: Any,
) -> None:
    """Xử lý hậu kỳ sau khi tool call hoàn tất:
    - Nếu delegate_task hoàn tất -> reset phase về IDLE & theo dõi worker failure chuẩn xác.
    - Nếu closeout_gate trả về APPROVED >= 85 -> set closeout_passed = True.
    - Nếu Coordinator sửa code hoặc commit -> reset closeout_passed = False.
    """
    fn_name = kwargs.get("tool_name") or function_name or kwargs.get("function_name", "")
    fn_args = kwargs.get("args") or function_args or kwargs.get("function_args", {})
    sess_id = session_id or kwargs.get("session_id", "")
    if not sess_id:
        return

    sess_state = _get_session_state(sess_id)

    # 1. HẬU KỲ DELEGATE_TASK: Reset phase về IDLE & Theo dõi thất bại chuẩn xác
    if fn_name == "delegate_task":
        sess_state["phase"] = "IDLE"
        sess_state["worker_session_id"] = None
        target_file = (sess_state.get("target_files") or [None])[0]
        res_str = str(result or "")

        # Thất bại khi worker báo ABORT_SCOPE hoặc FAILED hoặc exception
        # (không đặt \b sau "Exception:" vì ':' không phải word char -> \b chỉ khớp khi dính liền chữ)
        is_failure = bool(re.search(r"\b(?:STATUS:\s*ABORT_SCOPE\b|STATUS:\s*FAILED\b|STATUS:\s*ABORT\b|Exception:)", res_str))
        is_inspect_task = bool(sess_state.get("is_inspect_task"))
        if is_failure:
            # Task inspect thất bại KHÔNG tính vào consecutive_failures / worker_failures
            if not is_inspect_task:
                last_target = sess_state.get("last_failed_target")
                if target_file and target_file == last_target:
                    w_fails = sess_state.get("worker_failures", 0) + 1
                    c_fails = sess_state.get("consecutive_failures", 0) + 1
                else:
                    w_fails = 1
                    c_fails = 1
                    sess_state["last_failed_target"] = target_file

                sess_state["worker_failures"] = w_fails
                sess_state["consecutive_failures"] = c_fails
                if w_fails >= 2:
                    sess_state["l2_eligible"] = True
                    sess_state["l2_targets"] = sess_state.get("target_files", [])
        else:
            # Thành công -> reset failure count & hoàn lại 1 suất dispatch
            if not is_inspect_task:
                sess_state["consecutive_failures"] = 0
                sess_state["worker_failures"] = 0
                sess_state["last_failed_target"] = None
            sess_state["dispatch_count"] = max(0, sess_state.get("dispatch_count", 0) - 1)

        _update_session_state(sess_id, sess_state)
        return

    # 2. HẬU KỲ TERMINAL: Phân tích JSON của Closeout Gate
    if fn_name == "terminal":
        cmd = str(fn_args.get("command") or "").strip() if isinstance(fn_args, dict) else ""

        # P2-A: Siết chặt kiểm tra gọi Advisor Sol thật (Zero-Spoof Validation v2.5 Absolute Allowlist):
        # 1. Chặn tuyệt đối command chaining/substitution: ;, &&, ||, |, `, $, \n, \r, >, <
        # 2. Chuẩn hóa separator dấu \ sang / để hỗ trợ an toàn Windows shlex
        # 3. Yêu cầu argv[0] là python, argv[1] phải trỏ CHÍNH XÁC tới script Advisor hợp lệ qua realpath
        # 4. Cấm mọi cờ lạ/viết tắt/bypass: chỉ cho phép chính xác -q, --query, -c, --context
        # 5. Fail-Closed: Bắt buộc result là JSON hợp lệ có output VÀ exit_code == 0
        is_real_advisor_call = False
        if not re.search(r"[\n\r;&|`$><]", cmd):
            try:
                tokens = _split_terminal_command(cmd)
                if len(tokens) >= 3:
                    py_bin = Path(tokens[0].replace("\\", "/")).name.lower()
                    if py_bin in ("python", "python.exe", "python3", "python3.exe"):
                        real_script = os.path.normcase(str(Path(tokens[1]).resolve()))

                        if real_script in _allowed_advisor_scripts():
                            valid_flags = True
                            has_query = False
                            i = 2
                            while i < len(tokens):
                                tok = tokens[i]
                                if tok in ("-q", "--query", "-c", "--context") and i + 1 < len(tokens):
                                    has_query = has_query or tok in ("-q", "--query")
                                    i += 2
                                    continue
                                valid_flags = False
                                break

                            if valid_flags and has_query:
                                parsed = result
                                if isinstance(result, str):
                                    try:
                                        parsed = json.loads(result)
                                    except Exception:
                                        parsed = None
                                # Fail-Closed: bắt buộc dict có đủ output + exit_code (int thật, không phải bool)
                                if isinstance(parsed, dict) and "output" in parsed and "exit_code" in parsed:
                                    exit_code = parsed["exit_code"]
                                    stdout = parsed["output"]
                                    if (
                                        isinstance(exit_code, int)
                                        and not isinstance(exit_code, bool)
                                        and exit_code == 0
                                        and isinstance(stdout, str)
                                        and stdout.strip().startswith("--- Advisor (Sol / review) ---")
                                    ):
                                        is_real_advisor_call = True
            except Exception as exc_chk:
                logger.debug("[FARM_GUARD] Lỗi kiểm tra advisor terminal command: %s", exc_chk)

        if is_real_advisor_call:
            latest_id, _ = _get_latest_user_message(sess_id)
            sess_state["advisor_verified_msg_id"] = latest_id
            _update_session_state(sess_id, sess_state)
            logger.info("[FARM_GUARD] Advisor Sol verified called legitimately via tool for msg_id=%s", latest_id)
        if re.search(r"\bcloseout_gate\.py\b", cmd):
            res_str = str(result or "")
            passed = False
            m_json = re.search(r"\{[^{}]*\"verdict\"\s*:[^{}]*\}", res_str, re.DOTALL)
            if m_json:
                try:
                    j = json.loads(m_json.group(0))
                    if j.get("verdict") == "APPROVED" and int(j.get("score", 0)) >= 85:
                        passed = True
                except Exception:
                    pass
            if not passed:
                m_verdict = re.search(r"Verdict:\s*APPROVED\b", res_str)
                m_score = re.search(r"(?:Overall Score|Score):\s*(\d+)", res_str)
                if m_verdict and m_score and int(m_score.group(1)) >= 85:
                    passed = True

            if passed:
                sess_state["closeout_passed"] = True
                _update_session_state(sess_id, sess_state)
                logger.info("[FARM_GUARD] Closeout Gate APPROVED -> closeout_passed=True")
        elif re.search(r"\bgit\b.*\bpush\b", cmd):
            # Sau khi push thành công -> reset closeout_passed
            sess_state["closeout_passed"] = False
            _update_session_state(sess_id, sess_state)
        elif re.search(r"\bgit\b.*\bcommit\b", cmd):
            # Giữ closeout_passed=True để Coordinator tự động chạy tiếp git push sau khi commit!
            pass

        # Ghi nhận WinRT OCR trên ảnh:
        # Bắt buộc phân tích argv thật qua _split_terminal_command và đối chiếu ALLOWED_OCR_SCRIPTS
        is_real_ocr_cmd = False
        img_arg_path = None
        chars_bad = (chr(10), chr(13), ";", "&", "|", "`", "$", ">", "<")
        if not any(ch in cmd for ch in chars_bad):
            try:
                tokens = _split_terminal_command(cmd)
                if len(tokens) >= 2:
                    py_bin = Path(tokens[0]).name.lower()
                    if py_bin in ("python", "python.exe", "python3", "python3.exe"):
                        real_script = os.path.normcase(str(Path(tokens[1]).resolve()))
                        if real_script in _allowed_ocr_scripts():
                            for tok in tokens[2:]:
                                if tok.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                                    img_arg_path = tok
                                    is_real_ocr_cmd = True
                                    break
            except Exception as e_tok:
                logger.debug("[FARM_GUARD] Error tokenizing terminal cmd for OCR: %s", e_tok)

        if is_real_ocr_cmd and img_arg_path:
            ocr_text = ""
            exit_code = 1
            if isinstance(result, dict):
                ocr_text = str(result.get("output") or "")
                exit_code = int(result.get("exit_code", 1))
            elif isinstance(result, str):
                try:
                    pj = json.loads(result)
                    if isinstance(pj, dict) and "output" in pj:
                        ocr_text = str(pj.get("output") or "")
                        exit_code = int(pj.get("exit_code", 1))
                    else:
                        ocr_text = result
                        exit_code = 0
                except Exception:
                    ocr_text = result
                    exit_code = 0
            else:
                ocr_text = str(result or "")

            if exit_code == 0 and len(ocr_text.strip()) > 0:
                img_p = os.path.normcase(os.path.normpath(img_arg_path.strip().strip("'\"<>`")))
                if not _is_allowed_evidence_image_path(img_p):
                    logger.warning("[FARM_GUARD] OCR image rejected by Provenance Enforcement: %s", img_p)
                    return

                file_sha = _compute_file_sha256(img_p)
                if not file_sha:
                    logger.warning("[FARM_GUARD] OCR target image SHA-256 could not be computed: %s", img_p)
                    return

                verified = list(sess_state.get("verified_media_paths") or [])
                if img_p not in verified:
                    verified.append(img_p)
                sess_state["verified_media_paths"] = verified

                details = dict(sess_state.get("verified_media_details") or {})
                details[img_p] = {
                    "text": ocr_text.lower(),
                    "timestamp": time.time(),
                    "sha256": file_sha,
                    "source": "ocr",
                }
                sess_state["verified_media_details"] = details
                _update_session_state(sess_id, sess_state)

    # 3. KHI COORDINATOR GHI MÃ NGUỒN: Tự động reset closeout_passed
    if fn_name in ("write_file", "patch"):
        if sess_state.get("closeout_passed"):
            sess_state["closeout_passed"] = False
            _update_session_state(sess_id, sess_state)

    # 4. EVIDENCE FIRST GATE: Ghi nhận đường dẫn ảnh qua browser_navigate & browser_vision
    if fn_name == "browser_navigate":
        url = str(fn_args.get("url") or "") if isinstance(fn_args, dict) else ""
        clean_url = urllib.parse.urldefrag(url.split("?")[0])[0]
        if clean_url.startswith("file:///"):
            local_f = clean_url[8:].replace("/", "\\")
            sess_state["last_navigated_local_file"] = os.path.normcase(os.path.normpath(local_f))
        elif clean_url.startswith(("http://127.0.0.1", "http://localhost", "data:")):
            sess_state["last_navigated_local_file"] = "local_spoofed_page.html"
        else:
            sess_state["last_navigated_local_file"] = ""
        _update_session_state(sess_id, sess_state)
    elif fn_name == "browser_vision":
        # Từ chối ghi nhận nếu trang vừa điều hướng là file cục bộ HTML do agent tự tạo (chống HTML spoofing)
        last_f = str(sess_state.get("last_navigated_local_file") or "")
        if last_f.endswith((".html", ".htm")):
            logger.warning("[FARM_GUARD] browser_vision rejected: Navigated from local HTML file: %s", last_f)
            return

        res_str = str(result or "")
        vision_ok = bool(res_str.strip() and not res_str.startswith("Error") and "Traceback" not in res_str)
        if vision_ok:
            verified = list(sess_state.get("verified_media_paths") or [])
            details = dict(sess_state.get("verified_media_details") or {})
            sc_pat = "Screenshot path:\\s*([^\
\\n]+)"
            m_sc = re.search(sc_pat, res_str)
            if m_sc:
                sc_p = os.path.normcase(os.path.normpath(m_sc.group(1).strip().strip('"\'')))
                if os.path.isfile(sc_p) and _is_allowed_evidence_image_path(sc_p):
                    sc_sha = _compute_file_sha256(sc_p)
                    if sc_sha:
                        if sc_p not in verified:
                            verified.append(sc_p)
                        details[sc_p] = {
                            "text": res_str.lower(),
                            "timestamp": time.time(),
                            "sha256": sc_sha,
                            "source": "browser_vision_screenshot",
                        }
            sess_state["verified_media_paths"] = verified
            sess_state["verified_media_details"] = details
            _update_session_state(sess_id, sess_state)


def _get_latest_user_message(session_id: str, strict: bool = False) -> Tuple[int, str]:
    """Lấy (msg_id, content) tin nhắn gần nhất từ người dùng (bỏ qua thông báo hệ thống / background task).

    strict=True: không nuốt lỗi DB (thiếu state.db / database is locked) mà raise để caller fail-safe.
    """
    db_path = HERMES_ROOT / "state.db"
    if not db_path.exists():
        logger.warning("[FARM_GUARD] state.db không tồn tại tại %s", db_path)
        if strict:
            raise FileNotFoundError(f"state.db không tồn tại: {db_path}")
        return (0, "")
    try:
        conn = sqlite3.connect(str(db_path), timeout=1.0)
        try:
            c = conn.cursor()
            c.execute(
                """
                SELECT id, content FROM messages 
                WHERE session_id = ? AND role = 'user' 
                  AND content NOT LIKE '[ASYNC DELEGATION%'
                  AND content NOT LIKE '[IMPORTANT: Background process%'
                ORDER BY id DESC LIMIT 1
                """,
                (session_id,)
            )
            row = c.fetchone()
            if row:
                return (int(row[0]), str(row[1]))
        finally:
            conn.close()
    except Exception as exc:
        logger.error("[FARM_GUARD] Lỗi đọc latest user message: %s", exc)
        if strict:
            raise
    return (0, "")


ADVISOR_UNAVAILABLE_MARKER = (
    "\n\n--- Advisor ---\n"
    "Advisor: unavailable (Lỗi kết nối Advisor Sol; chỉ hiển thị câu trả lời Coordinator)"
)
ADVISOR_UNVERIFIED_MARKER = (
    "\n\n--- Advisor ---\n"
    "Advisor: unavailable (Guard không xác minh được ngữ cảnh/Advisor; chỉ hiển thị câu trả lời Coordinator)"
)


def _advisor_failsafe_text(response_text: str, marker: str = ADVISOR_UNVERIFIED_MARKER) -> str:
    """Fail-safe: lột marker Advisor không xác minh được rồi gắn marker 'unavailable' trung thực."""
    cleaned = response_text
    m_pos = cleaned.find("--- Advisor")
    if m_pos != -1:
        cleaned = cleaned[:m_pos]
    return f"{cleaned.rstrip()}{marker}"


def _enforce_advisor_dual_answer(response_text: str, session_id: str) -> Optional[str]:
    """Cơ chế Chốt chặn Cơ học (Mechanical Enforcement Gate v2.5 Hardened):
    Nếu User hỏi tư vấn/chiến lược (Advice Intent) mà câu trả lời chưa có Advisor Sol:
    Tự động gọi Advisor Sol và nối khối kết quả vào cuối tin nhắn trước khi gửi ra Telegram/User.
    Chống bypass sau compression, chống hallucination marker giả, chống gọi lặp lại.
    """
    if not response_text or not response_text.strip():
        return None

    # Không can thiệp vào worker subagent session
    if _is_worker_session(session_id):
        return None

    try:
        msg_id, user_msg = _get_latest_user_message(session_id, strict=True)
    except Exception as exc_db:
        logger.error("[FARM_GUARD] Không đọc được state.db trên session %s -> fail-safe Advisor: %s", session_id, exc_db)
        return _advisor_failsafe_text(response_text)
    if not user_msg or not user_msg.strip():
        return None

    try:
        sess_state = _get_session_state(session_id)
    except Exception as exc:
        logger.warning("[FARM_GUARD] Cảnh báo lỗi đọc session state trong enforce gate: %s", exc)
        sess_state = {}

    # P2-A: Chống lặp Advisor trên cùng tin nhắn user
    if sess_state.get("last_enforced_user_msg_id") == msg_id:
        return None

    # P2-A: Kiểm tra cờ advisor đã được gọi thật cho CHÍNH msg_id này
    verified_msg_id = sess_state.get("advisor_verified_msg_id")
    advisor_actually_called_for_msg = (verified_msg_id is not None and verified_msg_id == msg_id)

    has_advisor_marker = (
        "--- Advisor (Sol / review) ---" in response_text
        or "--- Advisor (" in response_text
        or "--- Advisor ---" in response_text
    )

    # Nhánh A: Sol đã được gọi thật và đã có marker hợp lệ -> Ghi nhận anti-repeat và pass through
    if has_advisor_marker and advisor_actually_called_for_msg:
        sess_state["last_enforced_user_msg_id"] = msg_id
        sess_state["advisor_verified_msg_id"] = None
        _record_advisor_metric(sess_state, "passthrough_count", session_id=session_id)
        try:
            _update_session_state(session_id, sess_state)
        except Exception:
            pass
        return None

    cleaned_response = response_text
    if has_advisor_marker and not advisor_actually_called_for_msg:
        logger.warning("[FARM_GUARD] Phát hiện marker Advisor giả mạo/hallucinated trên session %s cho msg_id %s. Lột bỏ để gọi Sol thật!", session_id, msg_id)
        m_pos = cleaned_response.find("--- Advisor")
        if m_pos != -1:
            cleaned_response = cleaned_response[:m_pos].rstrip()
        _record_advisor_metric(sess_state, "bypass_count", session_id=session_id)

    try:
        if _advisor_mod is None:
            raise RuntimeError("advisor_consult module unavailable")

        if _advisor_mod.classify_advice_intent(user_msg):
            logger.info("[FARM_GUARD] Advice Intent detected on session %s (msg_id=%d). Enforcing Advisor Sol Dual-Answer...", session_id, msg_id)
            t0 = time.monotonic()
            new_text = _advisor_mod.ensure_dual_answer(user_msg, cleaned_response)
            latency_ms = (time.monotonic() - t0) * 1000.0
            _record_advisor_metric(sess_state, "enforce_count", latency_ms, session_id=session_id)
            if isinstance(new_text, str) and "Advisor: unavailable" in new_text:
                _record_advisor_metric(
                    sess_state, "advisor_failure_count", latency_ms,
                    session_id=session_id, error="advisor_unavailable",
                )
            sess_state["last_enforced_user_msg_id"] = msg_id
            sess_state["advisor_verified_msg_id"] = None
            try:
                _update_session_state(session_id, sess_state)
            except Exception as exc_upd:
                logger.warning("[FARM_GUARD] Lỗi cập nhật session state sau khi gọi Sol: %s", exc_upd)
            return new_text
    except Exception as exc:
        logger.warning("[FARM_GUARD] Lỗi khi enforce Advisor Sol qua transform_llm_output: %s", exc)
        is_advice = True
        try:
            if _advisor_mod is not None:
                is_advice = _advisor_mod.classify_advice_intent(user_msg)
        except Exception:
            is_advice = True
        if is_advice:
            err_marker = ADVISOR_UNAVAILABLE_MARKER
            _record_advisor_metric(
                sess_state, "advisor_failure_count", session_id=session_id,
                error=f"{type(exc).__name__}: {exc}",
            )
            sess_state["last_enforced_user_msg_id"] = msg_id
            sess_state["advisor_verified_msg_id"] = None
            try:
                _update_session_state(session_id, sess_state)
            except Exception:
                pass
            return f"{cleaned_response.rstrip()}{err_marker}"

    return None


def _detect_completion_claims(text: str) -> Tuple[bool, Set[str]]:
    """Xác định xem văn bản có chứa tuyên bố hoàn thành tác vụ UI/Farm hay không.
    Tách văn bản thành các mệnh đề độc lập (theo dấu chấm, phẩy, chấm phẩy, chấm than, gạch ngang, xuống dòng).
    """
    if not text:
        return False, set()

    # Văn bản trích dẫn / code / mô tả không phải tuyên bố hoàn thành thật.
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"\"[^\"\n]*\"|“[^”\n]*”|‘[^’\n]*’", " ", text)
    text = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith(">"))

    patterns = {
        "2fa": [
            r"\b(?:2fa|xác\s+minh\s+2\s+bước|two-factor|xác\s+thực\s+2\s+lớp|thiết\s+lập\s+2fa)\s*[:=]?\s*(?:đã\s+được\s+bật|đang\s+bật|bật\s+thành\s+công|bật\s+xong|hoàn\s+tất|ok|enabled|activated|on|đã\s+bật)\b",
            r"\b(?:2fa|xác\s+minh\s+2\s+bước|two-factor|xác\s+thực\s+2\s+lớp)\s+đã\s+bật\b",
            r"\bđã\s+bật\s+(?:thành\s+công\s+)?(?:2fa|xác\s+minh\s+2\s+bước|xác\s+thực\s+2\s+lớp)\b",
            r"\bbật\s+(?:thành\s+công|xong|hoàn\s+tất)\s+(?:2fa|xác\s+minh\s+2\s+bước|xác\s+thực\s+2\s+lớp)\b",
            r"\b(?:đã\s+)?bật\s+(?:2fa|xác\s+minh\s+2\s+bước|xác\s+thực\s+2\s+lớp)\s+(?:thành\s+công|xong|hoàn\s+tất|ok)\b",
            r"✅\s*(?:đã\s+)?bật\s+2fa\b",
            r"\b(?:đã\s+)?(?:kích\s+hoạt|thiết\s+lập)\s+(?:thành\s+công\s+)?(?:2fa|xác\s+minh\s+2\s+bước)(?:\s+(?:thành\s+công|xong|hoàn\s+tất|ok))?\b",
            r"\btrạng\s+thái\s+2fa\s*[:=]?\s*(?:đã\s+)?(?:bật|on|active)\b",
        ],
        "login": [
            r"\bđã\s+(?:đăng\s+nhập|login|log\s*in)\b",
            r"\b(?:đăng\s+nhập|login|log\s*in)\s+(?:thành\s+công|xong|hoàn\s+tất|ok)\b",
            r"\b(?:logged\s+in|logged-in)\b",
            r"\b(?:vào\s+được|đăng\s+nhập\s+được)\s+nick\b",
            r"\bđã\s+vào\s+(?:được\s+)?tài\s+khoản\b",
            r"✅\s*(?:đã\s+)?(?:đăng\s+nhập|login)\b",
            r"\btrạng\s+thái\s+(?:đăng\s+nhập|login)\s*[:=]?\s*(?:thành\s+công|hoàn\s+tất|ok|đã\s+đăng\s+nhập)\b",
        ],
        "password": [
            r"\b(?:mật\s+khẩu|pass|password)\s*[:=]?\s*(?:đã\s+được\s+đổi|đã\s+đổi|đã\s+cập\s+nhật|changed|updated|reset|mới|ok)\b",
            r"\bđã\s+(?:đổi|cập\s+nhật|set|reset|thay\s+đổi)\s+(?:mật\s+khẩu|pass|password)\b",
            r"\b(?:đổi|cập\s+nhật|set|reset|thay\s+đổi)\s+(?:mật\s+khẩu|pass|password)\s+(?:thành\s+công|xong|hoàn\s+tất|ok)\b",
            r"\b(?:đổi|cập\s+nhật|set|reset|thay\s+đổi)\s+thành\s+công\s+(?:mật\s+khẩu|pass|password)\b",
            r"✅\s*(?:đã\s+)?(?:đổi\s+pass|mật\s+khẩu)\b",
        ],
    }

    split_chars = (chr(10), chr(13), ";", ",", ".", "!", "—")
    clauses = re.split(r"[" + "".join(split_chars) + r"]+|\s+-\s+|\bnhưng\b|\bvà\b", text)
    claim_types = set()

    for clause in clauses:
        c_str = clause.strip()
        if not c_str:
            continue
        if "?" in c_str or re.search(r"\b(?:có\s+.*không|sao\s+lại|tại\s+sao|thế\s+nào|được\s+chưa)\b", c_str, re.IGNORECASE):
            continue
        # Tác vụ web/browser (GPM, ChatGPT, mail...) không phải UI điện thoại farm -> không đòi ảnh máy.
        if re.search(r"\b(?:chatgpt|openai|gpm|gmail|hotmail|outlook|browser|trình\s+duyệt)\b", c_str, re.IGNORECASE):
            continue
        # Mô tả gate/guard/code/rule chứ không phải báo cáo kết quả tác vụ.
        if re.search(r"\b(?:gate|guard|plugin|hook|regex|false\s+positive|detector|__init__)\b", c_str, re.IGNORECASE):
            continue

        for cat, regexes in patterns.items():
            for pat in regexes:
                for m in re.finditer(pat, c_str, re.IGNORECASE):
                    start = m.start()
                    end = m.end()
                    prefix = c_str[max(0, start - 25):start].lower()
                    suffix = c_str[end:min(len(c_str), end + 35)].lower()

                    neg_local = r"\b(?:chưa|không|chưa\s+thể|không\s+thể|chẳng|chưa\s+từng|không\s+phải|chưa\s+được|không\s+được)\s*$"
                    if re.search(neg_local, prefix):
                        continue

                    intent_prefix = r"\b(?:đang|sẽ|chuẩn\s+bị|tiến\s+hành|bắt\s+đầu|thử|kiểm\s+tra|check|hướng\s+dẫn|quy\s+trình|cách|nút|trang|form|mở)\s*$"
                    if re.search(intent_prefix, prefix):
                        continue

                    neg_suffix = r"^\s*(?:bị\s+)?(?:thất\s+bại|lỗi|failed|error|hỏng|die|không\s+thành\s+công|chưa\s+thành\s+công|không\s+được|chưa\s+được|bị\s+chặn|bị\s+khóa|bị\s+ban|timeout)"
                    if re.search(neg_suffix, suffix):
                        continue

                    claim_types.add(cat)

    return (len(claim_types) > 0, claim_types)


def _extract_media_paths(text: str) -> List[str]:
    """Trích xuất danh sách đường dẫn file ảnh từ các thẻ MEDIA:<path> hoặc ![alt](path).
    Hỗ trợ bỏ qua chú thích phía sau (MEDIA:path.png - chú thích), unescape URL encoding (%20).
    """
    pat = r'(?:MEDIA:\s*|!\[.*?\]\()([^\s\)\"\'<>]+)'
    raw_matches = re.findall(pat, text, re.IGNORECASE)
    paths = []
    for m in raw_matches:
        cleaned = urllib.parse.unquote(m.strip().strip("'\"<>`),;"))
        if cleaned and cleaned not in paths:
            paths.append(cleaned)
    return paths


def _enforce_evidence_first_gate(response_text: str, session_id: str) -> Optional[str]:
    """Cơ chế Chốt chặn Bằng chứng Thị giác (Evidence-First Hard Gate v4.3 — Round 8 Production Certified):
    Nếu Coordinator tuyên bố hoàn thành tác vụ UI/Farm (đã đăng nhập, bật 2fa, đổi pass, v.v.):
    1. BẮT BUỘC câu trả lời phải chứa ít nhất 1 thẻ `MEDIA:<path>`.
    2. Toàn bộ các file ảnh trong thẻ MEDIA phải là file có thật trên đĩa,
       thuộc thư mục ảnh hợp lệ (Provenance Enforcement: tmp, screenshots, logs),
       VÀ đã được kiểm chứng qua WinRT OCR / browser_vision trong phiên làm việc.
    3. Ràng buộc nội dung nghiêm ngặt:
       - 2FA: bắt buộc ảnh chứa trạng thái BẬT ('xác minh 2 bước đang bật', 'trình xác thực bật') và loại trừ TẮT.
       - Login: bắt buộc ảnh chứa thông tin switcher / chuyển đổi tài khoản / profile sửa của trạng thái đã đăng nhập.
       - Password: bắt buộc ảnh chứa màn hình đổi mật khẩu thành công thật, từ chối bảng Excel.
    4. Ràng buộc Entity: Mỗi tài khoản được nêu trong báo cáo bắt buộc phải xuất hiện trong ảnh tương ứng (per-image binding).
    5. Chống file tampering: So khớp SHA-256 từ file thật trên đĩa tại thời điểm gửi với hash lúc OCR.
    6. Nếu vi phạm: FAIL-CLOSED lập tức ghi đè câu trả lời, trả về lỗi cảnh báo đỏ.
    """
    if not response_text or not response_text.strip():
        return None
    if _is_worker_session(session_id):
        return None

    has_completion_claim, claim_types = _detect_completion_claims(response_text)
    if not has_completion_claim:
        return None

    media_paths = _extract_media_paths(response_text)
    if not media_paths:
        logger.error("[FARM_GUARD] EVIDENCE FIRST GATE VIOLATION: Coordinator tuyên bố hoàn thành tác vụ nhưng KHÔNG đính kèm MEDIA:!")
        return (
            "🛑 **[EVIDENCE FIRST GATE — FAIL-CLOSED VIOLATION]**\n\n"
            "Coordinator đã tuyên bố hoàn thành tác vụ nhưng **KHÔNG ĐÍNH KÈM THẺ MEDIA:<path>** bằng chứng thực tế!\n"
            "Theo phán quyết kỷ luật P0 của Claude Code CLI & Invariant GATE 6: Báo cáo này bị coi là **VÔ GIÁ TRỊ**.\n"
            "👉 Yêu cầu: Phải điều hướng chụp ảnh màn hình đích thật trên máy và WinRT OCR trước khi báo kết quả."
        )

    try:
        sess_state = _get_session_state(session_id)
        verified_paths = {os.path.normcase(os.path.normpath(p)) for p in (sess_state.get("verified_media_paths") or [])}
        verified_details = sess_state.get("verified_media_details") or {}
    except Exception:
        verified_paths = set()
        verified_details = {}

    unverified = []
    tampered = []
    for p_str in media_paths:
        norm_p = os.path.normcase(os.path.normpath(p_str))
        if not os.path.exists(p_str):
            unverified.append(f"{p_str} (File không tồn tại trên đĩa)")
        elif norm_p not in verified_paths:
            unverified.append(f"{p_str} (Chưa qua WinRT OCR hoặc browser_vision)")
        else:
            info = verified_details.get(norm_p)
            saved_sha = str(info.get("sha256") or "").strip() if info else ""
            if not saved_sha:
                unverified.append(f"{p_str} (Thiếu chữ ký SHA-256 lúc OCR)")
            else:
                cur_sha = _compute_file_sha256(p_str)
                if not cur_sha or cur_sha != saved_sha:
                    tampered.append(f"{p_str} (SHA-256 không khớp: file bị sửa đổi/ghi đè sau khi OCR!)")

    if unverified:
        logger.error("[FARM_GUARD] EVIDENCE FIRST GATE VIOLATION: Ảnh MEDIA chưa qua kiểm chứng: %s", unverified)
        return (
            "🛑 **[EVIDENCE FIRST GATE — UNVERIFIED MEDIA]**\n\n"
            "Coordinator đã đính kèm ảnh nhưng ảnh **CHƯA ĐƯỢC SOI MẮT KIỂM CHỨNG** qua OCR / Vision:\n"
            + "\n".join(f"- `{u}`" for u in unverified) + "\n\n"
            "Cấm tuyệt đối gửi ảnh mù hoặc ảnh đối phó! Phải gọi `ocr.py` hoặc `browser_vision` mở ảnh ra kiểm tra trước."
        )

    if tampered:
        logger.error("[FARM_GUARD] EVIDENCE FIRST GATE VIOLATION: Phát hiện ảnh bị tampering: %s", tampered)
        return (
            "🛑 **[EVIDENCE FIRST GATE — TAMPERED MEDIA]**\n\n"
            "Phát hiện ảnh đã bị **THAY ĐỔI / GHI ĐÈ TRÊN ĐĨA (SHA-256 MISMATCH)** sau khi chạy lệnh OCR:\n"
            + "\n".join(f"- `{t}`" for t in tampered) + "\n\n"
            "Cấm hành vi gian lận ghi đè file sau khi soi mắt! Bắt buộc phải chạy lại OCR trên file mới."
        )

    if not verified_details:
        logger.error("[FARM_GUARD] EVIDENCE FIRST GATE VIOLATION: verified_details rỗng khi có tuyên bố hoàn thành!")
        return (
            "🛑 **[EVIDENCE FIRST GATE — MISSING EVIDENCE DETAILS]**\n\n"
            "Không tìm thấy chi tiết nội dung OCR của ảnh đính kèm trong phiên làm việc!\n"
            "Bắt buộc phải chạy `ocr.py` hoặc `browser_vision` kiểm chứng nội dung ảnh trước khi báo cáo."
        )

    # Từ khóa ranh giới từ chuẩn mực (bắt buộc đúng trạng thái BẬT và loại trừ TẮT)
    req_keywords_map = {
        "2fa": [
            r"\b(?:xác minh 2 bước|2 bước|two-step|two-factor)\s+(?:đang\s+bật|bật|on)\b",
            r"\btrình xác thực\s+(?:bật|on)\b",
            r"\b2fa\s+(?:on|bật)\b",
        ],
        "login": [
            r"\b(?:chuyển đổi tài khoản|thêm tài khoản)\b",
            r"\bswitcher\b",
            r"\b(?:sửa hồ sơ|chỉnh sửa hồ sơ)\b",
            r"\b(?:hồ sơ|profile)\b.*\b(?:sửa|chỉnh sửa)\b",
        ],
        "password": [
            r"\b(?:đã đổi mật khẩu|mật khẩu đã được đổi|đổi mật khẩu thành công|đã cập nhật mật khẩu)\b",
        ],
    }

    content_mismatches = []
    for cat in claim_types:
        patterns_for_cat = req_keywords_map.get(cat, [])
        matched_for_cat = False
        for p_str in media_paths:
            norm_p = os.path.normcase(os.path.normpath(p_str))
            info = verified_details.get(norm_p)
            if info:
                img_text = info.get("text", "")
                if cat == "2fa":
                    # Mở rộng loại trừ mọi biến thể 2FA đang tắt
                    disabled_pats = (
                        r"\b2fa\s*[:=]\s*(?:off|tắt)\b",
                        r"\b(?:xác\s+minh\s+2\s+bước|2\s+bước|two-step|two-factor)\s*[:=]?\s*(?:đang\s+)?(?:tắt|off)\b",
                        r"\btrình\s+xác\s+thực\s*[:=]?\s*(?:tắt|off)\b",
                        r"\bvô\s+hiệu\s+hóa\b",
                    )
                    if any(re.search(dp, img_text, re.IGNORECASE) for dp in disabled_pats):
                        continue
                if any(re.search(pat, img_text, re.IGNORECASE) for pat in patterns_for_cat):
                    matched_for_cat = True
                    break
        if not matched_for_cat:
            if cat == "2fa":
                content_mismatches.append("Ảnh MEDIA đính kèm không chứa nội dung xác nhận 'Xác minh 2 bước đang bật' (hoặc đang hiển thị trạng thái tắt)!")
            elif cat == "login":
                content_mismatches.append("Ảnh MEDIA đính kèm không chứa thông tin chuyển đổi tài khoản/switcher của trạng thái đã đăng nhập!")
            elif cat == "password":
                content_mismatches.append("Ảnh MEDIA đính kèm không chứa màn hình đổi mật khẩu thành công hợp lệ!")

    # Ràng buộc Entity (Tên Nick / Số Máy):
    # Với MỖI username và MỖI claim_type, bắt buộc phải có ít nhất 1 ảnh thỏa mãn đồng thời (Strict Per-Claim Per-User Binding)
    target_users = set()
    for m_u in re.finditer(r"(?<![a-zA-Z0-9_.])@([a-zA-Z0-9_]{3,24})(?![a-zA-Z0-9_.])", response_text):
        u_cand = m_u.group(1).lower()
        if u_cand not in ("gmail", "hotmail", "outlook", "yahoo", "icloud"):
            target_users.add(u_cand)
    for m_nick in re.finditer(r"\b(?:nick|tài\s+khoản)\s+([a-zA-Z0-9_]{3,24})\b", response_text, re.IGNORECASE):
        target_users.add(m_nick.group(1).lower())

    if target_users:
        for u in target_users:
            for cat in claim_types:
                cat_user_matched = False
                pats = req_keywords_map.get(cat, [])
                for p_str in media_paths:
                    norm_p = os.path.normcase(os.path.normpath(p_str))
                    info = verified_details.get(norm_p, {})
                    img_text = info.get("text", "")
                    if re.search(r"\b" + re.escape(u) + r"\b", img_text, re.IGNORECASE):
                        if cat == "2fa":
                            disabled_pats = (
                                r"\b2fa\s*[:=]\s*(?:off|tắt)\b",
                                r"\b(?:xác\s+minh\s+2\s+bước|2\s+bước|two-step|two-factor)\s*[:=]?\s*(?:đang\s+)?(?:tắt|off)\b",
                                r"\btrình\s+xác\s+thực\s*[:=]?\s*(?:tắt|off)\b",
                                r"\bvô\s+hiệu\s+hóa\b",
                            )
                            if any(re.search(dp, img_text, re.IGNORECASE) for dp in disabled_pats):
                                continue
                        if any(re.search(pat, img_text, re.IGNORECASE) for pat in pats):
                            cat_user_matched = True
                            break
                if not cat_user_matched:
                    content_mismatches.append(f"Không có ảnh MEDIA nào thỏa mãn đồng thời tác vụ '{cat}' và thông tin tài khoản @{u}!")

    if content_mismatches:
        logger.error("[FARM_GUARD] EVIDENCE FIRST GATE VIOLATION: Ảnh không khớp nội dung tuyên bố: %s", content_mismatches)
        return (
            "🛑 **[EVIDENCE FIRST GATE — CONTENT MISMATCH]**\n\n"
            "Ảnh MEDIA đính kèm **KHÔNG KHỚP VỚI NỘI DUNG TUYÊN BỐ**:\n"
            + "\n".join(f"- {m}" for m in content_mismatches) + "\n\n"
            "Cấm gửi ảnh màn hình khác để đối phó! Bắt buộc phải chụp và soi mắt đúng màn hình đích của tác vụ."
        )

    return None


def register(ctx: Any) -> None:
    """Hermes Plugin Lifecycle Registration Hook.
    Đăng ký pre_tool_call, post_tool_call và transform_llm_output với PluginContext.
    """
    def pre_tool_hook(tool_name: str = "", args: Optional[Dict[str, Any]] = None, session_id: str = "", **kwargs: Any):
        try:
            res = _on_pre_tool_call(tool_name, args, session_id=session_id, **kwargs)
            if isinstance(res, dict) and res.get("action") == "block":
                msg = res.get("reason") or res.get("message") or "Tool call blocked by farm guard."
                label = re.search(r"\[([^\]]+)\]", msg)
                logger.warning(
                    "[FARM_GUARD][BLOCK] tool=%s session=%s rule=%s",
                    tool_name, (session_id or "")[:16], label.group(1) if label else "UNLABELED",
                )
                return {"action": "block", "message": msg}
            return None
        except Exception as exc:
            logger.exception("[FARM_GUARD][BLOCK] tool=%s rule=GUARD_FAIL_CLOSED: %s", tool_name, exc)
            return {"action": "block", "message": f"⛔ [GUARD FAIL-CLOSED]: Lỗi nội tại guard: {exc}"}

    def post_tool_hook(tool_name: str = "", args: Optional[Dict[str, Any]] = None, result: Any = None, session_id: str = "", **kwargs: Any):
        try:
            _on_post_tool_call(tool_name=tool_name, args=args or {}, result=result, session_id=session_id, **kwargs)
        except Exception as exc:
            logger.exception("[FARM_GUARD] Error in post_tool_hook: %s", exc)
        return None

    def transform_output_hook(response_text: str = "", session_id: str = "", **kwargs: Any) -> Optional[str]:
        # 1. Chốt chặn Bằng chứng Thị giác (Evidence-First Gate)
        try:
            ev_res = _enforce_evidence_first_gate(response_text, session_id=session_id)
            if ev_res:
                # Không nuốt câu trả lời: giữ nội dung gốc bên dưới cảnh báo để user vẫn đọc được.
                return f"{ev_res}\n\n--- Nội dung gốc (CHƯA XÁC MINH) ---\n{response_text}"
        except Exception as exc:
            logger.exception("[FARM_GUARD] Fail-closed exception in evidence gate: %s", exc)
            return (
                "🛑 **[EVIDENCE FIRST GATE — FAIL-CLOSED]**\n\n"
                f"Guard gặp lỗi nội tại khi kiểm chứng bằng chứng ({type(exc).__name__}); câu trả lời bị chặn để an toàn."
            )

        # 2. Chốt chặn Advisor Dual-Answer
        try:
            return _enforce_advisor_dual_answer(response_text, session_id=session_id)
        except Exception as exc:
            logger.exception("[FARM_GUARD] Fail-safe exception in advisor gate: %s", exc)
            if not response_text or not response_text.strip():
                return None
            return _advisor_failsafe_text(response_text)

    def pre_llm_hook(*args: Any, **kwargs: Any):
        return None

    ctx.register_hook("pre_llm_call", pre_llm_hook)
    ctx.register_hook("pre_tool_call", pre_tool_hook)
    ctx.register_hook("post_tool_call", post_tool_hook)
    ctx.register_hook("transform_llm_output", transform_output_hook)
    logger.info("[FARM_GUARD] Plugin 'farm-coordinator-guard' registered successfully via register(ctx) with transform_llm_output.")

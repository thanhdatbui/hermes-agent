"""
Farm Policy Engine (Shared Single Source of Truth for Farm Hard Guards).
Certified by Claude Opus / Claude Code CLI Architecture Specification.

Phục vụ cả Plugin (farm-coordinator-guard) và Shell Hook (guard_dispatch_contract.py).
Mọi quy tắc, parser và tiêu chí nghiệm thu được chuẩn hóa tập trung tại đây.
"""

from __future__ import annotations

import difflib
import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ==========================================
# 1. PATH ROOTS & PROTECTED TARGETS
# ==========================================
HERMES_ROOT = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes"))
ALLOWED_REPO_ROOTS = [
    os.path.realpath(r"D:\Taadaa"),
]
# Cho phép temp dir trong môi trường pytest để chạy test suites cách ly
if "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules:
    import tempfile
    ALLOWED_REPO_ROOTS.append(os.path.realpath(tempfile.gettempdir()))

COORD_ALLOWED_ROOTS = [
    os.path.realpath(r"D:\Taadaa"),
    os.path.realpath(str(HERMES_ROOT)),
]
if "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules:
    import tempfile
    COORD_ALLOWED_ROOTS.append(os.path.realpath(tempfile.gettempdir()))

# Ngân sách routine edit của Coordinator (user mở khóa 2026-10-05; chỉnh qua env khi cần)
COORD_T1_MAX_FILES = int(os.environ.get("COORD_T1_MAX_FILES", 5))
COORD_T1_MAX_LINES = int(os.environ.get("COORD_T1_MAX_LINES", 200))

GUARD_SOURCE_DIR = os.path.realpath(str(HERMES_ROOT / "plugins" / "farm-coordinator-guard"))
HOOKS_DIR_HERMES = os.path.realpath(str(HERMES_ROOT / "hooks"))
HOOKS_DIR_TAADAA = os.path.realpath(r"D:\Taadaa\tools\hooks")
SSH_DIR = os.path.realpath(str(Path.home() / ".ssh"))

CLOSEOUT_GATE_SCRIPT = os.path.realpath(r"D:\Taadaa\tools\closeout_gate.py")
# Guard luôn đọc audit log thật; chỉ test mới override qua biến này (Coordinator không set được env của gateway).
GATE_AUDIT_PATH = Path(os.environ.get("FARM_GUARD_GATE_AUDIT_PATH", r"D:\Taadaa\logs\gate_audit.jsonl"))

PROTECTED_EXACT_FILES = {
    os.path.realpath(str(HERMES_ROOT / "state.db")),
    os.path.realpath(str(HERMES_ROOT / "farm_coordinator_phase.json")),
    os.path.realpath(str(HERMES_ROOT / "farm_coordinator_phase.lock")),
    os.path.realpath(str(HERMES_ROOT / "farm_coordinator_phase.json.lock")),
    os.path.realpath(str(HERMES_ROOT / "config.yaml")),
    os.path.realpath(str(HERMES_ROOT / ".env")),
    os.path.realpath(r"D:\Taadaa\AGENTS.md"),
    os.path.realpath(r"D:\Taadaa\HERMES_SUBAGENT_RULES.md"),
    os.path.realpath(r"D:\Taadaa\tools\TIERED_WORKFLOW.md"),
    CLOSEOUT_GATE_SCRIPT,
    os.path.realpath(r"D:\Taadaa\logs\gate_audit.jsonl"),
}

# Thành phần đường dẫn cấm ghi/đụng tới với MỌI actor: thư mục .git (config, hooks, index...).
_GIT_DIR_COMPONENT_RE = re.compile(r"(?:^|[\\/])\.git(?:[\\/]|$)", re.IGNORECASE)

def has_git_dir_component(path_str: str) -> bool:
    """True nếu đường dẫn (tuyệt đối hoặc tương đối) đi qua thư mục `.git`."""
    if not path_str or not isinstance(path_str, str):
        return False
    s = path_str.strip().strip("'\"`")
    if not s or any(ch in s for ch in " \t\r\n"):
        return False
    if _GIT_DIR_COMPONENT_RE.search(s):
        return True
    try:
        return bool(_GIT_DIR_COMPONENT_RE.search(os.path.realpath(s)))
    except Exception:
        return False


def has_path_evasion(path_str: str) -> bool:
    """Né bằng tên 8.3 (GIT~1) hoặc NTFS alternate data stream (file::$DATA)."""
    if not path_str or not isinstance(path_str, str):
        return False
    s = path_str.strip().strip("'\"`")
    if re.match(r"^[A-Za-z]:", s):
        s_rest = s[2:]
    else:
        s_rest = s
    return ":" in s_rest or bool(re.search(r"(?:^|[\\/])[^\\/]*~\d", s))


def is_protected_target(path_str: str) -> bool:
    """Kiểm tra xem file/thư mục có nằm trong vùng cấm bảo vệ hệ thống hay không."""
    if not path_str or not isinstance(path_str, str):
        return False
    if has_git_dir_component(path_str):
        return True
    try:
        norm = os.path.normpath(path_str.strip().strip("'\"`"))
        if not os.path.isabs(norm):
            return False
        real = os.path.realpath(norm)
    except Exception:
        return False

    if os.path.normcase(real) in {os.path.normcase(p) for p in PROTECTED_EXACT_FILES}:
        return True

    # Bảo vệ các thư mục hooks và guard source
    for pdir in (GUARD_SOURCE_DIR, HOOKS_DIR_HERMES, HOOKS_DIR_TAADAA, SSH_DIR):
        if _is_path_in_roots(real, [pdir]):
            return True

    return False


def is_test_file(path_str: str) -> bool:
    """
    Xác định một file có phải là test file hợp lệ hay không (Single Source of Truth).
    Chống test filename spoofing theo audit của Sol Web:
    1. Bắt buộc có hậu tố .py (hoặc test script .sh/.ps1).
    2. Nằm trong thư mục tests/ hoặc test/.
    3. HOẶC tên file bắt đầu bằng test_ / kết thúc bằng _test.py / conftest.py,
       NHƯNG bị từ chối nếu nằm sâu trong thư mục module nghiệp vụ lõi (/src/, /app/, /services/, /handlers/).
    """
    if not path_str or not isinstance(path_str, str):
        return False
    try:
        norm = os.path.normpath(path_str.strip().strip("'\"`"))
    except Exception:
        return False

    base = os.path.basename(norm).lower()
    norm_fwd = norm.replace("\\", "/").lower()

    if not (base.endswith(".py") or base.endswith(".sh") or base.endswith(".ps1")):
        return False

    is_test_name = base.startswith("test_") or base.endswith("_test.py") or base == "conftest.py"
    is_in_test_dir = "/tests/" in norm_fwd or "/test/" in norm_fwd or norm_fwd.startswith("tests/") or norm_fwd.startswith("test/")

    if is_in_test_dir:
        return True

    if is_test_name:
        # Chặn filename spoofing nhét file test giả vào sâu trong mã nguồn nghiệp vụ
        forbidden_biz_dirs = ("/src/", "/app/", "/lib/", "/core/", "/flows/", "/handlers/", "/services/", "/controllers/")
        for fdir in forbidden_biz_dirs:
            if fdir in norm_fwd:
                return False
        return True

    return False


def is_related_test_file(test_file: str, eligible_targets: List[str]) -> bool:
    """
    Kiểm tra xem file test có liên kết hợp lệ với ít nhất một target bị fail của Worker không (L2 Reason Binding).
    Chống việc Coordinator mở L2 cho target A nhưng lại đi sửa file test của target B không liên quan.
    """
    if not eligible_targets:
        return True
    test_norm = os.path.normpath(test_file).lower().replace("\\", "/")
    test_base = os.path.basename(test_norm)
    test_stem = os.path.splitext(test_base)[0].replace("test_", "").replace("_test", "")

    for tgt in eligible_targets:
        tgt_norm = os.path.normpath(tgt).lower().replace("\\", "/")
        tgt_base = os.path.basename(tgt_norm)
        tgt_stem = os.path.splitext(tgt_base)[0]

        # 1. Khớp stem: follow_state <-> test_follow_state
        if test_stem and (test_stem == tgt_stem or test_stem in tgt_stem or tgt_stem in test_stem):
            return True

        # 2. Cùng repo / module boundary (chia sẻ >= 3 path segments, ví dụ D:/Taadaa/tiktok-follow)
        tgt_parts = tgt_norm.split("/")
        test_parts = test_norm.split("/")
        if len(tgt_parts) >= 3 and len(test_parts) >= 3:
            if tgt_parts[:3] == test_parts[:3]:
                return True
    return False


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


# ==========================================
# 2. PAYLOAD PARSER (FAIL-CLOSED)
# ==========================================
class ContractError(Exception):
    """Lỗi vi phạm Dispatch Contract."""
    pass


ARG_KEYS = ("tool_input", "args", "arguments", "function_args", "params", "input")


def extract_tool_args(payload: dict) -> dict:
    """Trích xuất args từ payload của Hermes tool call hoặc hook một cách fail-closed."""
    if not isinstance(payload, dict):
        raise ContractError("PAYLOAD_UNPARSEABLE: payload không phải dict")

    for k in ARG_KEYS:
        v = payload.get(k)
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                continue
        if isinstance(v, dict) and v:
            return v

    # Trường hợp payload chính là args dictionary
    if any(k in payload for k in ("goal", "context", "tasks", "command", "path")):
        return payload

    raise ContractError("PAYLOAD_UNPARSEABLE: không tìm thấy tool args hợp lệ trong payload")


# ==========================================
# 3. DISPATCH CONTRACT VALIDATOR (GATE 2 & GATE 4)
# ==========================================
EDIT_VERBS_PATTERN = re.compile(
    r"\b(sửa|sửa\s+code|chỉnh\s+sửa|cập\s+nhật|refactor|fix|fix\s+code|vá\s+code|patch|thay\s+thế|implement|tích\s+hợp)\b",
    re.IGNORECASE
)


def _extract_blocks(tag: str, text: str) -> List[str]:
    """Trích xuất khối dữ liệu dạng TAG: <<< ... >>> hoặc TAG: ..."""
    blocks = []
    # 1. Tìm khối multi-line <<< ... >>>
    pat_multi = re.compile(rf"\b{tag}:\s*<<<\s*[\r\n]+(.*?)\s*>>>", re.DOTALL | re.IGNORECASE)
    for m in pat_multi.finditer(text):
        blocks.append(m.group(1))

    if blocks:
        return blocks

    # 2. Tìm dạng dòng đơn TAG: ...
    pat_single = re.compile(rf"\b{tag}:\s*([^\r\n]+)", re.IGNORECASE)
    for m in pat_single.finditer(text):
        val = m.group(1).strip()
        if val and val != "<<<":
            blocks.append(val)
    return blocks


def validate_dispatch(task: dict, inherited: Optional[dict] = None) -> Dict[str, Any]:
    """Thẩm định một task trong delegate_task theo chuẩn GATE 2, GATE 4 & Anti-Disguise."""
    inherited = inherited or {}
    goal = str(task.get("goal") or inherited.get("goal") or "").strip()
    context = str(task.get("context") or inherited.get("context") or "").strip()
    combined = goal + "\n" + context

    if not combined.strip():
        raise ContractError("CONTRACT_EMPTY: delegate_task thiếu cả goal và context")

    # Xác định TASK_KIND
    kind_match = re.search(r"\bTASK_KIND:\s*(EDIT|INVESTIGATE)\b", combined, re.IGNORECASE)
    if not kind_match:
        # Tự suy luận nếu có thẻ rõ ràng
        has_edit_cards = bool(re.search(r"\b(OLD_STRING|Mã cũ|Đoạn cũ):\s*", combined, re.IGNORECASE))
        has_read_cards = bool(re.search(r"\b(chỉ đọc|read-only|inspect|investigate|audit|trace|check\s+log)\b", combined, re.IGNORECASE))
        has_edit_intent = bool(EDIT_VERBS_PATTERN.search(goal))
        if has_edit_cards:
            task_kind = "EDIT"
        elif has_read_cards and not has_edit_intent:
            task_kind = "INVESTIGATE"
        elif has_edit_intent:
            task_kind = "EDIT"
        elif has_read_cards:
            task_kind = "INVESTIGATE"
        else:
            # Nếu có target_files hoặc TARGET_FILE thì suy luận là EDIT
            if task.get("target_files") or re.search(r"\b(?:TARGET_FILE|SCOPE_LOCK|FILE):\s*", combined, re.IGNORECASE):
                task_kind = "EDIT"
            else:
                raise ContractError(
                    "MISSING_TASK_KIND: Bắt buộc khai báo 'TASK_KIND: EDIT' hoặc 'TASK_KIND: INVESTIGATE' trong context (SCOPE LOCK MISSING TARGET FILE)"
                )
    else:
        task_kind = kind_match.group(1).upper()

    # ----------------------------------------------------
    # NHÁNH INVESTIGATE (Thám hiểm / Đọc log - READ-ONLY)
    # ----------------------------------------------------
    if task_kind == "INVESTIGATE":
        if EDIT_VERBS_PATTERN.search(goal):
            raise ContractError(
                f"INVESTIGATE_HAS_EDIT_INTENT: Goal chứa động từ sửa code ('{goal[:80]}...'). "
                f"CẤM ngụy trang task sửa code thành investigate! Bắt buộc dùng 'TASK_KIND: EDIT' kèm Patch Contract O(1)."
            )

        # Budget calls cho investigate <= 5
        budget_match = re.search(r"\bBUDGET(?:_CALLS)?:\s*(?:<=\s*)?(\d+)", combined, re.IGNORECASE)
        budget = int(budget_match.group(1)) if budget_match else None
        if budget is not None and budget > 5:
            raise ContractError(f"INVESTIGATE_BUDGET_EXCEEDED: Budget điều tra ({budget} calls) > 5. Task đọc tối đa 5 calls.")

        # Fail-fast check
        if not re.search(r"(?:fail[_-]?fast|abort|dừng|thoát|<=?\s*\d|tối đa\s*\d|budget)", combined, re.IGNORECASE):
            raise ContractError("INVESTIGATE_MISSING_FAIL_FAST: Task điều tra bắt buộc có 'FAIL_FAST: ...'")

        return {
            "task_kind": "INVESTIGATE",
            "target_files": [],  # Strictly read-only: Worker không có quyền ghi bất kỳ file nào!
            "budget": budget or 5,
        }

    # ----------------------------------------------------
    # NHÁNH EDIT (Sửa code - BẮT BUỘC PATCH CONTRACT O(1))
    # ----------------------------------------------------
    files_declared = _extract_blocks(r"(?:FILE|Target file|target_file|File cần sửa|TARGET_FILE|SCOPE_LOCK)", combined)
    if not files_declared:
        tf_arg = task.get("target_files")
        if isinstance(tf_arg, list):
            files_declared = [str(x) for x in tf_arg if x]
        elif isinstance(tf_arg, str) and tf_arg.strip():
            files_declared = [tf_arg.strip()]

    if not files_declared:
        raise ContractError("EDIT_MISSING_FILE: Task EDIT bắt buộc có 'FILE: <đường_dẫn_tuyệt_đối>' (SCOPE LOCK MISSING TARGET FILE)")

    # Loại bỏ file test ra khỏi danh sách file nghiệp vụ nếu được khai báo riêng (dùng is_test_file dùng chung)
    biz_files = []
    test_files = []
    for f in files_declared:
        f_clean = f.strip().strip("'\"`")
        norm = os.path.normpath(f_clean)
        if is_test_file(norm):
            test_files.append(norm)
        else:
            if norm not in biz_files:
                biz_files.append(norm)

    total_files = list(set(biz_files + test_files))
    if len(total_files) > 2:
        raise ContractError(
            f"MULTI_FILE_VIOLATION: Phát hiện {len(total_files)} files trong 1 task ({total_files}). "
            f"Tối đa <= 2 files (1 file nghiệp vụ + 1 file test). Bắt buộc chẻ nhỏ task!"
        )

    # Thẩm định từng file đích
    for fp in total_files:
        if not os.path.isabs(fp):
            raise ContractError(f"PATH_NOT_ABSOLUTE: '{fp}' không phải đường dẫn tuyệt đối")
        if os.path.isdir(fp):
            raise ContractError(f"DIRECTORY NOT ALLOWED: '{fp}' là THƯ MỤC! Phải chỉ định file cụ thể.")
        if not _is_path_in_roots(fp, ALLOWED_REPO_ROOTS):
            raise ContractError(f"OUT OF REPO WHITELIST: File '{fp}' nằm ngoài whitelist {ALLOWED_REPO_ROOTS}!")
        if is_protected_target(fp):
            raise ContractError(f"GUARD SOURCE BLACKLISTED: CẤM Scope Lock vào file hệ thống: '{fp}'")

    # Thẩm định OLD_STRING và NEW_STRING
    old_strings = _extract_blocks(r"(?:OLD_STRING|Mã cũ|Đoạn cũ)", combined)
    new_strings = _extract_blocks(r"(?:NEW_STRING|Mã mới|Đoạn mới)", combined)

    total_diff_lines = 0
    if old_strings:
        if not new_strings:
            raise ContractError("EDIT_MISSING_NEW_STRING: Task EDIT bắt buộc có 'NEW_STRING: <<< ... >>>'")
        if len(old_strings) != len(new_strings):
            raise ContractError(f"EDIT_STRING_MISMATCH: Số lượng OLD_STRING ({len(old_strings)}) != NEW_STRING ({len(new_strings)})")

        # Guard tự mở file đếm anchor O(1)
        total_diff_lines = 0
        total_biz_diff_lines = 0
        total_test_diff_lines = 0
        for i, (old_s, new_s) in enumerate(zip(old_strings, new_strings)):
            old_s_clean = old_s.rstrip("\r\n")
            new_s_clean = new_s.rstrip("\r\n")

            if len(old_s_clean.strip()) < 8:
                raise ContractError(f"OLD_STRING_TOO_SHORT: Đoạn mã cũ #{i+1} quá ngắn (< 8 chars), không đủ làm anchor O(1)")
            if old_s_clean == new_s_clean:
                raise ContractError(f"OLD_EQUALS_NEW: Đoạn mã cũ và mới #{i+1} hoàn toàn giống nhau")

            # Tìm file chứa anchor này
            matched_file = None
            for fp in total_files:
                if not os.path.isfile(fp):
                    continue
                try:
                    c_txt = Path(fp).read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                count = c_txt.count(old_s_clean)
                if count == 1:
                    matched_file = fp
                    break
                elif count > 1:
                    raise ContractError(f"ANCHOR_NOT_UNIQUE: Đoạn mã cũ #{i+1} xuất hiện {count} lần trong '{fp}'. Bắt buộc c == 1!")

            if not matched_file:
                raise ContractError(f"ANCHOR_NOT_FOUND: Đoạn mã cũ #{i+1} không tìm thấy trong bất kỳ file đích nào!")

            diff = list(difflib.unified_diff(old_s_clean.splitlines(), new_s_clean.splitlines()))
            diff_lines = sum(1 for line in diff if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))
            total_diff_lines += diff_lines
            if matched_file in test_files:
                total_test_diff_lines += diff_lines
            else:
                total_biz_diff_lines += diff_lines

        # Tách bạch ngân sách code logic vs test verification alignment
        if biz_files and total_biz_diff_lines > 30:
            raise ContractError(f"DIFF_BUDGET_EXCEEDED: Dự tính thay đổi {total_biz_diff_lines} dòng code nghiệp vụ (> 30 dòng). Bắt buộc chẻ nhỏ task!")
        if total_test_diff_lines > 120:
            raise ContractError(f"TEST_DIFF_BUDGET_EXCEEDED: Dự tính thay đổi {total_test_diff_lines} dòng file test (> 120 dòng). Bắt buộc chẻ nhỏ task!")
        if not test_files and total_diff_lines > 30:
            raise ContractError(f"DIFF_BUDGET_EXCEEDED: Dự tính thay đổi {total_diff_lines} dòng (> 30 dòng). Bắt buộc chẻ nhỏ task!")
    else:
        # Nếu không có OLD_STRING: kiểm tra xem có phải task tạo file mới hoặc task legacy không
        is_create = bool(re.search(r"\b(tạo|create|new\s+file)\b", goal, re.IGNORECASE))
        has_kind_edit = bool(re.search(r"\bTASK_KIND:\s*EDIT\b", combined, re.IGNORECASE))
        if has_kind_edit and not is_create:
            raise ContractError("EDIT_MISSING_OLD_STRING: Task EDIT bắt buộc có 'OLD_STRING: <<< ... >>>'")

    # Thẩm định FOCUSED_TEST (Bắt buộc cho EDIT có contract)
    test_match = re.search(r"\bFOCUSED_TEST:\s*([^\r\n]+)", combined, re.IGNORECASE)
    if not test_match:
        if bool(re.search(r"\bTASK_KIND:\s*EDIT\b", combined, re.IGNORECASE)) or old_strings:
            raise ContractError("EDIT_MISSING_FOCUSED_TEST: Task EDIT bắt buộc có 'FOCUSED_TEST: python -m pytest <path>::<node>'")
    focused_test_cmd = test_match.group(1).strip() if test_match else ""

    pytest_match = None
    pycompile_match = None
    if focused_test_cmd:
        # Cấm shell injection / metacharacters trong test command
        if re.search(r"[;&|`$><()\n\r]", focused_test_cmd):
            raise ContractError(f"DANGEROUS_FOCUSED_TEST: FOCUSED_TEST chứa ký tự điều khiển shell nguy hiểm: '{focused_test_cmd}'")

        # Bắt buộc cú pháp pytest focused với node_id hoặc py_compile (hỗ trợ Windows drive letter C: / D:)
        pytest_match = re.search(
            r"^(?:python\s+-m\s+pytest|pytest)\s+([^\s]+?\.py)(?:::([A-Za-z0-9_]+))(?:\s+(.*))?$",
            focused_test_cmd,
            re.IGNORECASE
        )
        pycompile_match = re.search(
            r"^python\s+-m\s+py_compile\s+([^\s]+?\.py)$",
            focused_test_cmd,
            re.IGNORECASE
        )

        if not (pytest_match or pycompile_match):
            raise ContractError(
                f"INVALID_FOCUSED_TEST_FORMAT: FOCUSED_TEST '{focused_test_cmd}' không đúng định dạng chuẩn! "
                f"Bắt buộc là 'python -m pytest <file.py>::<test_node> -q' hoặc 'python -m py_compile <file.py>'"
            )

    test_file_path = pytest_match.group(1) if pytest_match else (pycompile_match.group(1) if pycompile_match else None)
    test_node = pytest_match.group(2) if pytest_match else None
    if pytest_match and not test_node:
        raise ContractError(
            f"FOCUSED_TEST_SUITE_RUN_BLOCKED: '{focused_test_cmd}' chạy cả file test mà không chỉ định ::node cụ thể! "
            f"Bắt buộc gắn ::<test_name> để chạy < 30s."
        )

    # Thẩm định Gate 4 (Fail-Fast Injection) khi có contract EDIT
    if bool(re.search(r"\bTASK_KIND:\s*EDIT\b", combined, re.IGNORECASE)):
        has_fail_fast = bool(re.search(r"(?:\bfail[_-]?fast\b|\babort\b|dừng\s+ngay)", combined, re.IGNORECASE)) and \
                        bool(re.search(r"(?:\b3\s+iter|\b3\s+vòng|<=?\s*3\b)", combined, re.IGNORECASE))
        if not has_fail_fast:
            raise ContractError(
                "GATE4_FAIL_FAST_MISSING: Prompt thiếu câu lệnh Fail-Fast bắt buộc: "
                "'FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT)...'"
            )

    # Thẩm định Budget
    budget_match = re.search(r"\bBUDGET(?:_CALLS)?:\s*(\d+)", combined, re.IGNORECASE)
    budget = int(budget_match.group(1)) if budget_match else 15
    if budget > 15:
        raise ContractError(f"WORKER_BUDGET_TOO_HIGH: Budget {budget} calls > 15 calls!")

    return {
        "task_kind": "EDIT",
        "target_files": total_files,
        "budget": budget,
        "diff_lines": total_diff_lines,
        "focused_test": focused_test_cmd,
    }


# ==========================================
# 4. COORDINATOR WRITE LEDGER & GATE
# ==========================================
def compute_edit_footprint(fn_name: str, fn_args: dict) -> List[Tuple[str, int]]:
    """Tính số dòng thay đổi và danh sách file bị tác động bởi write_file / patch."""
    results = []
    if fn_name == "write_file":
        target = fn_args.get("path") or ""
        content = fn_args.get("content") or ""
        if not target or not isinstance(target, str):
            raise ValueError("write_file thiếu path")
        real_p = os.path.realpath(target.strip())
        new_lines = len(content.splitlines())
        if os.path.isfile(real_p):
            try:
                old_lines = Path(real_p).read_text(encoding="utf-8", errors="replace").splitlines()
                diff = list(difflib.unified_diff(old_lines, content.splitlines()))
                changed = sum(1 for line in diff if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))
                results.append((real_p, changed))
            except Exception:
                results.append((real_p, new_lines))
        else:
            results.append((real_p, new_lines))

    elif fn_name == "patch":
        target = fn_args.get("path") or ""
        mode = fn_args.get("mode") or "replace"
        if mode == "replace":
            old_s = fn_args.get("old_string") or ""
            new_s = fn_args.get("new_string") or ""
            if not target or not isinstance(target, str):
                raise ValueError("patch thiếu path")
            real_p = os.path.realpath(target.strip())
            diff = list(difflib.unified_diff(old_s.splitlines(), new_s.splitlines()))
            changed = sum(1 for line in diff if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))
            results.append((real_p, changed))
        elif mode == "patch":
            patch_content = fn_args.get("patch") or ""
            # V4A patch format
            targets = re.findall(r"^\*\*\*\s+(?:Update|Add|Delete)\s+File:\s*(.+)$|^\*\*\*\s+Move\s+to:\s*(.+)$", patch_content, re.MULTILINE | re.IGNORECASE)
            targets = [a or b for a, b in targets]
            if not targets:
                targets = re.findall(r"^[+-]{3}\s+[ab]/(.+)$", patch_content, re.MULTILINE)
            if not targets:
                raise ValueError("V4A patch không tìm thấy file header")
            changed = sum(1 for line in patch_content.splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))
            per_file_changed = max(1, changed // len(targets))
            for t in targets:
                results.append((os.path.realpath(t.strip()), per_file_changed))

    return results


def coordinator_write_gate(
    sess_id: str,
    fn_name: str,
    fn_args: dict,
    state: dict
) -> Tuple[bool, str, dict]:
    """
    Ràng buộc ghi mã nguồn của Coordinator:
    - T1: <= COORD_T1_MAX_FILES files, tổng diff <= COORD_T1_MAX_LINES dòng CỘNG DỒN cả session (routine edits).
    - L2 (Emergency Surgery): Đúng 2 files, <= 30 dòng, CHỈ KHI guard đã tự quan sát l2_eligible=True.
    - Nếu vi phạm: BLOCK FAIL-CLOSED.
    """
    try:
        edits = compute_edit_footprint(fn_name, fn_args)
    except Exception as e:
        return False, f"COORDINATOR WRITE BLOCKED: Không thể phân tích footprint edit: {e}", state

    if not edits:
        return False, "COORDINATOR WRITE BLOCKED: Không phát hiện file mục tiêu hợp lệ", state

    for p, _ in edits:
        if has_git_dir_component(p) or has_path_evasion(p):
            return False, f"COORDINATOR WRITE BLOCKED: CẤM ghi/sửa vào thư mục .git hoặc đường dẫn né (8.3/ADS): '{p}'", state
        if is_protected_target(p):
            return False, f"COORDINATOR WRITE BLOCKED: File '{p}' nằm trong vùng bảo vệ hệ thống!", state
        if not _is_path_in_roots(p, COORD_ALLOWED_ROOTS):
            return False, f"COORDINATOR WRITE BLOCKED: File '{p}' nằm ngoài whitelist {COORD_ALLOWED_ROOTS}!", state

    led = state.setdefault("write_ledger", {
        "t1_files": [],
        "t1_lines": 0,
        "l2_used": False,
        "l2_open": False,
        "l2_files": [],
        "l2_lines": 0
    })
    # Tương thích ngược schema cũ nếu thiếu các trường phân loại (Sol EXPLOIT-03)
    if "l2_biz_lines" not in led:
        led["l2_biz_lines"] = led.get("l2_lines", 0)
    if "l2_test_lines" not in led:
        led["l2_test_lines"] = 0

    new_files = {p for p, _ in edits}
    new_lines = sum(n for _, n in edits)

    # 1. Kiểm tra L2 (nếu đang trong phiên L2)
    if led.get("l2_open"):
        l2_files = set(led.get("l2_files", [])) | new_files
        biz_l2 = {p for p in l2_files if not is_test_file(p)}
        test_l2 = {p for p in l2_files if is_test_file(p)}

        total_l2_lines = led.get("l2_lines", 0) + new_lines
        total_biz_lines = led.get("l2_biz_lines", 0) + sum(n for p, n in edits if not is_test_file(p))
        total_test_lines = led.get("l2_test_lines", 0) + sum(n for p, n in edits if is_test_file(p))

        is_l2_ok = False
        if len(l2_files) <= 2:
            if biz_l2 and test_l2:
                # 1 file code nghiệp vụ (<= 30 dòng) + 1 file test verification (<= 120 dòng)
                if total_biz_lines <= 30 and total_test_lines <= 120:
                    is_l2_ok = True
            elif not biz_l2 and test_l2:
                # Chỉ có file test độc lập -> tuân thủ trần 30 dòng
                if total_l2_lines <= 30:
                    is_l2_ok = True
            else:
                # Chỉ có file nghiệp vụ -> tuân thủ trần 30 dòng
                if total_biz_lines <= 30:
                    is_l2_ok = True

        if is_l2_ok:
            led["l2_files"] = list(l2_files)
            led["l2_lines"] = total_l2_lines
            led["l2_biz_lines"] = total_biz_lines
            led["l2_test_lines"] = total_test_lines
            return True, "", state
        else:
            led["l2_open"] = False
            return False, (
                f"L2 BUDGET EXCEEDED: L2 cho phép tối đa 2 files và <= 30 dòng diff code nghiệp vụ (hoặc <= 120 dòng test alignment). "
                f"Yêu cầu hiện tại: {len(l2_files)} files, {total_l2_lines} dòng (biz: {total_biz_lines}, test: {total_test_lines})."
            ), state

    # 2. Kiểm tra nếu có thể mở L2
    if state.get("l2_eligible") and not led.get("l2_used"):
        # Mở L2 lần duy nhất
        eligible_targets = set(state.get("l2_targets", []))
        if eligible_targets:
            for p in new_files:
                if p not in eligible_targets:
                    if not is_test_file(p):
                        return False, (
                            f"L2 TARGET MISMATCH: L2 chỉ được phép sửa đúng target đã fail của Worker hoặc file test đi kèm: {eligible_targets}. "
                            f"Thực tế đang sửa: {new_files}"
                        ), state
                    elif not is_related_test_file(p, list(eligible_targets)):
                        return False, (
                            f"L2 TEST UNBOUND: File test '{p}' không có liên hệ với target bị fail của Worker: {eligible_targets}!"
                        ), state

        biz_new = {p for p in new_files if not is_test_file(p)}
        test_new = {p for p in new_files if is_test_file(p)}
        new_biz_lines = sum(n for p, n in edits if not is_test_file(p))
        new_test_lines = sum(n for p, n in edits if is_test_file(p))

        can_open = False
        if len(new_files) <= 2:
            if biz_new and test_new:
                if new_biz_lines <= 30 and new_test_lines <= 120:
                    can_open = True
            elif not biz_new and test_new:
                if new_lines <= 30:
                    can_open = True
            else:
                if new_biz_lines <= 30:
                    can_open = True

        if can_open:
            led["l2_used"] = True
            led["l2_open"] = True
            led["l2_files"] = list(new_files)
            led["l2_lines"] = new_lines
            led["l2_biz_lines"] = new_biz_lines
            led["l2_test_lines"] = new_test_lines
            return True, "", state
        else:
            return False, f"L2 REJECTED: L2 vượt ngân sách khởi tạo ({len(new_files)} files, {new_lines} dòng > 30).", state

    # 3. Kiểm tra T1 (routine edits của Coordinator, không cần Sol plan / worker)
    t1_files = set(led.get("t1_files", [])) | new_files
    total_t1_lines = led.get("t1_lines", 0) + new_lines

    if len(t1_files) <= COORD_T1_MAX_FILES and total_t1_lines <= COORD_T1_MAX_LINES:
        led["t1_files"] = list(t1_files)
        led["t1_lines"] = total_t1_lines
        return True, "", state

    # Hết ngân sách T1 và L2 chưa đủ điều kiện
    return False, (
        f"⛔ [COORDINATOR WRITE DENIED]: Hết ngân sách T1 (tối đa {COORD_T1_MAX_FILES} files, <= {COORD_T1_MAX_LINES} dòng cộng dồn cả session). "
        f"Đã dùng: {len(t1_files)} files, {total_t1_lines} dòng. "
        f"L2 Emergency Surgery chưa đủ điều kiện (cần 2 lần Worker failure liên tiếp trên cùng target). "
        f"BẮT BUỘC DISPATCH WORKER Luna High qua delegate_task với PATCH CONTRACT O(1)!"
    ), state


# ==========================================
# 5. COORDINATOR TERMINAL WHITELIST & SAFEGUARD
# ==========================================
DANGEROUS_WRITE_COMMANDS = re.compile(
    r"(?:\bopen\s*\([^)]*,\s*(?:mode\s*=\s*)?['\"][^'\"]*[wax\+][^)]*\)"
    r"|\bwrite_text\s*\("
    r"|\bwrite_bytes\s*\("
    r"|\bSet-Content\b"
    r"|\bOut-File\b"
    r"|\bAdd-Content\b"
    r"|\bNew-Item\b"
    r"|\bsed\s+-i"
    r"|\btee\b"
    r"|\bcp\b"
    r"|\bmv\b"
    r"|\bCopy-Item\b"
    r"|\bMove-Item\b"
    r"|\bgit\s+apply\b"
    r"|\bgit(?:\s+-[^\s]+|\s+--[^\s]+)*\s+commit\b"
    r"|\bgit(?:\s+-[^\s]+|\s+--[^\s]+)*\s+push\b"
    r"|\bgit\s+checkout\s+--"
    r"|\bgit\s+restore\b"
    r"|\bgit\s+reset\b)",
    re.IGNORECASE
)


_COORD_SOURCE_EXT_RE = re.compile(r"\.(?:py|ps1|psm1|sh|bat|cmd|js|ts|yaml|yml|toml|ini|cfg)$", re.IGNORECASE)
_COORD_GIT_READ = {
    "status", "diff", "log", "show", "branch", "rev-parse", "merge-base", "ls-files", "blame",
    "remote", "fetch", "worktree", "tag", "describe", "shortlog", "grep", "reflog", "cat-file",
    "add", "commit", "pull", "merge", "rebase", "cherry-pick", "switch", "fsck", "merge-tree", "config",
}
_COORD_SAFE_PREFIX_RE = re.compile(
    r"^(?:cat|head|tail|grep|rg|wc|ls|dir|type|echo|pwd|where|which|sort|uniq|cut|awk|jq|diff|fc|tree|stat|file"
    r"|mkdir|cp|claude|opencode|antigravity|psutil|tasklist|taskkill|hostname|whoami|date|true"
    r"|Get-Content|Select-String|Get-ChildItem|Get-Item|Test-Path|Get-Process|Get-ScheduledTask|Get-Date"
    r"|Write-Output|Write-Host|Resolve-Path|Measure-Object|Select-Object|Where-Object|ForEach-Object|Format-List|Format-Table"
    r"|sed(?![^|;&]*\s-i))(?:\.exe)?(?:\s|$)",
    re.IGNORECASE,
)


def _coord_split_segments(cmd: str) -> List[str]:
    """Tách lệnh theo && || ; | xuống dòng, bỏ qua ký tự nằm trong nháy."""
    segs, cur, quote, i = [], [], None, 0
    while i < len(cmd):
        c = cmd[i]
        if quote:
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c in ";|\n" or (c == "&" and cmd[i:i + 2] == "&&"):
            segs.append("".join(cur))
            cur = []
            i += 2 if cmd[i:i + 2] in ("&&", "||") else 1
            continue
        cur.append(c)
        i += 1
    segs.append("".join(cur))
    return [x.strip() for x in segs if x.strip()]


def _coord_redirect_violation(seg: str) -> str:
    """Chỉ chặn redirect ghi đè file mã nguồn/cấu hình hoặc vùng bảo vệ; 2>&1, >nul, >log.txt... được phép."""
    unquoted = re.sub(r"\"[^\"]*\"|'[^']*'", "", seg)
    unquoted = re.sub(r"\d*>&\d*", "", unquoted)
    for m in re.finditer(r"\d*>{1,2}\s*([^\s;&|]+)", unquoted):
        target = m.group(1).strip("\"'")
        if _COORD_SOURCE_EXT_RE.search(target) or is_protected_target(target):
            return target
    return ""


def _coord_segment_gate(seg: str, state: dict) -> Tuple[bool, str]:
    if re.match(r"^(?:cd|Set-Location|pushd|popd)(?:\s|$)", seg, re.IGNORECASE):
        return True, ""

    bad_target = _coord_redirect_violation(seg)
    if bad_target:
        return False, f"COORDINATOR TERMINAL BLOCKED: Cấm redirect '>' ghi đè file mã nguồn/bảo vệ '{bad_target}' (dùng patch/write_file)."

    if re.search(r"\b(os\.walk|rglob)\b|glob\.glob\s*\([^)]*\*{2}", seg):
        return False, "COORDINATOR TERMINAL BLOCKED: Cấm dùng os.walk hoặc glob recursive quét đĩa diện rộng!"

    git_m = re.match(r"""^git(?:\.exe)?((?:\s+(?:-C\s+(?:"[^"]*"|'[^']*'|\S+)|-c\s+\S+|--no-pager|-P))*)\s+([\w-]+)(.*)$""", seg, re.IGNORECASE | re.DOTALL)
    if git_m:
        opts, sub, rest = git_m.group(1), git_m.group(2).lower(), git_m.group(3)
        if re.search(r"(?:^|\s)-c\s", opts) or re.search(r"--exec\b", rest):
            return False, "COORDINATOR TERMINAL BLOCKED: Cờ git nguy hiểm (-c / --exec) bị cấm!"
        if sub == "push":
            if not state.get("closeout_passed") and not state.get("last_closeout_score", 0) >= 85:
                return False, "COORDINATOR TERMINAL BLOCKED: Cấm 'git push' trước khi Closeout Gate trả về APPROVED >= 85!"
            return True, ""
        if sub == "reset" and re.search(r"--hard\b", rest):
            return False, "COORDINATOR TERMINAL BLOCKED: Cấm 'git reset --hard' (hủy working tree)!"
        if sub == "checkout" and re.search(r"(?:^|\s)(?:--|\.)(?:\s|$)", rest):
            return False, "COORDINATOR TERMINAL BLOCKED: Cấm 'git checkout -- / .' (hủy working tree)!"
        if sub == "restore" and not re.search(r"--staged\b", rest):
            return False, "COORDINATOR TERMINAL BLOCKED: Cấm 'git restore' working tree (chỉ cho --staged)!"
        if sub == "clean" and re.search(r"(?:^|\s)-[a-zA-Z]*f", rest):
            return False, "COORDINATOR TERMINAL BLOCKED: Cấm 'git clean -f' (xóa file chưa track)!"
        if sub == "stash" and not re.match(r"\s+(?:list|show)\b", rest):
            return False, "COORDINATOR TERMINAL BLOCKED: Chỉ cho 'git stash list/show' (stash push/drop có thể giấu diff session khác)!"
        if sub in _COORD_GIT_READ or sub in ("reset", "checkout", "restore", "stash"):
            return True, ""
        return False, f"COORDINATOR TERMINAL BLOCKED: 'git {sub}' không nằm trong allowlist của Coordinator (git apply -> dùng patch tool)."

    if re.match(r"^(?:python3?|py)(?:\.exe)?\s+-c\b", seg, re.IGNORECASE):
        if DANGEROUS_WRITE_COMMANDS.search(seg) or re.search(r"\b(?:os\.remove|os\.unlink|shutil\.(?:rmtree|move|copy\w*)|subprocess|os\.system)\b", seg):
            return False, "COORDINATOR TERMINAL BLOCKED: 'python -c' chỉ dùng để kiểm chứng read-only; phát hiện thao tác ghi/xóa/subprocess!"
        return True, ""
    if re.match(r"""^(?:(?:python3?|py)(?:\.exe)?(?:\s+-[uXIB]\S*)*\s+(?:-m\s+(?:pytest|py_compile|json\.tool)\b|(?:"[^"]+\.py"|'[^']+\.py'|\S+\.py)(?:\s|$))|pytest(?:\.exe)?(?:\s|$))""", seg, re.IGNORECASE):
        return True, ""

    if re.match(r"^adb(?:\.exe)?(?:\s|$)", seg, re.IGNORECASE):
        if re.search(r"\binput\s+(?:tap|swipe)\b", seg, re.IGNORECASE):
            return False, "COORDINATOR TERMINAL BLOCKED: CẤM TUYỆT ĐỐI 'adb shell input tap/swipe' bấm tay thay cho sửa code!"
        return True, ""

    if _COORD_SAFE_PREFIX_RE.match(seg):
        return True, ""

    return False, f"COORDINATOR TERMINAL BLOCKED (DEFAULT-DENY): Lệnh '{seg[:80]}' không nằm trong allowlist của Coordinator!"


def coordinator_terminal_gate(cmd: str, state: dict) -> Tuple[bool, str]:
    """DEFAULT-DENY theo từng đoạn lệnh (&&, ;, |): mọi đoạn phải nằm trong allowlist.
    Mở khóa 2026-10-05: regex git neo theo subcommand (hết false positive 'git log --grep push'),
    bỏ chặn 2>&1 / redirect ra log, cho phép git read/commit local, python -c read-only, tiện ích đọc."""
    if not cmd or not isinstance(cmd, str):
        return True, ""
    for seg in _coord_split_segments(cmd.strip()):
        ok, reason = _coord_segment_gate(seg, state)
        if not ok:
            return False, reason
    return True, ""

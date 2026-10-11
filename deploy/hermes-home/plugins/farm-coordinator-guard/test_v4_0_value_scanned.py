import os
import pytest
import sys

PLUGIN_DIR = r"C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard"
sys.path.insert(0, PLUGIN_DIR)

from __init__ import (
    check_worker_tool_gate,
    _on_pre_tool_call,
    _PARENT_SESSION_CACHE,
)


@pytest.fixture(autouse=True)
def cleanup_env():
    os.environ.pop("TAADAA_WORKER", None)
    _PARENT_SESSION_CACHE.clear()
    yield


def test_alias_gap_closed_arbitrary_parameter_names_scanned():
    """LÝ DO 1 CLOSED: Worker dùng read_file(file_path=...), search_files(query=...) hay bất kỳ key lạ nào
    đều bị hàm _extract_all_string_values quét ra và BLOCK 100% nếu đụng target bảo vệ!
    """
    worker_sid = "worker_alias_test"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    # 1. read_file với tham số lạ 'file_path' trỏ ~/.ssh -> BỊ CHẶN!
    res1 = check_worker_tool_gate("read_file", worker_sid, {"file_path": r"C:/Users/Kibe/.ssh/id_rsa"})
    assert res1 is not None
    assert "INFO-LEAK BLOCKED" in res1.get("reason", "") or "OUT OF WHITELIST" in res1.get("reason", "")

    # 2. search_files với tham số 'query' hoặc 'pattern' trỏ state.db -> BỊ CHẶN!
    res2 = check_worker_tool_gate("search_files", worker_sid, {"pattern": "password", "custom_dir": r"C:/Users/Kibe/AppData/Local/hermes/state.db"})
    assert res2 is not None
    assert "INFO-LEAK BLOCKED" in res2.get("reason", "") or "OUT OF WHITELIST" in res2.get("reason", "")


def test_narrowed_whitelist_hermes_home_is_out_of_whitelist():
    """LÝ DO 2 / GHI CHÚ: HERMES_ROOT đã bị loại khỏi ALLOWED_REPO_ROOTS -> Mọi truy cập vào hermes home đều bị coi là out of whitelist."""
    worker_sid = "worker_hermes_leak"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    # Worker đọc file bất kỳ trong AppData/Local/hermes -> BỊ CHẶN OUT OF WHITELIST!
    res = check_worker_tool_gate("read_file", worker_sid, {"path": r"C:/Users/Kibe/AppData/Local/hermes/config.yaml"})
    assert res is not None
    assert "OUT OF WHITELIST" in res.get("reason", "") or "INFO-LEAK BLOCKED" in res.get("reason", "")


def test_git_no_textconv_flag_allowed_and_env_enforced():
    """LÝ DO 2 CLOSED: Lệnh git diff hỗ trợ cờ --no-textconv và tự động nạp core.attributesfile=/dev/null."""
    worker_sid = "worker_git_textconv"
    _PARENT_SESSION_CACHE[worker_sid] = "parent_1"

    res = check_worker_tool_gate("terminal", worker_sid, {"command": "git diff --no-textconv"})
    assert res is None
    assert "core.attributesfile=/dev/null" in os.environ.get("GIT_CONFIG_PARAMETERS", "")
    assert os.environ.get("GIT_ATTR_NOSYSTEM") == "1"

# Parasite Guard Telemetry & Zero-Modification Timeout Prevention (24/09/2026)

## 1. Bài học xương máu: Bẫy 0-Files-Modified và Timeout 180s khi quét đĩa

### Bối cảnh sự cố (Session 24/09/2026):
- User yêu cầu nâng cấp Telemetry & Exception Handling trong `D:/Taadaa/Tiktok_Reg/parasite_guard.py` và mở rộng test suite `test_parasite_guard.py`.
- Ràng buộc cứng: `Budget <= 8 calls, hoàn thành dưới 3 phút`, Closeout Gate >= 85/100.
- Đặc tả yêu cầu đã được user cung cấp 100% đầy đủ trong prompt (format log telemetry, đường dẫn file JSONL audit, log cảnh báo khi lỗi workbook, các điểm gọi audit, tên 2 test cases mới).

### Nguyên nhân thất bại nghiêm trọng:
1. **Quét đĩa diện rộng gây treo (180s timeout)**:
   - Worker chạy `rg "telemetry:" "D:/Taadaa"` và `os.walk('D:/Taadaa/Tiktok_Reg')` tìm kiếm lan man xem repo khác làm telemetry thế nào.
   - Trên Windows với các repo phone farm có OneDrive/worktrees/venv, các lệnh quét đĩa không giới hạn phạm vi bị treo cứng 180s mỗi lệnh, ngốn sạch thời gian phiên.
2. **Analysis Paralysis & Vi phạm Budget**:
   - Thay vì đọc 2 file (`parasite_guard.py`, `test_parasite_guard.py`), sửa file ngay và chạy test trong vòng 5-6 calls, worker dùng 14 calls chỉ để tìm kiếm, liệt kê và phân tích các hàm ngoại vi (`pick_and_fill_email`).
   - Kết quả: Hết hạn mức tool call (maximum iterations) mà **0 files modified**, task fail hoàn toàn dù lời giải đã rõ ràng.

---

## 2. Kỷ luật phân bổ Budget cứng cho tác vụ Telemetry / Guard / TDD (<= 8 calls)

Khi nhận task có ngân sách hữu hạn (`<= 8 calls`) với đặc tả rõ ràng:
- **Phase PLAN (Tối đa 2 calls)**:
  - Call 1: Đọc target file (ví dụ: `parasite_guard.py`).
  - Call 2: Đọc test file (ví dụ: `tests/test_parasite_guard.py`).
  - CẤM chạy bất kỳ lệnh tìm kiếm diện rộng (`rg`, `find`, `os.walk`, `search_files` trên root).
- **Phase EXECUTE (Tối đa 3 calls)**:
  - Call 3: Sửa target file theo đúng đặc tả (dùng `patch` hoặc `write_file`).
  - Call 4: Bổ sung tests vào test file.
- **Phase VERIFY & CLOSE (Tối đa 2 calls)**:
  - Call 5: Chạy test cô lập:
    `PYTHONPATH="D:/Taadaa/Tiktok_Reg;D:/Taadaa/automation-core" python -m pytest D:/Taadaa/Tiktok_Reg/tests/test_parasite_guard.py -v -p no:cacheprovider`
  - Call 6: Git add & commit theo đúng message quy chuẩn.

---

## 3. Đặc tả chuẩn cho Parasite Guard Telemetry & Audit Persistence

Hệ thống chống nick ký sinh (`parasite_guard.py`) đảm bảo tài khoản TikTok thuộc sở hữu của máy nào (`target_stt`) chỉ được phép thao tác trên đúng máy đó:

### A. Cấu trúc hàm `record_parasite_audit_event`:
```python
import json
from datetime import datetime, timezone
from pathlib import Path

AUDIT_LOG_PATH = Path("D:/Taadaa/runtime/audit/parasite_guard_audit.jsonl")

def record_parasite_audit_event(
    action: str,
    target_stt: int | str,
    account: str,
    owner_stt: int | str | None,
    status: str,
    reason: str,
    audit_path: Path | None = None,
) -> dict:
    """Ghi structured log telemetry va append vao file audit JSONL."""
    log_line = (
        f"[telemetry:parasite-guard] action={action} target_stt={target_stt} "
        f"account={account} owner_stt={owner_stt} status={status} reason={reason}"
    )
    print(log_line)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": str(action),
        "target_stt": target_stt,
        "account": str(account),
        "owner_stt": owner_stt,
        "status": str(status),
        "reason": str(reason),
    }

    target_file = audit_path or AUDIT_LOG_PATH
    try:
        target_file.parent.mkdir(parents=True, exist_ok=True)
        with open(target_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as exc:
        print(f"⚠ [parasite-guard:warning] Failed to append audit event to {target_file}: {exc}")

    return payload
```

### B. Exception Logging trong `find_account_owner_stt`:
Thay vì nuốt ngoại lệ với `except Exception: pass`, bắt buộc ghi log cảnh báo:
```python
except Exception as exc:
    print(f"⚠ [parasite-guard:warning] Failed to inspect workbook {wb_path}: {exc}")
```

### C. Các điểm gắn Telemetry trong `assert_account_machine_binding`:
1. **Block (phát hiện nick ký sinh)**:
   ```python
   record_parasite_audit_event("block", t_stt, account_identifier, owner_stt, "blocked", "parasite_detected")
   ```
2. **Override (operator cho phép ghi đè)**:
   ```python
   record_parasite_audit_event("override", t_stt, account_identifier, owner_stt, "allowed", reason)
   ```
3. **Verify / Valid (khớp máy chủ sở hữu)**:
   ```python
   record_parasite_audit_event("verify", t_stt, account_identifier, owner_stt, "matched", "valid_binding")
   ```

---

## 4. Test Suite mở rộng cho Parasite Guard (`tests/test_parasite_guard.py`)

Hai test bắt buộc để pass Closeout Gate >= 85/100:

1. **`test_parasite_guard_audit_event_logged_and_persisted(tmp_path, capsys)`**:
   - Truyền `audit_path = tmp_path / "test_audit.jsonl"`.
   - Gọi `record_parasite_audit_event("block", 201, "acc_test", 22, "blocked", "parasite_detected", audit_path=...)`.
   - Kiểm tra `capsys.readouterr().out` chứa `[telemetry:parasite-guard] action=block target_stt=201`.
   - Đọc file `test_audit.jsonl`, parse JSON và kiểm tra các fields (`action`, `target_stt`, `account`, `owner_stt`, `status`, `reason`).

2. **`test_pick_and_fill_email_aborts_registered_account()`**:
   - Mock `detect_after_continue` trả về `"registered"`.
   - Kiểm tra luồng xử lý email khi gặp nick đã đăng ký trên hệ thống thì abort email đó, không trả về credentials để tiếp tục tiến trình reg.

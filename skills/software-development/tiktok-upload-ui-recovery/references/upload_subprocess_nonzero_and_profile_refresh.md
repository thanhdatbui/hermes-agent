# Upload Subprocess Nonzero & Profile Verify Recovery

## 1. Bản chất của `upload_subprocess_nonzero`
- `upload_subprocess_nonzero` là lỗi catch-all ở tầng batch launcher (`run_tiktok_upload_batch.ps1`) khi tiến trình con (`python -m tiktok_workflow ...`) thoát với exit code khác 0.
- Bất kỳ lỗi nào trong workflow (kẹt UI, popup đè, timeout, sai account...) đều dẫn tới exit code khác 0.
- **Cách lấy Root Cause chuẩn xác:**
  + Không quét đĩa diện rộng (`grep -rn` trên toàn ổ/thư mục lớn sẽ bị timeout 900s làm treo session).
  + Mở trực tiếp file report của phiên: `D:/CodexRuntime/tiktok-video/runs/<run_id>/report.json`.
  + Đọc các trường: `reason`, `status`, `last_state` (ví dụ: `[ACCOUNT_SWITCHER_FAILED] ACCOUNT_VERIFY_MISMATCH: Profile did not show the expected account`).
  + `run_tiktok_upload_batch.ps1` đã được cấu hình tự động trích xuất `report.reason` vào `summary.csv` và output console để hiển thị chính xác triệu chứng.

## 2. Pitfall `tap_profile` trong `ACCOUNT_READY`
- Trong state `ACCOUNT_READY`, khi verify tài khoản chưa khớp (`ACCOUNT_VERIFY_MISMATCH`), quy trình cần tap lại tab Hồ sơ để làm mới UI XML.
- **Nguyên nhân bug:** `adapter.tap_profile()` có guard `if self.is_profile_root(xml_text): return` (nếu màn hình đã giống Profile root thì bỏ qua lệnh tap). Khi màn hình đang ở Profile cũ hoặc chưa load username mới, guard này làm lệnh tap bị huỷ âm thầm, dẫn đến retry 20s không tap được gì và fail-closed.
- **Giải pháp chuẩn:**
  + `adapter.tap_profile(force: bool = False)`: hỗ trợ cờ `force=True` để bypass guard `is_profile_root`.
  + Trong `_handle_account_ready` của `state_machine.py`, khi retry verify account, gọi `self.context.adapter.tap_profile(force=True)`.

# Chuẩn Hóa Bắt Buộc Check VPN Fail-Closed Trên Toàn Bộ Repo Automation Farm

## Bối Cảnh & Yêu Cầu
- Trên hệ thống Farm nuôi nick / đăng bài Taadaa (160 máy), toàn bộ máy có gán proxy trong workbook mapping bắt buộc phải kết nối VPN ViChanger thành công trước khi thao tác.
- Tuyệt đối cấm chạy với IP mạng trực tiếp (IP máy chủ/Đà Nẵng) để tránh quét hàng loạt và hỏng nick.
- Yêu cầu áp dụng thống nhất và fail-closed trên **TẤT CẢ các repo automation** nằm dưới `D:\Taadaa`.

---

## Danh Sách Repo & Module Check Chuẩn
Mọi repo sử dụng `automation_core.preflight` hoặc module preflight cục bộ đều phải tuân thủ chữ ký và hành vi sau:

1. **`tiktok-luot nuoi acc` (`python_runner/core/vpn_preflight.py` & `run_tiktok.py`):**
   - Gọi `require_vichanger_connected()` / `require_android_vpn(required=True)`.
   - Bắt buộc kiểm tra trước khi validate thiết bị và khởi động `feed_session_smoke`.

2. **`Tiktok-video` (`scripts/tiktok_workflow/state_machine.py`):**
   - Bước `RESOLVE_DEVICE`:
     ```python
     require_android_vpn(
         AdbClient(**adb_kwargs),
         required=True,
     )
     ```
   - Nếu mất VPN / check thất bại $\rightarrow$ Raise `WorkflowError(WorkflowState.RESOLVE_DEVICE, "VPN required before TikTok run", "VPN_REQUIRED_NOT_CONNECTED")`.

3. **`tiktok-follow` (`follow_runner/run_follow.py`):**
   - Check `require_vichanger_connected()` trước khi vào flow follow chéo.

4. **`tiktok-log-in` (`login_runner/account_reconcile.py`, `account_inventory.py`, `cli.py`):**
   - Check `require_android_vpn(required=True)`.

5. **`tiktok-add-bao-mat-f2a` (`python_runner/run_batch_live_2fa.py`):**
   - Check `require_android_vpn(required=True)`.

6. **`Tiktok_Reg`, `Hotmail`, `register gmail`, `add mail khoi phuc`:**
   - Đều đã tích hợp `require_android_vpn` trước khi mở app/thao tác đăng ký tài khoản.

---

## Quy Trình Xử Lý Khi Mất VPN
1. Kiểm tra serial trong file mapping proxy của host (`resolve_proxy_mapping_path()`).
2. Nếu máy có gán proxy nhưng mất VPN:
   - Thử tự động hồi phục qua `recover_missing_android_vpn()` (gọi GanProxy reassign $\rightarrow$ soft-reboot 1 lần $\rightarrow$ kiểm tra lại).
   - Nếu vẫn không có VPN $\rightarrow$ Dừng phiên ngay lập tức (**FAIL-CLOSED**), không tiếp tục chạy app bằng IP mạng thật.

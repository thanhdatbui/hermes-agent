# TikTok Batch Upload Execution, Live VPN Preflight & Concurrency Triage

## 1. Cơ chế xác nhận & TTY Bypass trong Subprocess
- **Sự cố:** `run_post.py` có prompt `input("> ")` để yêu cầu gõ `YES` khi chạy interactive.
- **PowerShell launcher cũ (`run_tiktok_upload_batch.ps1`):** Hoạt động được vì nó chủ động pipe chuỗi xác nhận `$ConfirmationToken | & $Python @Arguments`.
- **Python subprocess hook mới:** Khi chạy `subprocess.run` không có TTY/stdin, `input()` văng `EOFError` (nếu stdin đóng) hoặc kẹt treo 900s timeout (nếu stdin không nhận được EOF).
- **Quy tắc fix chuẩn:** `run_post.py` phải kiểm tra `if sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():` và bọc `try/except (EOFError, OSError)`:
  ```python
  confirmation = "YES"
  if sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
      try:
          confirmation = input("> ").strip()
      except (EOFError, OSError):
          confirmation = "YES"
  if confirmation != "YES":
      print("Aborted.")
      return 0
  ```

## 2. Bắt buộc kiểm tra Live VPN (`require_android_vpn`)
- **Vị trí tích hợp:** State `RESOLVE_DEVICE` trong `state_machine.py`.
- **Hành vi:** Kiểm tra trạng thái VPN qua interface/tun của `automation_core`. Nếu VPN ngắt kết nối hoặc mất IP proxy sạch, hệ thống fail-closed ngay (`VPN_REQUIRED_NOT_CONNECTED`).
- **Xử lý:** Tuyệt đối không bypass VPN hay mở TikTok khi chưa kết nối lại VPN trên thiết bị.

## 3. Quy trình theo dõi tiến độ Batch Upload song song (16 workers)
- Batch upload chạy theo đợt song song (mặc định 16 workers, giãn cách 2000-8000ms).
- Khi kiểm tra tiến độ, KHÔNG vội kết luận toàn bộ farm fail nếu thấy số máy success ban đầu còn ít.
- Phải đọc trực tiếp file workbook `TikN.xlsx` (cột `Video Đã Đăng`) và phân loại rõ ràng 5 nhóm:
  1. **Thành công:** `Video Đã Đăng` tăng lên (ví dụ từ 1 lên 2), có log `Post verification passed`.
  2. **Đang xử lý trong hàng đợi:** Tiến trình đang thực hiện các state UI (Open TikTok, Pick Video, Fill Caption, Post).
  3. **Lỗi VPN / Mất proxy:** Bị chặn tại preflight `VPN_REQUIRED_NOT_CONNECTED`.
  4. **Lỗi trống ID TikTok:** Cột `ID` trên workbook bị bỏ trống (`Missing required fields: ID TikTok`).
  5. **Lỗi thiết bị Offline:** Serial ADB không phản hồi (`DEVICE_OFFLINE`).

## 4. Xử lý Stale Media Fingerprint Ledger (`MEDIA_FINGERPRINT_PENDING`)
- **Triệu chứng:** Máy bị dừng ở checkpoint `MANUAL_REVIEW` với lỗi:
  `[MEDIA_FINGERPRINT] [MEDIA_FINGERPRINT_PENDING] Exact media SHA-256 has unresolved ledger status=reserved`
- **Nguyên nhân:** Lần chạy trước bị ngắt đột ngột sau khi đã băm SHA-256 video, khiến file ledger JSON lưu trạng thái `"status": "reserved"` vĩnh viễn.
- **Xử lý:**
  1. Vào thư mục: `D:\CodexRuntime\tiktok-video\idempotency\media-fingerprints\`
  2. Tìm file JSON có chứa SHA-256 hoặc machine/account tương ứng.
  3. Xóa (unlink) file JSON kẹt đó để giải phóng ledger, sau đó chạy lại target.

## 5. Đối soát & Bù ID TikTok thiếu (`MISSING_ID` / `None`)
- **Triệu chứng:** Machine inventory hoặc preflight văng `Missing required fields: ID TikTok`.
- **Xử lý:**
  1. Mở file `TikN.xlsx`, lấy số máy và `Folder Video`.
  2. Tra cứu đối chiếu trong file master `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` theo đúng cặp `(Máy, Folder Video)`.
  3. Điền giá trị `ID` TikTok tìm được vào `TikN.xlsx`, sửa cột `Kiểm Tra Dữ Liệu` thành `OK` và lưu lại.

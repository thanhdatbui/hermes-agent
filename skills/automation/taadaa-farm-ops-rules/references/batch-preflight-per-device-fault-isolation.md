# Batch Preflight Per-Device Fault Isolation (Cô Lập Lỗi Từng Máy Trong Batch Preflight)

## 1. Nguyên Tắc Cốt Lõi (User Directive)
> *"Lần sau sai máy nào thì bỏ qua máy đó, mắc gì dừng hết cả farm!"*

Trong mọi tác vụ batch đa máy trên Phone Farm (Reg Gmail, Reg TikTok, Feed session, Follow, Add 2FA, GPM login...):
- **CẤM TUYỆT ĐỐI FAIL-CLOSED TOÀN FARM:** Cấm ném `RuntimeError` hoặc crash toàn bộ tiến trình launcher chỉ vì 1 thiết bị gặp lỗi cấu hình (ví dụ: gõ nhầm serial khác, xung đột mapping, date marker lệch, thiếu proxy). Việc dừng toàn bộ batch làm tê liệt 79 máy bình thường khác là vi phạm nghiêm trọng kỷ luật vận hành.
- **Cơ chế Isolate & Skip (Cô lập & Bỏ qua):**
  - Khi quét inventory / device map / proxy map: Nếu phát hiện máy X có lỗi dữ liệu hoặc xung đột serial:
    1. Ghi log cảnh báo rõ ràng: `[warn] Máy {stt}: <chi tiết lỗi> -> bỏ qua máy này để bảo vệ cả farm`.
    2. Loại riêng máy X ra khỏi `device_map` / danh sách thực thi của phiên (`if stt not in conflicts`).
    3. Giữ nguyên toàn bộ các máy hợp lệ còn lại.
  - Tiến trình launcher tiếp tục chạy trên các máy hợp lệ (ví dụ: 79/80 máy).
- **Ngưỡng dừng khẩn cấp:** CHỈ dừng launcher khi sau khi lọc toàn bộ farm không còn bất kỳ máy nào hợp lệ (`len(valid_machines) == 0`).

## 2. Điển Cố Hiện Trường: Lỗi Reg Gmail 24/09/2026
- **Hiện tượng:** Watchdog chuỗi sau ca trưa báo: `Phase 1 (Reg Gmail - Code 1): LỖI KHỞI ĐỘNG RUNNER (Tổng máy: 0, Success: 0, Fail: 0)`.
- **Nguyên nhân:** Hàm `load_device_map_from_excel()` trong `gmail_reg_v10.py` ném `RuntimeError("Device map has conflicting valid serials for machine(s): 62")` vì hàng STT 491 của Máy 62 trong `taikhoan_dat_v2_updated .xlsx` bị dán nhầm serial `ce04...` thay vì `ce12...`.
- **Hậu quả:** Toàn bộ 80 máy bị dừng oan ở vòng preflight PowerShell, 0 máy nào được chạy.
- **Cách khắc phục chuẩn:**
  1. Dữ liệu: Sửa lại ô serial bị gõ nhầm trong Excel nguồn và sync sang `taikhoan_run_safe.xlsx`.
  2. Kiến trúc code: Bọc bỏ qua máy bị xung đột serial, nạp các máy còn lại, chỉ reject riêng máy đó ở cấp độ task runner.

# Farm Alert Triage & Codebase Fix Policy (ALL Farm Automation)

## 1. Bản Chất Của Farm Alert `[MÁY N]`
- Khi có cảnh báo `🚨 [MÁY N] DỪNG PHIÊN`: Đây là **báo cáo lỗi kịch bản/codebase**, không phải yêu cầu thợ bấm tay ADB chữa cháy tạm thời.
- Farm vận hành **80–160 máy tự động 24/7**. Nếu chỉ dùng lệnh ADB sửa trên 1 máy, tất cả các máy khác khi gặp cùng tình huống ở các ca sau sẽ tiếp tục crash và dừng phiên.
- **Mục tiêu bắt buộc:** Điều tra nguyên nhân gốc rễ trong script ➔ Vá logic tự phục hồi (auto-recovery) vào codebase ➔ Chạy test xác minh ➔ Commit/Push để toàn bộ 80-160 máy tự chạy mượt mà.

---

## 2. Quy Trình 4 Bước Chuẩn Khi Nhận Alert

### Bước 1: Trích xuất hiện trường nhanh (<1 giây)
- **Lệnh duy nhất:** `python D:/Taadaa/tools/inspect_machine.py <N>`
- Trả về ngay: Serial, danh sách nick, log run mới nhất (`summary.txt`, 20 dòng cuối `log.jsonl`), trạng thái focus/keyguard hiện tại và ảnh chụp live.
- **CẤM TUYỆT ĐỐI:**
  + CẤM chạy `os.walk`, `glob(recursive=True)`, `find` quét ổ đĩa tìm log.
  + CẤM chạy `grep -rn`, `search_files` lùng sục chuỗi lỗi (vd: `focus lost`, `stuck`) trong cả codebase `python_runner`.

### Bước 2: Điều tra Logic Script (Root Cause Analysis)
- Đọc đúng file flow quản lý bước kẹt (ví dụ `feed_swipe_smoke.py`, `device_prepare.py`, `benign_popup.py`).
- Xác định tại sao script lại crash hoặc dừng phiên thay vì tự xử lý:
  + Ví dụ: Launcher / Keyguard xuất hiện ➔ Script thiếu lớp tự động `keyevent 224` (wake) + `keyevent 82` (unlock) + relaunch TikTok.
  + Ví dụ: Popup quyền/quảng cáo mới ➔ Script thiếu rule trong `benign_popup_registry.py`.

### Bước 3: Sửa Codebase & Thêm Test
- Dispatch worker (`delegate_task`) viết hàm tự phục hồi trong script.
- Viết focused unit test trong `tests/` để test logic mới.
- Chạy focused test (<30s) đảm bảo pass 100%.

### Bước 4: Test Thực Tế & Đóng Gate
- Chạy Canary test trên đúng máy bị lỗi (chỉ test đúng đoạn logic vừa vá, không chạy lặp từ đầu).
- Gửi diff qua Plan-Review audit ➔ Commit & Push đồng bộ toàn farm.

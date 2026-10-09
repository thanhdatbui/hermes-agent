# Pitfall & Quy Trình: Xử Lý Lệnh "Fix Đi" Khi Nhận Báo Cáo Ca Nuôi Acc Bị Lỗi

## 1. Bối Cảnh Lỗi Thực Tế (Sự Cố 21/09/2026 - Ca 1 Row 1)
- Watchdog báo cáo Ca 1 Phiên 1 có 46 máy Kibe và 80 máy Admin bị Fail.
- User phát lệnh: `Fix đi`.
- **Sai lầm Coordinator:**
  1. Chỉ tập trung mổ xẻ code (code-surgery), vá 3 lỗi (`detect_quick_security_popup`, `_looks_like_user_placeholder`, remote ADB socket cho cụm Admin) rồi commit và dừng lại báo: *"Các phiên chạy tiếp theo sẽ tự động nhận diện..."*.
  2. Khi user hỏi `?`, Coordinator tự suy diễn sang Gate 6 Visual Evidence, chạy Canary 1 máy rồi gửi ảnh screencap.
  3. User phản ứng `?!!` vì máy farm của cả ca vẫn đang bỏ dở, chưa được chạy bù (re-run / resume partial fail).

## 2. Quy Tắc 2 Tầng Bắt Buộc Khi Nhận "Fix Đi" Sau Farm Alert / Báo Cáo Ca
Khi nhận lệnh `Fix đi` từ báo cáo ca nuôi acc:
1. **TẦNG 1: CODE SURGERY (Sửa lỗi gốc rễ):**
   - Sửa code trong `python_runner` hoặc `automation-core`.
   - Chạy pytest focused < 30s xác nhận pass 100%.
   - Commit git rõ ràng.
2. **TẦNG 2: RE-RUN / RESUME TRIAGE (Xử lý mẻ dở dang):**
   - Không được tự tiện kết luận "chờ ca sau tự chạy".
   - Kiểm tra ngay thời gian hiện tại trong Ca: Nếu còn trong khung giờ Ca (ví dụ Ca 1: 06:00 - 12:00) hoặc giữa các phiên:
     + Lập danh sách các máy fail do lỗi script vừa fix (loại trừ máy mất mạng/proxy die).
     + Đưa ra 2 lựa chọn rõ ràng hoặc hỏi user: Chạy bù ngay (targeted resume cho danh sách máy fail) hay để cron tự động chạy ở Phiên 2 / Ca kế tiếp.
   - Khi user nhắn `?` hoặc `?!!`: DỪNG MỌI HÀNH ĐỘNG TỰ SUY DIỄN, hỏi thẳng vào trọng tâm nhu cầu vận hành (re-run bù hay can thiệp cụ thể máy nào).

## 3. Bản Vá Kỹ Thuật Đã Ghi Nhận (Case 179 & Quick Security Unlabeled X)
- **Popup Mẹo Bảo Mật TikTok ("Hãy cùng kiểm tra bảo mật nhanh nhé"):**
  - Nút đóng X ở góc trên phải modal (`bounds [936,866][1056,998]`) có `text=""` và `content-desc=""`.
  - `detect_quick_security_popup` phải có fallback nhận diện nút clickable rỗng nhãn ở góc trên phải (`x1 >= 800`, width/height <= 200px) để dismiss thay vì coi là verify-dialog.
- **Remote ADB Host Cụm Admin (192.168.110.119):**
  - Tự động fallback sang `C:\Program Files (x86)\xiaowei\tools\adb.exe` khi cron subshell thiếu PATH `adb`.
  - Endpoint ATX HTTP JSON-RPC phải resolve host remote (`192.168.110.119`) thay vì mặc định `127.0.0.1`.

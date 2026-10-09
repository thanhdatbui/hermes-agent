# Cạm bẫy thiết kế: Tránh Over-engineering Cohort/Picker/Manifest & Giữ Dispatch Tối giản

## 1. Bối cảnh & Bài học xương máu (10/09 - 11/09/2026)
Hệ thống nuôi tài khoản TikTok từng bị tái phát bệnh over-engineering nghiêm trọng:
- Thay vì cứ đến giờ thì trích xuất Row tương ứng từ `taikhoan_run_safe.xlsx` và dispatch thẳng qua `run-feed-session.ps1`, một số subagent đã tự ý chế thêm cả một cụm: `picker.py` -> `staging.py` -> sinh `manifest.json` -> `cohort.py` -> `cohort_watchdog.py`.
- **Hậu quả trực tiếp:**
  1. Hàm validation trong `cohort.py` chặn cứng `block not in (1, 2, 3)`. Khi trang trại mở rộng lên 4 Ca/ngày (thêm Ca 4 / Row 8 lúc 00:00), validation ném `ValueError`, toàn bộ runner dừng hoạt động, cả 80 máy đứng im ("all máy pause").
  2. Bị deadlock và timeout hàng loạt khi cố debug / giải quyết mớ z-layer phức tạp.
  3. Cắt đứt hoàn toàn các hook phụ thuộc ngầm: ví dụ `upload_hook` bị phụ thuộc cứng vào `_effective_session_index(config) == 2` vốn chỉ được sinh từ `cohort_plan`. Khi gỡ bỏ cohort mà quên truyền lại flag session hoặc `--allow-upload-hook`, toàn bộ các ca feed chạy xong đều bị skip đăng video (`not-final-session` / `missing-session-identity`).

---

## 2. Nguyên tắc Bất biến: Tối giản hóa Schedule & Dispatch
1. **Trực tiếp từ Excel (Source of Truth):**
   - Giờ nào nuôi ca nào thì tính toán thẳng ra Row:
     - Ngày chẵn: 00h -> Row 8, 06h -> Row 2, 12h -> Row 4, 18h -> Row 6.
     - Ngày lẻ: 00h -> Row 7, 06h -> Row 1, 12h -> Row 3, 18h -> Row 5.
   - Không qua bất kỳ file manifest trung gian hay thuật toán phân bổ cohort phức tạp nào.
2. **Khung giờ không cross-midnight:**
   - Quy ước 00:00 là slot ca đêm mở đầu ngày mới, dùng trực tiếp `day % 2` của ngày đó để xác định tính chẵn/lẻ. Không tính bù trừ `(day - 1)` gây nhầm lẫn logic.
   - Dead zone: từ 01:00 đến 05:59 (không dispatch).

---

## 3. Cạm bẫy Gating Hook khi Refactor Dispatch (Upload & Follow)
Khi refactor hoặc đơn giản hóa launcher:
- **Upload Hook Gating:** Kiểm tra trong flow `multi_machine_feed_session.py`. Nếu hàm `_run_upload_hook()` kiểm tra `session_index == 2` hoặc `session_index == 3`, script gọi cấp cao (`run-feed-session.ps1` hoặc `run_tiktok.py`) **bắt buộc** phải truyền tham số tương ứng (hoặc thêm cờ rõ ràng như `--allow-upload-hook` / `--session-index 2`). Nếu không truyền, feed vẫn thành công nhưng không máy nào đăng video.
- **Watchdog Mismatch:** Watchdog (`feed_session_watchdog.py`) phải có định nghĩa các cửa sổ phiên (`SESSION_WINDOWS`) khớp 100% với số lần và khung giờ dispatch thực tế của runner. Nếu runner chỉ spawn 1 lần/ca mà watchdog lại đợi 2 phiên riêng biệt (Phiên 1 lướt, Phiên 2 đăng video), watchdog sẽ bị câm hoặc báo thiếu phiên.

---

## 4. Quy tắc Đồng bộ Cấu hình giữa Kibe và Admin
- Khi sao chép hoặc hỗ trợ cấu hình máy `admin` từ `kibe`:
  - Tuyệt đối không đưa file `.bat` thủ công bắt user tự làm nếu agent có thể điều khiển trực tiếp hoặc xuất lệnh cấu hình chuẩn qua hermes cron / config.
  - Cấu hình cron job của admin phải ánh xạ đúng đường dẫn tuyệt đối:
    - Host config: `D:\Taadaa\machine-config\admin.yaml`
    - Runtime: `D:\Taadaa\runtime\admin\...`
    - Workbook: `D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx`
    - Target Telegram Deliver: Giữ đúng channel/chat ID được yêu cầu.

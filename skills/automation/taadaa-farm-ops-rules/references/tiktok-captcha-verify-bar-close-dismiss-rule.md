# TikTok Captcha Puzzle Close Button & Verify-Bar-Close Invariant

## 1. Triệu chứng & Nguyên nhân
- Khi lướt Feed hoặc thực hiện luồng tự động, xuất hiện WebView Captcha ("Xác minh để tiếp tục:").
- Trên màn hình xuất hiện nút tắt X ở góc trên bên phải khung captcha:
  ```xml
  <node class="android.widget.Button" resource-id="verify-bar-close" bounds="[867,559][972,664]" clickable="true" />
  ```
- **Lỗi code cũ**: `_find_captcha_puzzle_close_x` trong `automation-core/src/automation_core/tiktok/benign_popup.py` trước đây đặt `exclude_resource_ids = ("verify-bar-close",)` cứng. Code sợ bấm nhầm thanh banner trải dài từ thời cũ, dẫn đến bỏ qua không bấm nút X này, làm hệ thống tưởng captcha không tắt được rồi dừng phiên (`manual-needed:manual_challenge`).

## 2. Invariant Quy tắc Xử lý `verify-bar-close`
Không bao giờ loại trừ mù quáng (blanket exclude) `verify-bar-close`:
- **Thanh banner (Exclude)**: Nếu `verify-bar-close` trải dài toàn màn hình (`width >= 0.5 * right_max`), ví dụ `bounds="[0,0][1080,120]"`, thì ĐÂY LÀ BANNER, cần bỏ qua không bấm.
- **Nút X đóng Captcha (Cho phép bấm)**: Nếu `verify-bar-close` có kích thước nhỏ gọn (`width < 0.5 * right_max`) và nằm ở vùng góc trên bên phải (`in_top_right`, tọa độ x >= 0.55 * right_max, y <= 0.45 * bottom_max), thì ĐÂY CHÍNH LÀ NÚT TẮT CAPTCHA, BẮT BUỘC bấm tắt để giải phóng popup tiếp tục nuôi feed.

## 3. Log Triage Không Đòi Code Của User
- Mọi dữ liệu phiên chạy nuôi feed đều được ghi đầy đủ tại `D:/Taadaa/runtime/kibe/live/YYYY-MM-DD/row-X-HHMMSS/` hoặc `D:/Taadaa/tiktok-luot nuoi acc/.ai-runs/`.
- Coordinator/Agent BẮT BUỘC tự tra cứu trực tiếp O(1) qua cấu trúc thư mục runtime của phiên gần nhất để đọc `log.jsonl`, `summary.txt` và `ui.xml`.
- TUYỆT ĐỐI KHÔNG hỏi xin user code hoặc script khi hệ thống đã lưu sẵn log trên host.

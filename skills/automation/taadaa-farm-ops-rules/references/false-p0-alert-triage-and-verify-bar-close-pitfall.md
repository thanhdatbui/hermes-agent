# Triệt Tiêu False P0 Alert Khi Phân Loại Lỗi Farm & Tự Động Tra Cứu Log

## 1. Bài Học Xương Máu Về Điều Phối & Không Được Hỏi Lại User (User Correction)
- **Sự cố:** Khi user bảo "Fix đi" hoặc "có log là dính cái gì k", Coordinator đã vô thức hỏi xin lại user file/code/đường dẫn script ("Gửi giúp tôi đường dẫn repo hoặc tên script..."), khiến user ức chế nghiêm trọng vì:
  1. Toàn bộ thông tin repo (`D:/Taadaa/tiktok-luot nuoi acc`, `D:/Taadaa/automation-core`) đã hiển thị rõ trong context ngay từ đầu turn.
  2. Runner nuôi acc luôn lưu log chi tiết từng phiên tại `D:/Taadaa/runtime/kibe/live/<date>/<session>/machines/machine_<N>/<timestamp>/` (`summary.txt`, `log.jsonl`, `artifacts/...`).
- **Quy tắc bất biến:**
  - **TỰ TÌM TRONG RUNTIME VÀ LOG CỦA MÁY:** Khi user hỏi về log của ca nuôi, BẮT BUỘC tự kiểm tra `D:/Taadaa/runtime/kibe/live/` theo ngày và số máy, mở `summary.txt`, `log.jsonl` hoặc `ui.xml` tương ứng. TUYỆT ĐỐI CẤM hỏi user "code/log lưu ở đâu".
  - **TỰ DISPATCH HOẶC FIX ĐÚNG REPO:** Khi đã định vị được bug trong `automation-core`, trực tiếp dispatch worker hoặc lập Patch Contract xử lý ngay.

---

## 2. Bản Chất Lỗi False P0 Alert (Mất Phiên Giả)
- **Triệu chứng:** Telegram hú còi:
  `🚨 [BATCH ALERT: LỖI HỆ THỐNG] P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT: Phát hiện 1 máy dính lỗi login/mất phiên: Máy M35: manual_challenge marker detected`.
- **Nguyên nhân gốc rễ (Root Cause):**
  - Runner của `tiktok-luot nuoi acc` phân loại mọi lỗi thuộc nhóm auth/challenge thành blocker chung: `blocker_type = "login-gms-verification"`.
  - Trong `automation-core/src/automation_core/batch_aggregator.py`:
    ```python
    # CODE CŨ (SAI):
    session_lost_failures = [
        m for m in failed
        if any(kw in f"{m.error_type or ''} {m.error_message or ''}".lower() for kw in SESSION_LOST_KEYWORDS)
    ]
    ```
    Chuỗi ghép chứa từ `"login"` trong `error_type` ("login-gms-verification"), dù `error_message` là `"manual_challenge marker detected"` (chỉ là captcha/thử thách tạm thời), dẫn tới máy bị phân loại nhầm vào `session_lost_failures` và kích hoạt P0 mất phiên.
- **Cách khắc phục:**
  - Ưu tiên kiểm tra `CHALLENGE_KEYWORDS` trước (trên `error_message` hoặc `error_type` thuần challenge, loại trừ blocker type gộp `"login-gms-verification"`).
  - Chỉ xếp vào `session_lost_failures` khi message hoặc error_type thực sự khớp từ khóa mất phiên thật (`logged out`, `văng`, `session expired`, `login screen`...).

---

## 3. Pitfall Cấm Bấm Nút X Captcha `verify-bar-close`
- **Hiện tượng:** Màn hình hiện WebView captcha ghép hình TikTok (`verify captcha`):
  ```xml
  <node class="android.webkit.WebView" text="verify captcha" bounds="[108,559][972,1432]" />
  <node class="android.widget.Button" resource-id="verify-bar-close" bounds="[867,559][972,664]" />
  ```
- **Pitfall trong code:**
  - Trong `automation-core/src/automation_core/tiktok/benign_popup.py`: hàm `_find_captcha_puzzle_close_x` có tham số:
    `exclude_resource_ids: tuple[str, ...] = ("verify-bar-close",)`
  - Do lịch sử cũ sợ `verify-bar-close` là thanh banner không tắt được captcha, code đã loại trừ nó. Nhưng trên thực tế của TikTok S7, chính nút `X` góc trên bên phải của WebView captcha lại mang ID `verify-bar-close`.
  - Hậu quả: Script tìm không ra nút đóng nào khác -> coi captcha là unrecoverable -> dừng ca nuôi với lỗi `manual-needed:manual_challenge`.
- **Giải pháp:** Nếu WebView captcha có nút `verify-bar-close` nằm ở góc trên bên phải (`in_top_right(element)`), không được loại trừ mù quáng mà phải cho phép chạm để đóng thử thách tạm thời.

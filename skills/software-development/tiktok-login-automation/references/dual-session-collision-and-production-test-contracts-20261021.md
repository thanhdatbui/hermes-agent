# Dual-Session Collision, Lock Contention & Production-Test Contracts (2026-10-21)

## 1. Hiện Tượng & Nguyên Nhân Va Chạm 2 Session
- **Bối cảnh:** Cùng một sự cố farm (ví dụ: M24 kẹt Account Switcher) được phát đi qua 2 kênh:
  1. Kênh khẩn cấp `🚨 [BATCH ALERT: LỖI HỆ THỐNG]` (P0 alert).
  2. Kênh định kỳ `tiktok-feed-session-watchdog` (báo cáo tổng kết ca).
- **Hệ quả va chạm:**
  - Cả 2 session Coordinator độc lập cùng nhảy vào xử lý Máy 24.
  - **Tranh chấp device lock:** Tiến trình login `tiktok_login_v1.py 24` của session này liên tục đụng `device lock active (machine_24.lock.json)` của PID từ session kia (hoặc `do_rename_canonical_runner.py`).
  - **Phân mảnh commit Git:** Cả 2 session cùng tạo các commit sửa `social_reg_v1.py` và `tiktok_login_v1.py`.
- **Kỷ luật giải quyết va chạm:**
  - Không hoảng loạn revert hay ép reset thô bạo.
  - Rà soát `git log origin/main..HEAD` và `git diff origin/main..HEAD -w` để bóc tách:
    + Session 1 vá: `_tiktok_login_modal_present` (loại trừ Settings) và `upsert_tracking_account` (chấp nhận re-read khớp).
    + Session 2 vá: `_profile_tab_node` (ngưỡng cy >= 1780 tránh đĩa nhạc), `wait_login_success` (timeout 75s), `drive_login_screens` (đệm chờ xác thực mật khẩu 4G proxy), `dismiss_profile_overlays` (đóng overlay bình luận).
    + Hai tập vá hoàn toàn bổ trợ, không conflict logic. Sau đó gộp (squash/rebase) thành 1 commit O(1) duy nhất trước khi đưa vào Closeout Gate.

---

## 2. Kỷ Luật Viết Test Production Cho Closeout Gate (Sol Reviewer Strike 1 & 2)

Reviewer Sol High chấm điểm rất khắt khe về **Test Evidence**. Dưới đây là các bẫy chết người và cách khắc phục chuẩn mực:

### Bẫy 1: Duplicate Predicate Trong Test Thay Vì Gọi Hàm Thật
- **Lỗi:** Test tự viết `verify_re_read(...)` hoặc tự tính `safe_y = y1 + max(...)` rồi assert.
- **Reviewer đánh giá:** Test chỉ mô phỏng lại công thức toán học, không chứng minh được code production chạy đúng -> Trừ nặng điểm (72/100).
- **Khắc phục:** Gọi trực tiếp `social.tap_add_account("emulator-5554")`, monkeypatch `get_ui_xml` và `tap`, rồi assert tọa độ tap thực tế được sinh ra.

### Bẫy 2: `os.fsync` Và `io.BytesIO` Không Có File Descriptor
- **Lỗi:** Khi test `upsert_tracking_account`, dùng `io.BytesIO` để chứa workbook giả lập. Hàm production gọi `os.fsync(locked_file.fileno())` dẫn tới crash `AttributeError: 'BytesIO' object has no attribute 'fileno'` -> hàm rơi vào block except và lưu vào `tracking_pending.csv`, trả về `None`.
- **Khắc phục:** Dùng fixture `tmp_path / "tracking.xlsx"` của pytest, mở file bằng `open(tracking_file, "r+b")`. File nhị phân thật trên đĩa có `fileno()` hợp lệ, cho phép `os.fsync` chạy mượt mà.

### Bẫy 3: Phục Hồi Trường Password Bằng Hint Tiếng Việt (`Nhập mật khẩu`)
- **Lỗi:** Hàm `wait_for_edittext` có thể miss node password khi ATX dump chậm. Fallback tìm node dựa vào `n.get("password")` hoặc `hint`. Tuy nhiên, node EditText của TikTok có thể để chuỗi `"Nhập mật khẩu"` trong thuộc tính `text` hoặc `hint`, và có dấu tiếng Việt.
- **Khắc phục:**
  1. Trong `list_edittext_nodes`, trích xuất thêm trường `"hint": attrs.get("hint", "")`.
  2. Trong `fill_password_and_login`, dùng `strip_accents(n.get("hint") or n.get("text") or "").lower()` để đối soát với danh sách `["mat khau", "password"]`.

### Bẫy 4: ADB Command Treo Trong Test Offline (`wait_login_success`)
- **Lỗi:** `wait_login_success` gọi `shell(device_id, "dumpsys", "activity", "activities")` để kiểm tra foreground app. Trong môi trường unit test không có thiết bị thật, lệnh `shell` sẽ bị timeout (20s) hoặc ném `RuntimeError`.
- **Khắc phục:** BẮT BUỘC monkeypatch `social.shell = lambda *a, **k: "com.ss.android.ugc.trill"`, `save_ui_xml`, `screenshot` và time-generator trước khi gọi `wait_login_success`. Kiểm tra đủ cả 2 nhánh:
  1. Nhánh thành công ngay khi UI có marker Home Feed (`_is_home_feed_xml(xml) is True`).
  2. Nhánh hết hạn timeout 75s trả về `False` khi UI không xuất hiện success hint.

---

## 3. Strike 3 Reviewer Hand-Off & 50-Test Production Expansion (Grace Band 82 APPROVED)

Khi Closeout Gate trượt 3 lần liên tiếp trên cùng một `scope_hash` (Strike 1 & Strike 2 Sol Repair tạo patch chưa đủ điểm, ví dụ 78 và 79/100):
- **Cơ chế kích hoạt:** Closeout Gate phát cờ `[REVIEWER_HANDOFF_TRIGGERED]`. Coordinator và Sol Repair BẮT BUỘC dừng việc đoán mò/tự sửa và chuyển giao ngay cho Reviewer CLI (`claude_worker.py --role worker` với `claude-haiku-5-5`, hoặc fallback `ag_cli.py fix`).
- **Nâng cấp Test Suite toàn diện (50 Tests):**
  Claude Worker mở rộng file test từ 10 tests đơn vị lên 50 tests tích hợp đầy đủ:
  1. *Cô lập side effect (Autouse Fixture):* Redirect `PROJECT_ROOT` sang `tmp_path`, mock logging, `hide_keyboard`, backup tracking để không làm vấy bẩn file `tracking_pending.csv` trong working tree.
  2. *Kiểm tra các biến thể tham số (Parametrize):* Test `fill_password_retypes_only_when_revealed_value_mismatches` với chuỗi mật khẩu thật, mask bullet `•••••••••••••`, chuỗi rỗng và chuỗi sai; test `wait_login_success` với 6 trạng thái manual auth (`captcha`, `google_relogin`, `identity_verification`, `terms_consent`, `account_not_found`, `rate_limited`).
  3. *Kiểm chứng các bất biến của Tracking Workbook:* Insert slot mới sau block máy, tái sử dụng slot trống (empty slot reuse), cập nhật hàng cũ với so khớp email không phân biệt hoa thường, từ chối duplicate TikTok ID và từ chối slot thứ 9 vượt trần 8 nick.
- **Kết quả nghiệm thu:**
  - `50 passed in 2.0s`.
  - Sol Reviewer chấm **82/100 (APPROVED)** trong khung Grace Band 80–84 điểm.
  - Lệnh `python D:/Taadaa/tools/safe_push.py D:/Taadaa/Tiktok_Reg origin main` xác nhận bản ghi audit trong `gate_audit.jsonl` và push thành công lên GitHub remote.

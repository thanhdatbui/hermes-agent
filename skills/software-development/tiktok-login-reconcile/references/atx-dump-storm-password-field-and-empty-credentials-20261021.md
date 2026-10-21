# Bẫy Atx-Agent Wedge Do Dump Dồn Dập Màn Password & Cứu Hộ Credentials Trống (2026-10-21)

## 1. Triệu chứng sự cố
Khi chạy `tiktok_login_v1.py <STT> --email <ID>` để nạp bù nick vào Switcher:
- App đã mở đến màn "Nhập mật khẩu" (`com.ss.android.ugc.trill:id/f8t`).
- Script đã nhận diện `email DA CO tai khoan TikTok (password field)` và ghi nhận `detect_after_continue=registered`.
- Nhưng bước `[8] Fill password` bị crash với lỗi:
  ```
  [ui-xml] atx-agent dump attempt 1/3 failed on <serial>, retry in 0.3s...
  [ui-xml] atx-agent dump exhausted (3/3 attempts + reset) on <serial> - refusing unsafe shell uiautomator dump
  STOPPED: [08] Không tìm thấy EditText password
  ```

## 2. Nguyên nhân kỹ thuật kép

### A. Vòng lặp dump XML dồn dập (Dump Storm) làm treo ATX
Trong `social_reg_v1.py` (hàm `fill_password_and_login`):
1. Vòng lặp `while time.time() < deadline:` gọi `xml_pw_check = get_ui_xml(device_id)` -> dump lần 1 thành công, phát hiện màn mật khẩu.
2. Ngay sau đó gọi `save_ui_xml(device_id, ...)` -> hàm này lại gọi `get_ui_xml()` dump lần 2.
3. Tiếp tục gọi `wait_for_edittext(device_id, ...)` -> lại gọi `get_ui_xml()` dump lần 3.
Trên các dòng máy yếu như Samsung S7 Android 8, việc gọi `dumpWindowHierarchy` liên tiếp 3 lần trong 1-2 giây khiến ATX-agent socket hoặc Accessibility Service bị treo (`futex_wait_queue_me`), trả về XML rỗng. `wait_for_edittext` nhận XML rỗng và timeout văng `RuntimeError`.

### B. Thiếu Pass & Email trong Workbook Master
Nick `@trinhgiang7694` (máy 24, Row 192) đã đăng ký trước đó và đã có secret 2FA trong cột E, nhưng cột D (PASS) và cột F (Email) bị bỏ trống trong `taikhoan_dat_v2_updated .xlsx`.
- Hệ quả: `tiktok_login_v1` phân loại `usable=False`, khi bị ép gọi login thì thiếu pass để submit, kẹt màn đăng nhập và timeout 388s.

## 3. Khắc phục chuẩn O(1)

### A. Sửa code `fill_password_and_login()` trong `social_reg_v1.py`
1. Thay `save_ui_xml()` bằng `save_xml_blob(xml_pw_check)` để tái sử dụng XML đã dump trước đó.
2. Nếu `wait_for_edittext` trả về rỗng do ATX chập chờn, lập tức fallback sang `list_edittext_nodes(xml_pw_check)`.
3. Bổ sung fallback tọa độ an toàn cho Samsung S7 `{"coord": (495, 594), "x1": 138, "y1": 564, "x2": 852, "y2": 624, "rid": "", "password": True}`.

### B. Cứu hộ Credentials từ kết quả đăng ký cũ
Tra cứu file deferred tracking `D:/Taadaa/runtime/kibe/artifacts/runs/.../tracking_result_*.json` hoặc `social_reg_log.txt`:
- Lấy lại mật khẩu TikTok và email gốc (`JasmynQuines487694@hotmail.com`).
- Tạo backup `taikhoan_dat_v2_updated .xlsx.bak_*` và backfill vào dòng tương ứng, bảo toàn nguyên vẹn 2FA secret.
- Kiểm tra lại bằng `python D:/Taadaa/tools/excel_preflight_validator.py` đạt PASS 100%.

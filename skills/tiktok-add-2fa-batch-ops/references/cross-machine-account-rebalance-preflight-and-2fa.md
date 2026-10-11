# Điều Phối Nick Dư Giữa Các Máy & Quy Trình Bật 2FA Trước Khi Chuyển (11/10/2026)

## 1. Bối cảnh Tràn Trần 8 Nick trên thiết bị
- TikTok trên Android chỉ cho phép lưu tối đa 8 tài khoản trong Switcher.
- Khi máy bị dồn thừa nick (ví dụ máy 74 có 8 nick trong app nhưng cần đưa nick chính chủ khác vào), tài khoản trên máy KHÔNG PHẢI KÍ SINH mà là tài sản farm.
- Quy trình: chọn nick non nhất (reg gần nhất, ít video, ít fl) chuyển sang máy thiếu slot (< 8 nick, ví dụ M266 Admin).

## 2. Kỷ luật Bật 2FA & Đặt Pass trên máy nguồn trước khi chuyển
- **Invariant**: Tuyệt đối KHÔNG logout nick non ra khỏi máy nguồn khi chưa có mật khẩu và 2FA.
- **Thực thi Phase B**:
  - Chạy `run_capture_phase_b.py --live` trên máy nguồn (máy đang giữ phiên login của nick).
  - Tự động đặt mật khẩu đạt chuẩn và bật 2FA TOTP (Authenticator App), trích xuất Secret Key 32 ký tự.
  - Ghi nhận đầy đủ Mật khẩu + Secret Key vào workbook.
- **Ghi sổ trước, login sau**:
  - Cập nhật thông tin nick vào các file Excel của máy nhận (TikN.xlsx, taikhoan_run_safe.xlsx, taikhoan_dat_v2_updated .xlsx).
  - TUYỆT ĐỐI CHƯA vội login lên máy nhận cho đến khi có ca chạy hoặc chỉ đạo.
  - **BẮT BUỘC ĐĂNG XUẤT NGAY KHỎI MÁY NGUỒN ĐỂ NHÀ SLOT (Cấm nhảy cóc sang login nick mới)**:
    * Khi app TikTok trên máy đã đủ 8 nick, nút "Thêm tài khoản" (`Add account`) ở đáy Switcher bị **ẨN HOÀN TOÀN**.
    * Nếu chưa logout nick non mà đã vội chạy `tiktok_login_v1.py` nạp nick mới, script sẽ văng lỗi `UI_XML_TIMEOUT` / `Không thấy: ('Thêm tài khoản', 'Add account')` do không có cửa vào form đăng nhập.
    * Do đó, thứ tự bắt buộc: (1) Add 2FA & lưu pass -> (2) Logout dứt điểm nick non ra khỏi máy nguồn để máy về 7 slot -> (3) Mới tiến hành login nick đích.

## 3. Pitfalls Kỹ Thuật Khi Chạy Phase B Trên Nick Điều Chuyển
- **Lỗi `non_xml_ui_dump` do thiếu APK Stub UiAutomator trên máy yếu (S7/Android 7)**:
  * Khi `run_capture_phase_b.py` văng lỗi `{"status": "failed", "reason": "non_xml_ui_dump"}`, nguyên nhân do `atx-agent` (port 7912) không kết nối được stub JSON-RPC vì package `com.github.uiautomator` và `com.github.uiautomator.test` chưa được cài đặt hoặc bị disable ngầm trên thiết bị.
  * Kho APK chuẩn có sẵn tại: `C:\Users\Kibe\.GemPhoneFarm\app\app-uiautomator.apk` và `app-uiautomator-test.apk`.
  * Khắc phục nhanh:
    1. Đẩy APK lên máy:
       `adb -s <serial> push "C:/Users/Kibe/.GemPhoneFarm/app/app-uiautomator.apk" /data/local/tmp/`
       `adb -s <serial> push "C:/Users/Kibe/.GemPhoneFarm/app/app-uiautomator-test.apk" /data/local/tmp/`
    2. Cài đặt cấp quyền:
       `adb -s <serial> shell pm uninstall com.github.uiautomator` (nếu có dấu vết cũ)
       `adb -s <serial> shell pm uninstall com.github.uiautomator.test`
       `adb -s <serial> shell pm install -t -g /data/local/tmp/app-uiautomator.apk`
       `adb -s <serial> shell pm install -t -g /data/local/tmp/app-uiautomator-test.apk`
    3. Sau khi cài, `atx-agent` sẽ dump XML bình thường, không còn bị timeout hay trả XML rỗng.
- **Bẫy Mismatch Máy Trong Preflight Khi Chạy Cross-Machine (`identity_matches=False -> WorkbookError`)**:
  * Khi chạy Phase B trên máy nguồn (ví dụ M74) nhưng trỏ vào file Master của máy nhận (ví dụ Admin row 621, máy 266), hàm `inspect_target()` trong `core/workbook.py` đối soát cột `Máy`:
    `_clean(ws.cell(row, machine_col).value) == _clean(target.machine)`
  * Nếu dòng trong Excel đã ghi số máy nhận (266) trong khi runner gọi `--machine 74`, đối soát fail ngay (`266 != 74`), trả về `WorkbookPreflight(identity_matches=False)` và văng `WorkbookError`.
  * **Quy trình chuẩn**:
    - Cách 1: Chạy Phase B trên dòng của máy nguồn (Kibe row) trước để lấy pass + 2FA secret, sau đó mới đồng bộ bộ thông tin hoàn chỉnh sang dòng máy nhận (Admin row).
    - Cách 2: Nếu tạo dòng mới trên file máy nhận, tạm thời để cột `Máy` là số máy nguồn (74) trong lúc chạy `run_capture_phase_b.py --machine 74`, sau khi hoàn tất 2FA mới sửa lại thành số máy nhận (266).
- **Bẫy Stale 2FA Cell trong Workbook (`WorkbookPreflight has_2fa=True`)**:
  * Khi gán nick mới vào một dòng trên Master Excel (`taikhoan_dat_v2_updated .xlsx`), nếu ô cột 5 (`2FA`) hoặc cột 4 (`PASS`) vẫn còn lưu secret/pass của nick cũ trước đó, `inspect_target()` sẽ trả về `has_2fa=True`.
  * Hậu quả: `run_capture_phase_b.py` fail-closed ngay lập tức với `{"status": "failed", "reason": "WorkbookError"}`.
  * Khắc phục: Trước khi kích hoạt Phase B, bắt buộc clear sạch ô:
    ```python
    ws.cell(row, 4).value = None  # PASS
    ws.cell(row, 5).value = None  # 2FA
    ```
    Đảm bảo kiểm tra `WorkbookPreflight(identity_matches=True, has_2fa=False)` trước khi khởi chạy `--live`.
- **Bẫy Tên File Master Có Khoảng Trắng (`taikhoan_dat_v2_updated .xlsx`)**:
  * Chú ý file Master luôn có dấu cách trước phần mở rộng: `taikhoan_dat_v2_updated .xlsx`. Khi truyền qua bash terminal cần bọc nháy kép cẩn thận, tránh lỗi phân tách tham số hoặc regex guard.
- **Kỷ Luật Output Điều Phối (Cấm Rò Rỉ Gate Text)**:
  * Tuyệt đối không để text của các hook kiểm duyệt nội bộ (`[EVIDENCE FIRST GATE — FAIL-CLOSED VIOLATION]...`) xả thẳng vào output trả lời User trên Telegram. Báo cáo bằng chứng ngắn gọn, trung thực và tập trung vào kết quả thực tế.

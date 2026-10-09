# Khắc phục điểm nghẽn UI Gmail (03_add & 04_google), Bẫy Status Bar / SystemUI và PowerShell UTF-8 Encoding

Ngày cập nhật: 07/09/2026

## 1. Bối cảnh sự cố
Trong flow tự động hóa đăng ký Gmail trên farm máy Android (`D:\Taadaa\register gmail\gmail_reg_v10.py`), worker thường xuyên gặp lỗi tại 2 bước:
- `[03_add] Không mở được account switcher / Add another account`: Sau khi bấm avatar Gmail, không tìm thấy hoặc bấm trượt card "Thêm tài khoản khác".
- `[04_google] Không chọn được provider Google`: Đã mở danh sách provider nhưng không chọn được Google, hoặc màn hình bị che bởi popup cập nhật bảo mật.
Đồng thời, log tiếng Việt hiển thị ra console hoặc chuyển tiếp sang pipeline đêm (`run_night_chain_pipeline.py`) bị lỗi font (mojibake) do PowerShell `Get-Content` đọc sai encoding.

---

## 2. Các nguyên nhân gốc rễ & Giải pháp kỹ thuật

### 2.1. Bẫy SystemUI / Status Bar trong UI XML (`03_add`)
- **Triệu chứng:** Hàm tìm card bento / switcher `find_add_account_card_in_switcher` tìm nhầm một node ở góc trên cùng bên trái màn hình (`bounds=[12,0][66,71]`), dẫn đến tap vào thanh thông báo/Status bar thay vì card tài khoản.
- **Nguyên nhân:** Vòng lặp duyệt toàn bộ node XML không kiểm tra package của Gmail và không có cận dưới trục Y, khiến các node hệ thống (`com.android.systemui`) lọt vào danh sách fallback candidate.
- **Giải pháp:**
  - Khóa chặt package: `if attrs.get("package", "") != "com.google.android.gm": continue`.
  - Khóa cận Y an toàn: `if y < 300: continue` và chỉ chấp nhận card trong vùng hiển thị nội dung `300 <= y <= 1850`.

### 2.2. Nút "Thêm tài khoản khác" nằm dưới Fold (`03_add`)
- **Triệu chứng:** Danh sách tài khoản trong switcher dài (nhiều tài khoản hoặc màn hình độ phân giải thấp như S7 1080x1920), nút "Thêm tài khoản khác" bị ẩn dưới mép màn hình.
- **Giải pháp:** Trong `wait_and_tap_add_account_in_switcher`, nếu sau lần kiểm tra đầu tiên chưa thấy nút, thực hiện cuộn nhẹ một lần:
  ```python
  shell(device_id, "input", "swipe", "540", "1500", "540", "900", "300")
  ```

### 2.3. Popup cập nhật bảo mật che khuất danh sách Provider (`04_google`)
- **Triệu chứng:** Sau khi bấm Add account, màn hình hiện popup "Bản cập nhật bảo mật..." của Gmail che mất danh sách chọn nhà cung cấp dịch vụ email (Google, Outlook, Yahoo...).
- **Giải pháp:** Trong vòng lặp `tap_google_provider_entry`, luôn gọi `dismiss_gmail_security_update_popup(device_id, xml=xml)` để tự động phát hiện và đóng popup trước khi quét node provider Google.

### 2.4. Khắc phục Mojibake tiếng Việt (Unicode)
- **Trong script Python:**
  - Thay thế toàn bộ chuỗi lỗi mã hóa (ví dụ: `ThÃªm tÃ i khoáº£n khÃ¡c`, `KhÃ´ng má»Ÿ Ä‘Æ°á»£c`) bằng chuỗi tiếng Việt chuẩn UTF-8.
  - Hỗ trợ song song cả biến thể có dấu và không dấu: `"Them tai khoan khac"`, `"Thêm tài khoản khác"`, `"Add another account"`.
- **Trong PowerShell launcher (`run_parallel.ps1`):**
  - PowerShell 5.1 mặc định sử dụng ANSI/OEM codepage khi đọc file bằng `Get-Content`.
  - BẮT BUỘC chỉ định `-Encoding UTF8`:
    ```powershell
    $content = @(Get-Content -LiteralPath $LogPath -Encoding UTF8 -ErrorAction Stop)
    ```

### 2.5. Phân loại lỗi tinh gọn trong Pipeline Đêm (`run_night_chain_pipeline.py`)
- Khi worker gặp lỗi `04_google` hoặc lỗi chọn provider, pipeline cần gom nhóm chuẩn xác về `google provider error` thay vì để chuỗi lỗi dài hoặc bị coi là lỗi không xác định:
  ```python
  elif "04_google" in low or "provider" in low:
      clean_reason = "google provider error"
  ```

# Kỷ luật Encoding và Phân loại Mã lỗi (Error Categorization) trong Báo cáo Cron Farm

## 1. Bối cảnh & Sự cố thực tế (07/09/2026)
Trong báo cáo tự động của chuỗi đêm `night-chain-reg-pipeline` (job_id: `38ea60c09825`) gửi về Telegram, danh sách máy lỗi xuất hiện chuỗi ký tự vỡ font đầy dấu hỏi chấm:
`01, 02, 36, 47 ([04_google] Kh?ng ch?n ???c provider...);`
Gây phản ứng tiêu cực từ user ("Ngôn ngữ đéo gì v") do báo cáo khó hiểu, mất thẩm mỹ và không chỉ rõ được bản chất lỗi.

## 2. Phân tích 3 Tầng Nguyên nhân Gốc rễ

### Tầng 1: Vỡ chuỗi cứng ngay trong mã nguồn (Source Code Corruption)
- Khi các agent trước hoặc script tự động thực hiện thao tác sửa code/patch mà không bảo toàn encoding UTF-8 (hoặc dùng regex replace với fallback ASCII/errors='replace'), các ký tự tiếng Việt có dấu bị chuyển thành dấu hỏi cứng `?` ngay trong source code:
  ```python
  # Trong gmail_reg_v10.py (commit cũ b729e8d):
  raise RuntimeError("[04_google] Kh?ng ch?n ???c provider Google")
  ```
- Chuỗi exception này khi raise lên sẽ mang theo dấu hỏi `?` vĩnh viễn dù sau đó console/file có cấu hình UTF-8 thế nào đi nữa.

### Tầng 2: PowerShell 5.1 mặc định giải mã ANSI/OEM khi đọc Log
- Trong các script PowerShell điều phối song song (như `run_parallel.ps1`):
  ```powershell
  # SAI: Mặc định theo OEM code page (Windows-1252 / CP437)
  $content = @(Get-Content -LiteralPath $LogPath -ErrorAction Stop)

  # ĐÚNG: Ép buộc UTF-8 chuẩn
  $content = @(Get-Content -LiteralPath $LogPath -Encoding UTF8 -ErrorAction Stop)
  ```
- Khi thiếu `-Encoding UTF8`, `Get-Content` của Windows PowerShell đọc các log file UTF-8 (không có BOM) sinh ra từ Python và làm vỡ toàn bộ ký tự đa byte thành mojibake hoặc dấu hỏi trước khi ghi vào `summary.json`.

### Tầng 3: Thiếu bộ lọc phân loại lỗi (Error Categorization) trong Report Launcher
- Báo cáo cron cấp cao (`run_night_chain_pipeline.py`) nhận `reason` từ `summary.json` và in thẳng chuỗi thô ra tin nhắn Telegram nếu chuỗi đó không khớp với 3 bộ lọc cứng (`proxy timeout`, `phone verification`, `recaptcha`).
- Việc xả raw exception string / unhandled error messages lên kênh chat khiến báo cáo dài dòng, chứa rác kỹ thuật và dễ lộ lỗi format.

## 3. Quy chuẩn Khắc phục & Phòng ngừa (BẮT BUỘC)

1. **Kỷ luật Error Categorization trong Cron Launcher:**
   - Mọi failure reason trích xuất từ worker hoặc `summary.json` PHẢI đi qua hàm phân loại (classifier) để chuẩn hóa thành các nhãn lỗi ngắn gọn, sạch sẽ, viết thường hoặc viết hoa có quy củ.
   - Ví dụ:
     - `04_google` / `provider google` -> `google signin error` hoặc `provider error`
     - `account_creation_error` -> `account creation rejected`
     - `app_update_dismiss_button` -> `device update popup blocked`
   - Chỉ giữ fallback chuỗi thô khi độ dài ngắn và đã qua làm sạch dấu câu/ký tự lạ.

2. **Ép buộc `-Encoding UTF8` trong mọi script PowerShell đọc/ghi File:**
   - Luôn sử dụng `Get-Content ... -Encoding UTF8` và `Set-Content ... -Encoding UTF8`.
   - Trong Python, luôn mở file với `encoding="utf-8"`, và stdout launcher phải có `sys.stdout.reconfigure(encoding="utf-8")`.

3. **Cấm lưu chuỗi Unicode dạng hỏng vào Source Code:**
   - Trước khi commit bất kỳ thay đổi nào vào repo farm, agent phải kiểm tra diff để đảm bảo không đưa ký tự `?` thay thế vào các chuỗi log/exception tiếng Việt.

## 4. Ghi nhận Hiện trường Samsung S7 UI Tràn & Popup Chặn
- **Popup cập nhật hệ điều hành:** Gmail trên Samsung S7 (Android 8) xuất hiện popup *"Hãy cập nhật thiết bị để đảm bảo an toàn"* (`com.google.android.gm:id/app_update_dismiss_button`). Cần được auto-dismiss ở bước preflight/provider setup (`tap_google_provider_entry`).
- **Tràn Account Switcher Menu:** Khi máy đã có nhiều tài khoản hoặc xuất hiện card *"Cảnh báo bảo mật quan trọng"*, nút *"Thêm tài khoản khác"* bị tụt khỏi màn hình. Bắt buộc thực hiện thao tác cuộn nhẹ (swipe/scroll `540, 1500 -> 540, 900`) để bộc lộ nút thay vì click fallback ngay.
- **Cảnh giác Mojibake trong Text Matcher:** Khi từ khóa tìm kiếm bị lưu dưới dạng double-encoded UTF-8 (mojibake như `"ThÃªm tÃ i khoáº£n khÃ¡c"`), hàm strip-accents sẽ sinh chuỗi rác (`thãªm tãi...`) khiến regex/loose matcher thất bại hoàn toàn. Luôn định nghĩa cả 2 dạng: tiếng Việt chuẩn UTF-8 và không dấu ASCII (`"Thêm tài khoản khác"`, `"Them tai khoan khac"`).
- **Chống Lọt Node SystemUI (Package Leakage):** Khi tìm kiếm component theo tọa độ/bounds fallback trong `root.iter("node")`, bắt buộc lọc `attrs.get("package") == "com.google.android.gm"` và biên tọa độ tối thiểu `y >= 300`. Tránh tình trạng nhặt nhầm icon thông báo Android / GemPhone trên status bar (`bounds=[12,0][66,71]`, `y=35`) làm click lạc ra ngoài app.

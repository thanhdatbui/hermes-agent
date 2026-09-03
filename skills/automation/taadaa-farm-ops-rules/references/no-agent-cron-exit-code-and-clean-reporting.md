# No-Agent Cron Exit Code & Clean Telegram Reporting Standards

## Bối cảnh & Vấn đề
Khi cronjob chạy ở chế độ `no_agent: true`, Hermes scheduler sẽ thực thi trực tiếp script Python/Bash và lấy toàn bộ `stdout` gửi thẳng về chat Telegram.

### Bẫy Lỗi (Anti-Pattern):
1. **Exit code != 0 làm Hermes nuốt stdout:** Nếu script con/máy con trong batch bị lỗi và script tổng hợp trả về `exit code 1` (hoặc non-zero), Hermes coi job bị sập (crashed). Hermes sẽ không gửi `stdout` mà kích hoạt hàm `_summarize_cron_failure_for_delivery`, parse các từ khóa như `"timed out"` trong log và gửi cảnh báo sai lệch `⚠️ Cron failed: provider timeout...`.
2. **Spam log per-machine:** In log từng dòng `[OK] Machine XX...` hoặc `[WARN] Machine YY...` làm ngập màn hình Telegram.
3. **Emoji & Special Unicode Symbols:** Báo cáo dính emoji hoặc các ký tự symbol/pictograph vi phạm chuẩn ngắn gọn của farm.

---

## Chuẩn Thiết Kế & Xử Lý

### 1. Quy tắc Exit Code
- Script wrapper / pipeline tổng hợp **bắt buộc return 0** sau khi đã xuất bản tin báo cáo ra `stdout` (kể cả khi batch có máy fail).
- Chỉ return non-zero khi chính script pipeline bị crash nghiêm trọng trước khi tạo được báo cáo.

### 2. Tách Biệt stderr và stdout
- **`sys.stderr`:** Chứa toàn bộ log tiến trình, debug, khởi động subprocess, thời gian hoàn thành từng phase.
- **`sys.stdout`:** Chỉ in duy nhất 1 bản tin báo cáo sạch sẽ và hoàn chỉnh.

### 3. Chuẩn Báo Cáo Telegram (Farm Style)
- Dùng bullet ASCII (`-` và `+`), tuyệt đối không dùng emoji (⚠️, ❌, 📋, 🚀...) hoặc ký tự bullet unicode (`•`).
- Cấu trúc chuẩn theo 2 phase hoặc batch:
  ```text
  [BÁO CÁO CHUỖI ĐÊM] Gmail -> TikTok
  - Thời gian: 01:00 -> 01:54 (54 phút)

  - Phase 1 (Reg Gmail - Code 0):
    + Tổng máy: 15
    + Success (13): 01, 02, 03, 05, 06, 07, 10, 11, 12, 13, 14, 15, 16
    + Fail (2): 08, 09 (proxy timeout)

  - Phase 2 (Reg TikTok - Code 0):
    + Tổng máy: 13
    + Success (13): 01, 02, 03, 05, 06, 07, 10, 11, 12, 13, 14, 15, 16
    + Fail (0)
  ```
- **Gộp máy lỗi (Compact Grouping):** Gộp các máy cùng chung mã lỗi/lý do trên 1 dòng:
  `08, 09, 17 (proxy timeout); 49 (phone verification)`
- Khi không có máy lỗi: Bắt buộc ghi rõ `+ Fail (0)`.

### 4. Sanitization & Fallback Phòng Vệ
- Chuẩn hóa Unicode NFC và lọc ký tự an toàn:
  - Whitelist: ASCII cơ bản (chữ, số, khoảng trắng, dấu câu an toàn `.,:;!?'"()_/-[]+>`) + `VIETNAMESE_EXTRA_CHARS`.
  - Loại bỏ triệt để emoji, math/currency/modifier symbols (`=`, `$`, `^`, `∑`, `−`, `√`, `∞`), ký tự Latin mở rộng ngoài tiếng Việt (`ß`, `Æ`, `Ł`, `ĳ`).
- **Bóc prefix lặp trong fallback text:** Dùng regex bóc sạch các cụm `TOTAL=\d+`, `SUCCESS=\d+`, `FAILED_OTHER=\d+` trước khi format reason để không bị lặp chữ số trong dòng `+ Fail (N): ...`.
- **Phòng vệ Exception:** Bọc `safe_int_count`, `safe_format_stt` bắt cả `ValueError`, `TypeError`, `OverflowError` và float non-finite (`inf`, `nan`) để đảm bảo format không bao giờ crash trước khi return 0.

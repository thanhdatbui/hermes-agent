# Xử Lý UI_TARGET_AMBIGUOUS:Next:0 & Kỷ Luật Gọi Unified Patch Pipeline (31/10/2026)

## 1. Bản Chất Sự Cố `UI_TARGET_AMBIGUOUS:Next:0`
- **Hiện tượng:** Trong báo cáo 2FA ban đêm (`night_2fa_trace_{date}.log`), xuất hiện lỗi dạng `UI_TARGET_AMBIGUOUS:Next:0` tại bước điều hướng đổi mật khẩu hoặc xác minh danh tính.
- **Nguyên nhân kỹ thuật:**
  * Hàm `_tap_value(expected, prefix=...)` trong `live_phase_b_adapter.py` nhận `expected="Tiếp"` và tra cứu `_BILINGUAL_LABELS` ra `"Next"`.
  * Nếu cả 2 lần tìm kiếm ban đầu không tìm thấy phần tử khả dụng (do giao diện TikTok thực tế dùng nhãn `"Tiếp tục"` hoặc `"Continue"` hoặc khác trạng thái `prefix`), adapter ném ngoại lệ `LiveAdapterError("UI_TARGET_AMBIGUOUS:Next:0")`.
- **Giải pháp O(1) chuẩn hóa:**
  * Gom danh sách nhãn ứng viên đa ngữ mở rộng: `["Tiếp", "Tiếp tục", "Next", "Continue"]`.
  * Lặp qua từng nhãn với cả hai trạng thái `prefix=True` và `prefix=False`.
  * Chỉ raise lỗi khi toàn bộ các tổ hợp ứng viên đều không tìm thấy mục tiêu trên UI XML dump.

## 2. Kỷ Luật Thực Thi Qua `unified_patch_pipeline.py`
- Khi User ra lệnh "Fix dùm cái", "Fix đi", Coordinator kích hoạt trọn gói:
  `python D:/Taadaa/tools/unified_patch_pipeline.py run --repo D:/Taadaa/tiktok-add-bao-mat-f2a --file python_runner/core/live_phase_b_adapter.py --task "<task>" --test-cmd "python -m pytest python_runner/tests/test_live_phase_b_adapter.py -q" --no-canary --no-canary-reason "<lý do>"`
- **Pitfall chặn dòng của Coordinator Guard:**
  * CẤM ngắt dòng lệnh bằng dấu gạch chéo ngược `\` (backslash). Guard kiểm tra terminal theo từng dòng độc lập; các dòng tham số rời rạc như `--repo ... \` sẽ bị kích hoạt cơ chế `DEFAULT-DENY` chặn ngay lập tức.
  * Lệnh pipeline BẮT BUỘC viết trên một dòng duy nhất (single line).
- **Quy tắc `--no-canary` khi fix logic adapter thuần túy:**
  * Khi thay đổi mã nguồn tập trung vào adapter / unit test và không muốn chiếm dụng máy farm đang nghỉ ca, chỉ định rõ cờ `--no-canary --no-canary-reason "..."` để pipeline hoàn tất S0-S3 và chuyển thẳng sang S5 (AWAITING_USER).

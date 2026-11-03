# Gemini Web Autonomous Worker (Argon 4) Tier 1 Dispatch & Canary Integration (2026-11-03)

## 1. Bối Cảnh & Quyết Định Cấu Trúc (User Mandate 2026-11-03)
- **Qoder DeepSeek-Flash:** Đợt promo token miễn phí 0.0x kết thúc lúc 23:00 ngày 31/10/2026 (`ENABLE_QODER_WORKER` mặc định `= 0`).
- **User Mandate:** Đẩy **Gemini Web** (Argon 4 Pool qua `:20129`) lên làm **Tier 1 Primary Worker** chạy trước Sol Web Worker.
- **Canary Live Verification:** Đã kiểm chứng thực thi trực tiếp trên hiện trường qua `dispatch_worker.py`, đạt exit code 0 trong 23.2s.

---

## 2. Phân Tầng Single Dispatch Gateway (`D:/Taadaa/tools/dispatch_worker.py`)

1. **Tier 1 (Primary): `gemini_web_worker.py`**
   - Model backend: `gemini-web-argon-pool` qua OmniRoute (`http://127.0.0.1:20129/v1/chat/completions`).
   - Cờ cấu hình: `ENABLE_GEMINI_WORKER = os.environ.get("ENABLE_GEMINI_WORKER", "1") == "1"`.
   - Timeout: `max(args.timeout, 480)`.
   - Khả năng ReAct: Hỗ trợ cả block Action tiêu chuẩn (`ACTION: PATCH`, `ACTION: COMMAND`) và native Gemini format (`PATCH <file>` kèm `<<<< ... ==== ... >>>>`).
   - Gating an toàn: Chỉ cho phép test runner trong allowlist (`pytest`, `unittest`).
2. **Tier 2 (Fallback 1): `sol_worker.py`** (`gpt-web-sol` qua `:20129`).
3. **Tier 3 (Fallback 2): `ag_cli.py`** (Antigravity CLI Pool).
4. **Tier 4 (Fallback 3): `claude_worker.py`** (Claude Haiku 5.5 kẹp turns <= 15).

---

## 3. Các Cạm Bẫy Vận Hành Đã Đúc Kết Từ Thực Tế

1. **Bẫy `ACTION: DONE` khi chưa sửa file:**
   - Khi prompt quá dài hoặc có skill injection lớn, model web có thể vội vã nhả `ACTION: DONE`.
   - `gemini_web_worker.py` và `dispatch_worker.py` bắt buộc verify changes (`modified_files != []` và `target_file_modified`). Nếu không có diff (`NO_DIFF`), hệ thống tự động kích hoạt fallback sang Tier 2 (Sol) thay vì báo thành công giả.
2. **Bẫy Cho Phép Test Runner Khắt Khe:**
   - Hàm `is_command_safe` chỉ allowlist `pytest` và `unittest`. Lệnh `python -m py_compile` không nằm trong danh sách kiểm thử được phép và sẽ bị từ chối; muốn test cú pháp phải chạy qua focused pytest hoặc py_compile độc lập sau khi worker trả diff.
3. **Chốt Chặn Hard-Stop:**
   - Lỗi `NEEDS_INPUT` (marker `BLOCKED:`) và lỗi môi trường `ENV` (permission/file not found) là HARD STOP. Hệ thống dừng ngay lập tức, không trôi luồng sang Sol hay Agy.

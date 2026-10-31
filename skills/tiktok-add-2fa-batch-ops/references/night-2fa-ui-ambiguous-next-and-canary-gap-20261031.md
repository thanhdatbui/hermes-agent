# Night 2FA UI Ambiguous Next, Graph API Dual-Workbook & Canary Enforcement (31/10/2026)

## 1. Triệt Tiêu Lỗi `UI_TARGET_AMBIGUOUS:Next:0` Trong Đổi Pass TikTok
- **Bản chất lỗi:** 
  * Khi vào màn hình xác minh danh tính TikTok để tạo/đổi mật khẩu, TikTok hiển thị nút điều hướng có thể mang các nhãn khác nhau: `"Tiếp"`, `"Tiếp tục"`, `"Next"`, `"Continue"`.
  * Hàm `_tap_value("Tiếp", prefix=True)` cũ chỉ tra cứu nhãn đơn ngữ hoặc 1 cặp song ngữ cố định. Khi giao diện app render chữ "Tiếp tục" hoặc nút Next có cấu trúc khác, hàm văng lỗi `UI_TARGET_AMBIGUOUS:Next:0` làm hỏng cả phiên 2FA.
- **Giải pháp O(1) chuẩn hóa trong `live_phase_b_adapter.py`:**
  * Tại `_tap_value()`, tự động mở rộng danh sách candidate:
    `candidates = [expected] + [_BILINGUAL_LABELS.get(expected)]`
    Nếu `expected in {"Tiếp", "Tiếp tục", "Next", "Continue"}`, nạp toàn bộ bộ nhãn biến thể.
  * Duyệt thử lần lượt các nhãn với cả 2 cờ `prefix=True/False`, bắt `LiveAdapterError` để thử tiếp trước khi fail-closed.

---

## 2. Bẫy Bỏ Qua Canary S4 (`--no-canary`) & Lệch Cờ CLI Pipeline
- **Hiện tượng:**
  * Coordinator khi chạy `unified_patch_pipeline.py` đã dùng `--no-canary` với lý do "đây là code logic adapter và unit test mock đã pass".
  * **Kỷ luật Farm:** Code sửa `live_phase_b_adapter.py` trực tiếp điều khiển app TikTok trên máy thật S7. Dùng mock unit test để bỏ qua Canary máy thật là vi phạm nghiêm trọng Gate 6 Invariant (né tránh thực địa).
- **Nguyên nhân kỹ thuật phát hiện:**
  * `unified_patch_pipeline.py` ghép `["--device", args.canary_device]`, nhưng `canary_runner.py` chỉ nhận `--machine <N>`, `--machines <list>` hoặc `--auto-device`.
  * Lệch cờ CLI khiến Coordinator sợ crash pipeline nên đã lạm dụng `--no-canary`.
  * **Quy chuẩn bắt buộc:** Khi sửa code liên quan thiết bị, BẮT BUỘC chỉ định máy thật (`--machine <N>` hoặc cấu hình `--auto-device`) để Canary S4 chạy thực tế, cấm lạm dụng `--no-canary`.

---

## 3. Cơ Chế Thang Não Gate B: Vì Sao `gemini-web` Rớt Sang `sol-worker`
- **Thang ưu tiên:** `1. gemini-web` (Argon 4 Pool :20129) -> `2. sol-worker` (`gpt-web-sol` :20129) -> `3. claude-cli`.
- **Lý do fallback:**
  * Khi `gemini-web` nhận prompt, nếu model bị ảo giác cấu trúc code (tự bịa ra `old_string` không tồn tại trong file thật), hàm thẩm định `validate_plan()` sẽ phát hiện `file_text.count(old_str) != 1` và REJECT ngay lập tức.
  * Hệ thống tự động ghi vết thô vào `D:/Taadaa/runtime/audit_logs/gate_b_last_raw_response.txt` và chuyển quyền cho `sol-worker`.
  * Khi `sol-worker` tạo plan có anchor duy nhất tuyệt đối (`count == 1`), plan được APPROVE. Đây là hành vi đúng thiết kế của cơ chế tự phục hồi bậc thang (Multi-Tier Brain Ladder).

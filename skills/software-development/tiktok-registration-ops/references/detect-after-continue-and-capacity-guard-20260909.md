# Pitfall: detect_after_continue Header Collision & Machine Capacity Counting (2026-09-09)

## 1. False Positive trong `detect_after_continue()` (Header Collision)
- **Triệu chứng:** Hàng loạt máy (11 máy STT 02, 47, 54, 57, 58, 59, 62, 63, 67, 68, 69) đồng loạt văng lỗi:
  `RuntimeError: [07] Tat ca 1 email cua STT {stt} da co TK TikTok`
  mặc dù email hoàn toàn mới và chưa từng đăng ký.
- **Nguyên nhân gốc rễ:**
  - Trong `detect_after_continue()` (`social_reg_v1.py`), danh sách `form_hints` chứa từ khóa `"nhap dia chi email"`.
  - Tiêu đề tĩnh (header) của màn hình nhập email TikTok chính là:
    `<node package="com.ss.android.ugc.trill" class="android.widget.TextView" text="Nhập địa chỉ email" bounds="[96,336][984,450]" />`
  - Khi click nút *"Tiếp tục"*, TikTok chuyển trạng thái nút sang spinner xoay (loading) với `text=""`. Trong khoảng thời gian chờ server phản hồi (1–3s qua proxy 4G), tiêu đề *"Nhập địa chỉ email"* vẫn hiển thị.
  - Vòng lặp `while` kiểm tra `form_hints` ngay vòng đầu tiên, khớp `"nhap dia chi email"`, lập tức trả về `"form_still_visible"`.
  - Trong `fill_email_and_next()`, nhánh `form_still_visible` rơi vào `else:` (coi như không xác định), gửi phím `BACK` (keyevent 4), thoát khỏi flow đăng ký. Khi duyệt hết candidate emails, script raise nhầm thông báo "Tất cả email đã có TK TikTok".
- **Giải pháp chuẩn hóa:**
  - Tuyệt đối không dùng cụm từ tiêu đề header cho `validation_error_hints`. Chỉ dùng các cụm lỗi validation rõ ràng: `"nhap dia chi email hop le"`, `"dia chi email khong hop le"`, `"email khong hop le"`, `"enter a valid email"`, `"invalid email"`, `"valid email"`.
  - Phân tách cờ `had_form_error` để khi hết candidates thì raise đúng bản chất: `RuntimeError(f"[07] Khong the dang ky email cho STT {stt} do loi form validation ('{em}')")`.

---

## 2. Đếm số lượng tài khoản theo máy trong Tracking Sheet (`tiktok_target_eligibility.py`)
- **Triệu chứng:** Máy 61 bị crash với lỗi `MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`.
- **Nguyên nhân:**
  - Trong `load_registered_mailboxes()`, logic đếm cũ là:
    ```python
    if tiktok_id and stt_idx is not None and stt_idx < len(row):
        machine_counts[m] += 1
    ```
  - Trong file `taikhoan_dat_v2_updated .xlsx`, máy 61 đã được cấp phát đủ 8 dòng (Row 482–489), nhưng dòng thứ 8 có `tiktok_id = None` (slot đã giữ chỗ/chưa hoàn tất ghi ID).
  - Vì điều kiện `if tiktok_id`, `machine_counts[61]` chỉ đếm được 7. `select_pending_targets()` cho rằng máy còn chỗ (< 8) nên tiếp tục dispatch máy 61. Trên thiết bị thực tế, TikTok đã đăng nhập đủ 8 tài khoản.
- **Giải pháp:**
  - Đếm toàn bộ các dòng hợp lệ đã phân bổ cho STT `m` trong sheet tracking (`if stt_idx is not None and raw_stt: machine_counts[m] += 1`), bất kể `tiktok_id` đã có hay chưa.

---

## 3. Quy tắc Alert Pipeline vs Báo Cáo Vận Hành Chuỗi Đêm
- Trong `run_night_chain_pipeline.py`, Phase 2a gọi `_run_all_targets.py`. Hàm `batch_exit_code()` luôn trả về `1` nếu có ít nhất 1 máy thất bại (`fail_count > 0`).
- Không được dùng điều kiện thô `if tiktok_reg_code != 0:` để bắn `_send_night_chain_alert("Phase 2a", ...)`.
- Phải parse `tiktok_reg_details = parse_tiktok_details(tiktok_reg_out)`: Nếu `total > 0` và có kết quả từng máy, đây là kết quả vận hành farm bình thường (đã được tổng kết chi tiết trong Báo Cáo Chuỗi Đêm sáng hôm sau), KHÔNG bắn script alert làm phiền người vận hành. Chỉ bắn alert khi pipeline/script crash không sinh ra danh sách kết quả.

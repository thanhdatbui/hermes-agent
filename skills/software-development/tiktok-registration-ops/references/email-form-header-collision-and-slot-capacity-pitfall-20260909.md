# Pitfall: Email Form Header Collision, Machine Slot Capacity & Pipeline Alerting (2026-09-09)

## 1. Trùng lặp Tiêu đề Header với Lỗi Form Validation (`detect_after_continue`)
- **Hiện tượng:** 11 máy trong batch đồng loạt văng lỗi:
  `RuntimeError: [07] Tat ca 1 email cua STT ... da co TK TikTok`
- **Nguyên nhân gốc rễ:**
  - Trên màn hình nhập email của TikTok, tiêu đề cố định (screen title header) là `"Nhập địa chỉ email"`.
  - Hàm `detect_after_continue()` trước đây chứa `"nhap dia chi email"` trong danh sách `form_hints`.
  - Khi click nút "Tiếp tục", nút chuyển sang trạng thái loading spinner (`text=""`), nhưng request mạng đang gửi đi thì tiêu đề `"Nhập địa chỉ email"` vẫn hiển thị.
  - Vòng lặp kiểm tra phát hiện ngay `"nhap dia chi email"` ở lần quét đầu tiên và trả về sớm `"form_still_visible"`.
  - `fill_email_and_next()` không bắt riêng kết quả này, rơi vào nhánh `else:` gửi phím BACK (`keyevent 4`), hủy quá trình đăng ký và báo nhầm là email đã có tài khoản TikTok.
- **Quy tắc bắt buộc:**
  - Danh sách hint cho `form_still_visible` BẮT BUỘC chỉ chứa các cụm từ báo lỗi validation thực sự:
    `"nhap dia chi email hop le"`, `"dia chi email khong hop le"`, `"email khong hop le"`, `"enter a valid email"`, `"invalid email"`.
  - TUYỆT ĐỐI KHÔNG đưa tiêu đề tĩnh của màn hình vào hint.
  - Phân biệt rõ ngoại lệ form validation với ngoại lệ email đã tồn tại.

## 2. Lỗi Kiểm tra Giới hạn 8 Tài khoản / Máy (`machine_counts`)
- **Hiện tượng:** Máy đã đủ 8 tài khoản trên app TikTok bị chọn lại và fail với lỗi:
  `RuntimeError: [04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`
- **Nguyên nhân gốc rễ:**
  - Trong `tiktok_target_eligibility.py::load_registered_mailboxes()`, điều kiện đếm máy từng là:
    `if tiktok_id and stt_idx is not None and stt_idx < len(row): machine_counts[m] += 1`
  - Nếu file tracking `taikhoan_dat_v2_updated .xlsx` đã có sẵn 8 dòng slot cho máy, nhưng dòng thứ 8 có `tiktok_id = None` (chưa gán ID), thì `machine_counts[m]` chỉ đếm được 7.
  - Bộ chọn `select_pending_targets()` thấy 7 < 8 nên vẫn cấp thêm target cho máy đó, dẫn đến crash khi thiết bị vật lý đã đủ 8 tài khoản.
- **Quy tắc bắt buộc:**
  - Đếm `machine_counts[m]` dựa trên số dòng slot đã cấp phát cho máy `m` trong sheet `Tài Khoản`, không phụ thuộc vào việc `tiktok_id` đã được ghi nhận hay chưa.

## 3. Phân biệt Lỗi Vận hành Batch và Lỗi Script / Pipeline trong Chuỗi Đêm
- **Hiện tượng:** Pipeline ban đêm gửi cảnh báo `[FARM ALERT: LỖI SCRIPT / PIPELINE]` cho Phase 2a dù batch đã chạy hết các targets và tổng kết kết quả.
- **Nguyên nhân gốc rễ:**
  - `_run_all_targets.py` trả về exit code 1 bất cứ khi nào `fail_count > 0` (thông qua `batch_exit_code`).
  - Trong `run_night_chain_pipeline.py`, Phase 2a chỉ kiểm tra `if tiktok_reg_code != 0:` để gửi cảnh báo lỗi script, khác với Phase 1 (Gmail) vốn kiểm tra `if not (isinstance(details, dict) and int(details.get("total", 0) or 0) > 0)`.
- **Quy tắc bắt buộc:**
  - Khi runner hoàn thành batch và tạo ra `all_results.json` với `total > 0`, đây là kết quả vận hành farm bình thường (được báo cáo chi tiết trong báo cáo chuỗi đêm cuối phiên).
  - Chỉ gửi `_send_night_chain_alert()` khi tiến trình thực sự bị crash (không đọc được kết quả hoặc `total == 0`).

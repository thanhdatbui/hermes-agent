# Cơ chế Per-Account Organic Rest (1/3) Thay Thế Modulo 6 Cũ

## 1. Bối cảnh & Lý do thay đổi
- **Cơ chế cũ (Modulo 6 toàn cục):** Runner tính toán chu kỳ 6 ngày `(now.date() - epoch).days % 6`. Vào Day 2 (Row lẻ) và Day 5 (Row chẵn), toàn bộ farm/toàn bộ máy trong row đều chuyển sang trạng thái "Dưỡng sinh" (set `TAADAA_REST_DAY_NO_FOLLOW=1` và không truyền `-AllowUploadHook`).
  - *Nhược điểm:* Khiến hoạt động follow/upload bị ngắt quãng đồng loạt trên toàn bộ farm vào ngày dưỡng sinh; hành vi mang tính robot tập trung, dễ bị thuật toán TikTok nhận diện pattern đồng loạt.
- **Cơ chế mới (Per-Account Organic Rest 1/3):**
  - Đẩy quyền quyết định ngày dưỡng sinh xuống từng worker (từng tài khoản độc lập).
  - Tỷ lệ nghỉ dưỡng sinh tự nhiên là **1/3 (~33.33%)** mỗi ngày cho từng tài khoản.
  - Các tài khoản còn lại (2/3) vẫn follow và upload bình thường. Farm hoạt động liên tục mỗi ngày, không còn ngày "chết" hoàn toàn.

---

## 2. Chi tiết kiến trúc & Triển khai

### A. Runner phân định Lịch Chẵn / Lẻ (`tiktok_runner.py`)
- Phân định ca Chẵn / Lẻ đơn giản theo ngày dương lịch:
  ```python
  # Parity: 0 nếu ngày chẵn (Row chẵn), 1 nếu ngày lẻ (Row lẻ)
  parity = 0 if (now.day % 2 == 0) else 1
  row = slots[parity]
  is_rest_day = False  # Nhường quyền quyết định cho từng worker
  ```
- Runner luôn truyền `-AllowUploadHook` và **xóa bỏ** biến môi trường toàn cục `TAADAA_REST_DAY_NO_FOLLOW`:
  ```python
  child_env = dict(os.environ)
  child_env.pop("TAADAA_REST_DAY_NO_FOLLOW", None)
  ```

### B. Worker xác định Organic Rest độc lập (`multi_machine_feed_session.py`)
- Dùng hàm băm MD5 dựa trên tuple `(date_str, machine, row)` để đảm bảo:
  1. **Nhất quán trong ngày (Deterministic):** Dù chạy Phiên 1, Phiên 2 hay retry lại trong cùng một ngày, tài khoản đó vẫn giữ nguyên trạng thái (nghỉ hoặc hoạt động).
  2. **Độc lập và ngẫu nhiên (Entropy):** Các máy khác nhau và các row khác nhau có kết quả băm khác nhau, phân bổ đều ~33.33% nghỉ và ~66.67% hoạt động.
  ```python
  def _is_account_organic_rest_day(machine: int, row: int, date_str: str | None = None) -> bool:
      if not date_str:
          date_str = datetime.now().strftime("%Y-%m-%d")
      h = hashlib.md5(f"{date_str}:{machine}:{row}".encode("utf-8")).hexdigest()
      return (int(h[:8], 16) % 3) == 0
  ```

### C. Tác động của Organic Rest Day lên các Hook
1. **Feed Session:** Vẫn chạy bình thường (lướt video, tương tác organic để giữ trust score).
2. **Follow Hook (`_run_follow_hook`):**
   - Bỏ qua follow hook nếu `_is_account_organic_rest_day(m_id, r_id)` trả về `True`.
   - Ghi log skip: `reason="organic-rest-day-pure-feed"`, `action="skip_follow_rest_day"`.
3. **Upload Hook (`_run_upload_hook`):**
   - Bỏ qua upload hook nếu `_is_account_organic_rest_day(machine_id, upload_row)` trả về `True`.
   - Ghi log skip: `reason="organic-rest-day-pure-feed"`.

# Quy Chuẩn Đánh Giá "Nick Cắn Đề Xuất" (Trending / Viral Detection)

Tài liệu tham chiếu chuẩn hóa logic phát hiện tài khoản cắn đề xuất trên các công cụ giám sát TikTok Farm (`tiktok_dashboard.py`, `tiktok_account_tracker.py`, Telegram alert).

---

## 1. Bản Chất Vấn Đề & Pitfall Cần Tránh

### Pitfall: Ngưỡng quá nhạy (`delta > 0`)
- **Sai lầm:** Đặt điều kiện `is_trending = (delta_f > 0) or (delta_h > 0)`.
- **Hệ quả thực tế:**
  - Trong farm hàng trăm tài khoản, chỉ cần 1 người lướt qua bấm like hoặc 1 bot follow ngẫu nhiên (+1 like hoặc +1 follower giữa 2 lần quét), nick đã bị gắn mác `🔥 ĐỀ XUẤT`.
  - Trên web dashboard (port 1905), hàng loạt nick (20-30% toàn farm) hiển thị huy hiệu `🔥 ĐỀ XUẤT`, gây nhiễu thông tin nghiêm trọng, làm mất khả năng nhận diện các nick thực sự viral.

---

## 2. Tiêu Chuẩn Ngưỡng Phân Định (Benchmark)

Dựa trên dữ liệu thực tế từ `D:/Taadaa/data/tiktok_tracker.db` (đối soát 600 nick):
- Số nick tăng follower tự nhiên (+1 đến +2 fl): ~40 nick. Chỉ có ~2 nick tăng $\ge 10$ fl.
- Số nick tăng tim tự nhiên (+1 đến +3 tim): ~100 nick. Chỉ có 3 nick tăng $\ge 50$ tim.

### Ngưỡng Khuyến Nghị Cho Hệ Thống:

1. **Chuẩn Tracker & Telegram Alert (`tiktok_account_tracker.py`):**
   ```python
   # Ngưỡng tối thiểu để tính là có tín hiệu tăng trưởng / đề xuất
   trending = bool(follower_delta >= 10 or heart_delta >= 50)
   ```

2. **Chuẩn Phân Tầng Dashboard Web (Khuyến khích cập nhật):**
   - **Tín hiệu chớm đề xuất / Tăng trưởng:** `delta_f >= 10` hoặc `delta_h >= 50` (Badge: `⚡ TĂNG TRƯỞNG`).
   - **Cắn đề xuất thực sự (Viral Spike):** `delta_f >= 20` hoặc `delta_h >= 100` (Badge: `🔥 ĐỀ XUẤT`).
   - **Tài khoản lớn duy trì tương tác:** `follower >= 1000 and is_live and (delta_f > 0 or delta_h > 0)` (Tránh gắn cờ đề xuất cho nick 1k fl đứng yên không tăng trưởng).

---

## 3. Checklist Điều Phối Khi Sửa Rule Đề Xuất

Khi nhận yêu cầu tinh chỉnh logic đề xuất trên Dashboard:
1. **Kiểm tra file logic:**
   - `D:/Taadaa/tools/tiktok_dashboard.py`: Logic hàm `get_farm_data()` tính `is_trending` và `delta_f`, `delta_h`.
   - `D:/Taadaa/tools/tiktok_account_tracker.py`: Hàm `export_excel_report()` và `generate_summary_message()`.
2. **Kỷ luật điều phối:**
   - Coordinator chỉ O(1) query SQLite kiểm tra phân bố số liệu trước & sau.
   - Soạn Patch Contract duy nhất tuyệt đối (`grep -o ... | wc -l == 1`).
   - Dispatch Worker qua `delegate_task` thực hiện patch và restart service (PID listening port 1905).

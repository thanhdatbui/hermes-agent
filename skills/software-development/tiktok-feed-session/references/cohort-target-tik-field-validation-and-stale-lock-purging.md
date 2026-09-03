# Quy Chuẩn Validate Frozen Cohort Target Identity & Dọn Dẹp Stale Device Lock Khi Batch Fail (2026-08-28)

## 1. Bản chất lỗi `cohort target identity mismatch: missing:tik`
- Trong hệ thống nuôi acc TikTok theo phiên cron (`tiktok-luot nuoi acc`), cấu trúc manifest phân bổ ca (như Ca 2 Row 4) và workbook `taikhoan_run_safe.xlsx` có thể không khai báo trường `tik` trong danh sách target phân bổ.
- Nếu hàm `_apply_cohort_identity` trong `python_runner/flows/multi_machine_feed_session.py` áp dụng quy tắc kiểm tra cứng:
  ```python
  # LỖI: Bắt buộc mọi target phải có key "tik"
  if "tik" not in expected:
      mismatches.append("missing:tik")
  ```
  $\rightarrow$ Toàn bộ 34 máy trong ca sẽ bị chặn đứng ngay ở giây đầu tiên của preflight trước khi lướt feed.
- **Quy chuẩn đúng (Commit `e5164c2`):** Chỉ kiểm tra đối soát `tik` khi trường này thực sự xuất hiện trong `expected` cohort plan:
  ```python
  if "tik" in expected:
      val = expected.get("tik")
      if type(val) is bool or not isinstance(val, (int, str)) or not str(val).strip() or str(val) != str(account.tik):
          mismatches.append("tik")
  ```

---

## 2. Quy trình Xử lý & Dọn Dẹp Device Lock sau khi Batch gặp sự cố Preflight
- Khi một batch máy lớn (ví dụ 34 máy) gặp sự cố validation hoặc preflight VPN, hệ thống sẽ gán lock trạng thái `blocked` và sinh ra cả 2 định dạng file trong `~/.codex/device-locks/`:
  - `machine_<ID>.lock.json`
  - `serial_<SERIAL>.lock.json`
- **Hệ quả:** Sau khi sửa xong code và deploy script runner mới, các tick cron tiếp theo vẫn sẽ bỏ qua toàn bộ máy (`skipped-device-locked`) do vướng lock `blocked` cũ.
- **Quy trình phục hồi bắt buộc:**
  1. Patch và test code validation (`pytest python_runner/tests/ -k cohort` $\rightarrow$ 100% pass).
  2. Đồng bộ script mới sang `C:\Users\Kibe\AppData\Local\hermes\scripts\tiktok_runner.py`.
  3. Quét và xóa sạch các file lock phát sinh trong khoảng thời gian xảy ra sự cố tại `C:\Users\Kibe\.codex\device-locks\`.
  4. Xác nhận tick cron tiếp theo spawn launcher thành công và các máy bắt đầu lướt feed thật.

---

## 3. Cơ chế Báo Cáo của Watchdog (`feed_session_watchdog.py`)
- Watchdog hoạt động độc lập mỗi 5 phút với nguyên tắc:
  - **Điều kiện gửi tin:** `(completed_count >= expected_count and not runner_busy) or (now_hm >= win["end"] and not runner_busy)`.
  - **Khi đang chạy cuốn chiếu:** Nếu 32/34 máy đã xong và 2 máy cuối đang thực hiện những lượt swipe cuối, watchdog giữ trạng thái chờ runner dừng hẳn trước khi tổng kết, đảm bảo số liệu gửi lên Telegram là trọn vẹn và không bị phân mảnh.

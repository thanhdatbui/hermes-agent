# Post-Upload Auto Audit Watchdog Silence & Empty Schema Invariant (2026-10-31)

## 1. Hiện Tượng Thực Tế
- Cronjob định kỳ `post-upload-auto-audit-sync` (ID: `968d54d74b72`, chạy vào `45 10,16,20,0 * * *`) bất ngờ báo lỗi `Script exited with code 1` vào tick rạng sáng lúc 00:45.
- Cảnh báo Farm Alert nổ làm gián đoạn hệ thống dù không có lỗi phần cứng hay lỗi mạng.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Lệch Nhịp Ca Upload vs Khung Giờ Rạng Sáng (00:45):**
   - Ca tối ngày hôm trước kết thúc trước 21:00, còn ngày mới 31/10 tại thời điểm 00:45 chưa có bất kỳ máy nào bắt đầu upload ca mới.
   - Hàm `get_uploaded_accounts_from_ledger(date_str)` đọc `shift_upload_history.json` trả về danh sách rỗng (`accounts == []`).
2. **Schema Inconsistency Trap:**
   - Khi có account, `run_post_upload_sync` trả về summary đầy đủ: `date`, `row`, `total`, `confirmed_match`, `delayed_or_anomaly`, `anomalies`.
   - Nhưng khi rỗng, code cũ trả về:
     ```python
     return {"total": 0, "success": 0, "delayed": 0, "results": []}
     ```
   - Trong `main()`, dòng in báo cáo truy xuất `summary['date']` và `summary['row']` nhưng 2 key này không tồn tại, gây crash:
     ```text
     KeyError: 'date'
     ```
   - Exit code 1 khiến Hermes Cron Scheduler phân loại là task thất bại và gửi alert.

---

## 3. Quy Tắc Bắt Buộc Khi Thiết Kế Watchdog Đối Soát Sau Ca

### 3.1. Đồng Nhất Schema Tuyệt Đối (Schema Parity)
- Dù danh sách tài khoản trống (`not accounts`), summary dictionary trả về BẮT BUỘC phải có cùng cấu trúc và đầy đủ các key chuẩn:
  ```python
  if not accounts:
      logger.info(f"Không có nick nào upload success trong ca {date_str} (Row: {row or 'ALL'})")
      return {
          "date": date_str,
          "row": row,
          "total": 0,
          "confirmed_match": 0,
          "delayed_or_anomaly": 0,
          "anomalies": [],
      }
  ```

### 3.2. Triệt Để Giữ Im Lặng Khi Không Có Dữ Liệu (Watchdog Silence Contract)
- Với các cronjob `no_agent=True` có `deliver` về Telegram:
  - **Stdout có chữ** $\to$ Hermes gửi tin nhắn đến Telegram.
  - **Stdout rỗng** $\to$ Hermes giữ im lặng tuyệt đối.
  - **Exit code != 0** $\to$ Hermes gửi alert cảnh báo lỗi script.
- Do đó, khi `summary.get("total", 0) == 0`:
  - Phải return ngay với exit code 0 trước khi in báo cáo ra stdout (trừ khi có cờ `--json-output` từ caller lập trình).
  - Tránh in tiêu đề bảng biểu trống ("Tổng số nick vừa cào: 0") làm rác kênh chat Telegram của farm.

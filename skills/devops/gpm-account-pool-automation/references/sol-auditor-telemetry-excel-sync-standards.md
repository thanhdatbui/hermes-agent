# Telemetry Metrics & Thread-Safe Excel Sync for Sol Auditor (>= 85)

## 1. Bối cảnh & Yêu cầu Sol Auditor
Khi Sol Auditor đánh giá mã nguồn các script tự động hóa GPM / Gmail 2FA / Excel Sync, các tiêu chí đánh giá nghiêm ngặt bao gồm:
- **Telemetry Observability**: Tất cả các thao tác critical (đồng bộ file, giải mã OTP/2FA, lưu DB/Excel) phải phát ra telemetry metric dạng JSON có cấu trúc rõ ràng (`timestamp`, `event`, `pid`, `duration_ms`, `status`, `metadata`).
- **Thread Safety / File Concurrency**: Thao tác đọc/ghi file Excel dùng chung (`master_gmail_manager.xlsx`, `gmail_clean_v2.xlsx`) qua `openpyxl` phải được bảo vệ bởi central threading Lock (`threading.Lock()`) để chống corrupt file khi chạy đa luồng/đa worker.
- **Unit Test Coverage**: Phải có bộ unit test toàn diện (functional test, mocking Excel I/O, concurrency/race-condition test, và error handling rollback/failure test).

---

## 2. Chuẩn Telemetry Metric JSON

Hàm telemetry chuẩn tái sử dụng:
```python
import datetime
import json
import logging
import os

logger = logging.getLogger("Telemetry")


def log_telemetry_metric(event_type: str, data: dict):
  """Ghi nhận telemetry metric có cấu trúc JSON để phục vụ quan sát hệ thống & watchdog."""
  metric = {
      "timestamp": datetime.datetime.now().isoformat(),
      "event": event_type,
      "pid": os.getpid(),
      "data": data,
  }
  logger.info(f"[TELEMETRY_METRIC] {json.dumps(metric, ensure_ascii=False)}")
  return metric
```

---

## 3. Pattern Thread-Safe Sync Excel với Telemetry

```python
import datetime
import threading
import time
import openpyxl

_EXCEL_SYNC_LOCK = threading.Lock()


def sync_secret_to_excels(email: str, secret_key: str) -> bool:
  """Lưu đồng bộ Secret Key 2FA vào cả master_gmail_manager.xlsx và gmail_clean_v2.xlsx.

  Bảo đảm thread-safe và ghi nhận telemetry metric đầy đủ.
  """
  t0 = time.time()
  success = False
  with _EXCEL_SYNC_LOCK:
    try:
      now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      clean_secret = secret_key.strip().replace(" ", "").upper()

      # 1. Master Excel
      wb1 = openpyxl.load_workbook(MASTER_EXCEL)
      for sname in ["Kibe_Farm_S7", "Master_All"]:
        if sname not in wb1.sheetnames:
          continue
        ws = wb1[sname]
        headers = [
            str(ws.cell(1, col).value or "").strip().lower()
            for col in range(1, ws.max_column + 1)
        ]
        col_map = {h: col + 1 for col, h in enumerate(headers)}

        email_col = col_map.get("email", 2)
        sec_col = col_map.get("2fa_secret", 5)
        upd_col = col_map.get("cập nhật", 15)
        note_col = col_map.get("ghi chú", 14)

        for r in range(2, ws.max_row + 1):
          cell_em = str(ws.cell(r, email_col).value or "").strip().lower()
          if cell_em == email.lower():
            ws.cell(r, sec_col, clean_secret)
            if upd_col <= ws.max_column:
              ws.cell(r, upd_col, now_str)
            curr_note = str(ws.cell(r, note_col).value or "").strip()
            if curr_note == "None":
              curr_note = ""
            tag = "Bật 2FA Authenticator thành công"
            if tag not in curr_note:
              ws.cell(
                  r, note_col, f"{curr_note} | {tag}".strip(" |") if curr_note else tag
              )
            break
      wb1.save(MASTER_EXCEL)
      wb1.close()

      # 2. Clean V2 Excel
      wb2 = openpyxl.load_workbook(CLEAN_V2_EXCEL)
      ws2 = wb2.active
      headers2 = [
          str(ws2.cell(1, col).value or "").strip().lower()
          for col in range(1, ws2.max_column + 1)
      ]
      col_map2 = {h: col + 1 for col, h in enumerate(headers2)}
      email_col2 = col_map2.get("tài khoản gmail", 2)
      sec_col2 = col_map2.get("2fa", 4)

      for r in range(2, ws2.max_row + 1):
        cell_em = str(ws2.cell(r, email_col2).value or "").strip().lower()
        if cell_em == email.lower():
          ws2.cell(r, sec_col2, clean_secret)
          break
      wb2.save(CLEAN_V2_EXCEL)
      wb2.close()

      success = True
      return True
    except Exception as e:
      logger.error(f"Lỗi khi lưu Excel cho {email}: {e}")
      success = False
      return False
    finally:
      duration_ms = round((time.time() - t0) * 1000, 2)
      log_telemetry_metric(
          "sync_secret_to_excels",
          {
              "email": email,
              "status": "success" if success else "failed",
              "duration_ms": duration_ms,
          },
      )
```

---

## 4. Cấu trúc Unit Test chuẩn (Pytest & Mocks)

Để vượt qua ngưỡng Sol Auditor >= 85, bộ unit test bắt buộc bao gồm:
1. **Mock Excel in-memory / temporary file**: Tránh ghi đè file production thật (`D:\OneDrive\...`).
2. **Test Clean Secret String Formatting**: Kiểm tra secret có khoảng trắng / chữ thường được chuẩn hóa thành uppercase và không khoảng cách (`"abcd efgh"` -> `"ABCDEFGH"`).
3. **Test Concurrency Stress Test**: Dùng `concurrent.futures.ThreadPoolExecutor` gọi song song hàm ghi để chứng minh không có race condition hay unhandled exception.
4. **Test Exception Handling & Telemetry Emission**: Dùng `unittest.mock.patch` mô phỏng lỗi `openpyxl.load_workbook` raises `IOError`, kiểm tra hàm trả về `False` an toàn và telemetry event được ghi nhận với `status="failed"`.

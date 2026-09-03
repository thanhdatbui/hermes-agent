# Windows PowerShell Detached Spawn Flags & Cohort Tik Validation Lessons (2026-08-28)

## 1. Windows PowerShell Detached Spawn Flag Trap
- **Triệu chứng:** Cron job `phase9-runner-tiktok-feed` gọi `_spawn_live` sinh PID và lease nhưng sau đó tiến trình biến mất ngay lập tức, không có folder run live nào được tạo và không có worker nào chạy.
- **Nguyên nhân gốc rễ:** `subprocess.Popen` truyền `creationflags = 0x00000208` (`CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS`). Trên Windows, `powershell.exe` (PowerShell 5.1) yêu cầu một console host subsystem hợp lệ để khởi chạy; `DETACHED_PROCESS` cắt đứt console subsystem khiến PowerShell crash/exit ngay khi mở.
- **Giải pháp chuẩn:**
  ```python
  if sys.platform == "win32":
      popen_kwargs["creationflags"] = 0x08000200  # CREATE_NEW_PROCESS_GROUP (0x200) | CREATE_NO_WINDOW (0x8000000)
  else:
      popen_kwargs["start_new_session"] = True
  ```
  `CREATE_NO_WINDOW` cho phép tiến trình chạy ngầm hoàn toàn mà không làm sập runtime PowerShell.

## 2. Cohort Target Identity: `missing:tik` Validation Trap
- **Triệu chứng:** Hàng loạt máy trong ca nuôi feed (ví dụ Ca 2 Row 4) dừng ngay ở giây đầu tiên với lỗi:
  `cohort target identity mismatch: missing:tik` và bị đưa vào lock `blocked`, gây nghẽn toàn bộ farm.
- **Nguyên nhân gốc rễ:** Hàm `_apply_cohort_identity` trong `multi_machine_feed_session.py` ép kiểm tra cứng:
  `if "tik" not in expected: mismatches.append("missing:tik")`. Tuy nhiên, trong manifest các ca nuôi feed thuần (như Row 4), trường `tik` không được khai báo trong `entries_by_machine`.
- **Giải pháp chuẩn:**
  Chỉ validate trường `tik` nếu `tik` có tồn tại trong expected target:
  ```python
  if "tik" in expected:
      val = expected.get("tik")
      if type(val) is bool or not isinstance(val, (int, str)) or not str(val).strip() or str(val) != str(account.tik):
          mismatches.append("tik")
  ```

## 3. Quy tắc kiểm tra Tiến độ & Báo cáo Cron Watchdog
- Watchdog chạy `no_agent: true` mỗi 5 phút và chỉ gửi tin báo cáo Telegram khi:
  1. Toàn bộ máy dự kiến trong ca/phiên đã hoàn thành VÀ runner đã dừng hẳn.
  2. HOẶC đã qua mốc kết thúc khung giờ phiên VÀ runner đã dừng hẳn.
- Khi một phiên đang có máy chạy dở dang (ví dụ 32/34 máy xong, 2 máy đang swipe), watchdog giữ `silent` để không spam báo cáo thiếu số liệu.

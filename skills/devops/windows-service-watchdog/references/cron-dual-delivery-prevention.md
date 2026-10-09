# Cron Dual Delivery Prevention (no_agent stdout vs Script Bot API)

## Hiện tượng (Symptom)
Người dùng nhận được 2 tin nhắn báo cáo gần như cùng 1 giây (ví dụ: `23:50:50`):
1. **Tin nhắn 1:** Tin nhắn sạch sẽ (chỉ có nội dung báo cáo HTML/Markdown).
2. **Tin nhắn 2:** Tin nhắn có header `Cronjob Response: <job-name> (job_id: <id>)` chứa nội dung tương tự hoặc một phần nội dung.

## Nguyên nhân gốc rễ (Root Cause)
Cơ chế kép gửi tin nhắn đồng thời giữa Script và Scheduler:
- **Kênh A (Script chủ động):** Script Python gọi trực tiếp HTTP Bot API Telegram (`send_farm_alert` qua `urllib.request` tới `https://api.telegram.org/bot<TOKEN>/sendMessage`).
- **Kênh B (Scheduler tự động):** Cronjob trong Hermes được tạo với:
  ```json
  {
    "no_agent": true,
    "deliver": "telegram:-5373649734"
  }
  ```
  Và trong script có lệnh `print(report_msg)`. Trong Hermes, khi `no_agent: true`, bất kỳ output nào trên STDOUT đều được coi là message cần gửi đến đích (`deliver`).

Khi kết thúc, Script vừa bắn HTTP Telegram (Kênh A), vừa in ra STDOUT khiến Hermes Scheduler bắn tiếp một lượt nữa tới cùng kênh Telegram (Kênh B).

## Hai mô hình chuẩn (Choose ONE Delivery Architecture)

### Mô hình 1: Script tự gửi Telegram (Khuyên dùng khi cần format HTML tùy biến cao)
- **Cấu hình Cronjob:** Đặt `deliver: local`.
  ```python
  cronjob(action='update', job_id='<job_id>', deliver='local')
  ```
- **Xử lý trong Script:**
  - Giữ lại `send_farm_alert(report_msg)`.
  - **BỎ HẲN** `print(report_msg)` in ra STDOUT. Thay vào đó chỉ in ngắn gọn hoặc redirect:
    ```python
    sys.stderr.write("[WATCHDOG] Report sent via Bot API\n")
    # hoặc print("[WATCHDOG] Done", file=sys.stderr)
    ```

### Mô hình 2: Để Hermes Cron Scheduler tự Deliver
- **Cấu hình Cronjob:** Đặt `deliver: telegram:-<chat_id>`, `no_agent: true`.
- **Xử lý trong Script:**
  - **BỎ HẲN** hàm `send_farm_alert()` hoặc không gọi nó.
  - Script giữ STDOUT hoàn toàn rỗng trong suốt quá trình chạy.
  - Khi cần báo cáo, chỉ in đúng nội dung báo cáo ra `sys.stdout` một lần duy nhất trước khi `exit(0)`.
  - Không in ra STDOUT khi không có việc (`s_count == 0` -> im lặng hoàn toàn).

---

## 3. Bẫy Fallback STDOUT (The Fallback Print Trap)

### Cảnh báo bẫy logic:
Nhiều kỹ sư có thói quen viết fallback phòng thủ: "Nếu gửi Bot API lỗi hoặc không có token thì in ra console để scheduler gửi bù":
```python
# BẪY NGUY HIỂM GÂY DUPLICATE
if token:
    try:
        sent = send_farm_alert(report_msg)
        if not sent:
            print(report_msg)  # <-- BẪY
    except Exception as e:
        print(report_msg)      # <-- BẪY
else:
    print(report_msg)          # <-- BẪY
```

### Tại sao bẫy này chắc chắn gây Báo Kép:
1. **HTTP Transient Timeout**: Khi mạng lag, `urllib.request.urlopen(..., timeout=15)` có thể bị timeout ở client sau 15s trong khi Telegram server ĐÃ nhận và ĐÃ phát tin nhắn vào group thành công. Kết quả: `sent == False` hoặc văng Exception, nhánh fallback `print(report_msg)` kích hoạt. Hermes Scheduler bắt lấy STDOUT và gửi tiếp tin nhắn thứ hai mang header `Cronjob Response:`.
2. **Cấu hình Cron chưa chuyển sang `local`**: Khi Cronjob vẫn mang `deliver: telegram:-5373649734`, chỉ cần một lần fallback hoặc log sót là lập tức bị bắn đúp.

### Nguyên tắc xử lý bất biến:
- Trong **Mô hình 1 (Script tự gửi)**: TUYỆT ĐỐI CẤM fallback `print(report_msg)` ra STDOUT. Mọi lỗi gửi API chỉ được ghi vào `sys.stderr.write(...)`. BẮT BUỘC đặt cronjob `deliver: local`.
- Không cố gắng "lai tạp" 2 mô hình trong cùng một script watchdog.

---

## 4. Bẫy Exception Double-Fire & Alert Storm Khi Cron Lặp Lại ("Bắn cả đống alert")

### Hiện tượng
Khi script cronjob crash (ví dụ `NameError: name 'executor' is not defined`):
1. Telegram nhận được đồng thời 2 tin nhắn cảnh báo trong vòng 1-2 giây:
   - **Tin 1:** `🚨 [FARM ALERT: LỖI SCRIPT / PIPELINE]` do script tự gọi HTTP Bot API.
   - **Tin 2:** `⚠️ Cron '<name>' failed: Script exited with code 1 stderr: ...` do Hermes Cron Scheduler tự động deliver khi tiến trình exit non-zero.
2. Với cronjob chạy định kỳ (ví dụ `*/15 3,4,5 * * *` = 12 lần/ca), mỗi lần chạy lại bị crash tương tự -> **12 tick × 2 alerts = 24 alerts** dội về group (Alert Storm), gây spam nghiêm trọng cho người dùng.

### Nguyên nhân cấu trúc
Đoạn code bắt ngoại lệ ở entrypoint:
```python
if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        _send_clear_cache_alert(f"Lỗi script nghiêm trọng: {exc}")  # <-- Bắn Kênh A (Bot API)
        raise  # <-- Thoát exit code 1 -> Hermes Scheduler bắn tiếp Kênh B (Scheduler Deliver)
```
Kết hợp với việc thiếu bộ đệm Debounce / Cooldown cho Exception:
- Script chỉ debounce lỗi per-machine trong `main()`, nhưng bỏ quên khối `except Exception:` ngoài cùng.
- Hàm `send_farm_script_alert()` không có cache cooldown theo `hash(script_name + error_reason)`.

### Giải pháp chống Alert Storm (3-Tier Anti-Alert-Storm)
1. **Khử Double-Fire ở Entrypoint:**
   - Nếu cronjob đã cấu hình `deliver: telegram:-<chat_id>`: KHÔNG gọi thêm `_send_clear_cache_alert()` rồi `raise`. Chỉ cần `raise` để Hermes Scheduler deliver stderr là đủ, hoặc bắt exception, gọi alert một kênh duy nhất rồi `sys.exit(0)`.
2. **Debounce Exception cấp Script (Stateful Cache):**
   - Lưu vết lỗi và timestamp vào state file (ví dụ `alert_debounce_state.json`).
   - Nếu cùng loại lỗi xuất hiện lại trong cửa sổ Cooldown (ví dụ 4 giờ hoặc cùng ngày `today_str`), script **im lặng hoàn toàn** (silent), chỉ log vào stderr hoặc file log cục bộ.
3. **Cooldown cấp Framework (`send_farm_script_alert` trong `automation-core`):**
   - Lưu cache trong thư mục tạm `farm_alerts_cooldown/` với key băm MD5 `f"{script_name}:{error_reason}"`.
   - **Ghi file nguyên tử (Atomic replace):** Ghi ra file `.tmp` có chứa PID và epoch millisecond (`f"{k}_{os.getpid()}_{int(now_ts * 1000)}.tmp"`) rồi dùng `replace(cd_p)` để triệt tiêu race condition khi nhiều worker/tiến trình cùng trigger alert đồng thời.
   - **Telemetry & Logging:** Ghi `log.info("[COOLDOWN_SUPPRESSED] Script alert for '%s' suppressed within 3600s cooldown")` khi bị chặn, và `log.warning("[COOLDOWN_CACHE_ERROR] ...")` nếu gặp lỗi đọc/ghi cache thay vì nuốt `pass`.
   - **Bypass switches:** Tự động bypass cooldown khi có `FORCE_TEST_ALERT_DISPATCH=1` (để unit test luôn kiểm chứng được chuỗi format/dispatch mà không bị dính state cũ), hoặc qua biến môi trường `FARM_ALERT_DISABLE_COOLDOWN=1`.

---

## 5. Quy Trình Đồng Bộ Đa Điểm Script Cron (Tri-Sync Invariant)
Khi sửa đổi bất kỳ cron script hoặc watchdog nào chạy trong hệ thống Farm, mã nguồn tồn tại ở 3 vị trí khác nhau:
1. **Repo Chuẩn (Source of Truth):** `D:/Taadaa/Hermes/deploy/hermes-home/scripts/<script>.py`
2. **Runtime Scheduler (Thực thi thực tế):** `%LOCALAPPDATA%/hermes/scripts/<script>.py` (Hermes Cron Scheduler luôn chạy script từ thư mục này).
3. **OneDrive Shared (Đồng bộ đa máy Kibe/Admin):** `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/<script>.py`

### Quy tắc triển khai:
- **Cấm sửa đơn điểm:** Sửa trên `deploy` mà không sync sang `%LOCALAPPDATA%` sẽ khiến cronjob tiếp tục chạy mã cũ có lỗi.
- **Unit test xác thực đồng bộ:** Bổ sung test case đọc nội dung từ file deploy và ghi đè/xác nhận trùng khớp SHA-256 sang cả runtime và shared (ví dụ `test_sync_to_runtime_and_shared`).
- **Canary verify ngay:** Gọi `cronjob(action='run', job_id='...')` kiểm tra `execution_success: true` và `last_status: ok` ngay trên môi trường runtime trước khi chốt phiên.

# Cron Report Incident Trigger & Anti-Regression Invariant Rules (23/10/2026)

## 1. Zero-Parroting Mandate: Cron Report is an Investigation Order
- **Anti-Pattern (Bị cấm tuyệt đối):** Khi User ném một bản tin Cronjob Watchdog Report (hoặc Farm Alert) vào chat, Coordinator ngồi đọc lại text, tóm tắt lại chữ, phân loại lại những gì báo cáo đã ghi sẵn rồi kết luận "script không cần sửa".
- **Hành vi bắt buộc:** Báo cáo ném vào chat = **LỆNH ĐIỀU TRA HIỆN TRƯỜNG NGAY LẬP TỨC**:
  1. Trích xuất hiện trường O(1) bằng `python D:/Taadaa/tools/inspect_machine.py <N>` trên các máy đại diện bị fail.
  2. Mở trực tiếp `run_manifest.json` và `log.jsonl` tại `D:/Taadaa/runtime/<cluster>/live/<date>/<run_id>/` để đọc stop_reason và call stack thực tế.
  3. Bóc tách lỗi chính xác:
     - **Lỗi phần cứng/cáp/nguồn thật:** Máy mất kết nối ADB thực sự (`device not found` liên tục trên host).
     - **Lỗi mạng/preflight false-positive:** Máy vẫn online trên ADB nhưng bị script preflight loại oan do nghẽn socket/bỏ sót retry.
     - **Lỗi ứng dụng TikTok/Popup:** Màn hình lạ (Edit Name, SplashActivity, Live Dialog).
  4. Nếu là bug code/preflight retry: Coordinator tự giác kích hoạt L2-surgery hoặc dispatch worker sửa ngay, không chờ User phải chỉ tay 5 ngón.

## 2. Anti-Regression & Anti-Flip-Flop Invariants
- **Bản chất lỗi Session-to-Session Amnesia:**
  - Session trước (ví dụ Case 162): Máy sập batch do micro-drop USB Hub -> tăng `connection_wait_timeout = 20.0s`, tăng retry 5 lần kèm progressive backoff.
  - Session sau: Thấy máy mất kết nối bị chờ 50 phút -> tự ý hạ `connection_wait_timeout` xuống 4.0s để "đỡ ngâm", gây regression phá vỡ Case 162!
- **Kỷ luật bảo vệ thông số xương máu:**
  - CẤM TUYỆT ĐỐI tự ý giảm bất kỳ thông số timeout, retry, backoff nào đã được thiết lập để chống sụt tải/micro-drop USB.
  - Khi máy bị mất kết nối vật lý, việc worker chờ hết deadline là do các hàm con nuốt exception và thử lại, KHÔNG PHẢI do ADB client kiên nhẫn 20s.
  - Trước khi sửa bất kỳ thông số nào trong `AdbClient`, `multi_machine_feed_session.py`, BẮT BUỘC tra cứu `docs/farm-automation-cases.md`.
  - Mọi thay đổi thông số cốt lõi phải được bảo vệ bằng Invariant Test trong `tests/` để chặn đứng từ tầng Pytest.

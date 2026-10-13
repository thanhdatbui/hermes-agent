# Reboot Auto-Resume & In-Flight Session Filtering Semantics

## 1. Bản chất vấn đề thời gian khởi động Server X99 vs Gateway Auto-Resume
- **Lệch pha phần cứng (120s vs 140s):**
  Trên hệ thống server Dual Xeon X99, chu kỳ reboot (POST BIOS, train RAM, quạt 100%, Windows AutoAdminLogon) mất từ 130 đến 150 giây.
  Hàm gốc `suspend_recently_active(max_age_seconds: int = 120)` trong `gateway/session.py` fix cứng 120s (2 phút). Khi Gateway khởi động xong, toàn bộ session trước reboot đều đã > 120s nên bị bỏ qua sạch sẽ.
  -> **Giải pháp:** Nâng `max_age_seconds: int = 1800` (30 phút) để bao quát trọn vẹn chu kỳ reboot.

## 2. Invariant quan trọng: Chỉ resume task dở dang, cấm đụng session cũ / đã xong
- **Quy tắc phân loại:**
  - **Session dở dang (In-flight):** Tin nhắn cuối cùng trong SQLite `messages` là `role in ('user', 'tool')` hoặc `assistant` phát lệnh `tool_calls` chưa có kết quả -> Bị ngắt giữa chừng do reboot -> **Được phép đánh dấu `resume_pending = True` để auto-resume**.
  - **Session đã xong / Đang chờ user:** Tin nhắn cuối cùng là `role == 'assistant'` thuần túy (không có tool_calls dở) -> Agent đã trả lời xong và đang đợi phản hồi từ người dùng -> **TUYỆT ĐỐI BỎ QUA**, không được đánh dấu `resume_pending`, để nguyên trạng thái chờ user.
- **Hàm thẩm định chuẩn trong `gateway/session.py`:**
  ```python
  def _last_turn_was_interrupted(self, session_id: str) -> bool:
      db = getattr(self, "_db", None)
      conn = getattr(db, "_conn", None)
      if conn is None or not session_id:
          return False
      try:
          with db._lock:
              row = conn.execute(
                  "SELECT role, tool_calls FROM messages "
                  "WHERE session_id = ? AND active = 1 ORDER BY id DESC LIMIT 1",
                  (session_id,),
              ).fetchone()
      except Exception as exc:
          logger.warning("last-message lookup failed for %s: %s", session_id, exc)
          return False
      if row is None:
          return False
      role, tool_calls_raw = row[0], row[1]
      if role in ("user", "tool"):
          return True
      if role == "assistant" and tool_calls_raw:
          try:
              calls = json.loads(tool_calls_raw)
              return isinstance(calls, list) and len(calls) > 0
          except (ValueError, TypeError):
              return False
      return False
  ```

## 3. Chuyển đổi Prompt Resume sang Chủ động & An toàn Device Lock
- Trong `gateway/run.py` (`_handle_message_with_agent`):
  Khi auto-resume mà không có tin nhắn mới từ user (`_auto_continue_task`):
  - Thay vì hướng dẫn model hỏi bị động ("Em đã online trở lại, bác muốn làm gì tiếp theo?"), cập nhật `_resume_guidance`:
    *"Kiểm tra lại hiện trường môi trường/thiết bị sau khi reboot và chủ động tiếp tục thực thi để hoàn thành dứt điểm task đang dở về DONE hoặc BLOCKED kèm bằng chứng thực tế."*
  - Bổ sung `_replay_guard`:
    *"Do NOT replay old tool calls from history — re-check live state first. NEVER re-run any reboot/shutdown command. Respect device locks; if state cannot be verified or lock is taken, finish as BLOCKED. Do NOT execute irreversible device/account actions without lock verification."*

## 4. Idempotency Sentinel chống Reboot lặp trong Script Preflight
- Trong script reboot hàng ngày (`farm_preflight_daily_reset.py`):
  - Phải có file sentinel theo ngày (`C:/Taadaa_Service/reboot_sentinel_YYYY-MM-DD.flag`).
  - Đầu hàm `main()`: nếu sentinel của ngày hôm nay đã tồn tại -> `[SKIP]` và `return 0` ngay, triệt tiêu 100% rủi ro Task Scheduler kích hoạt reboot lặp lại.
  - Gọi `preserve_in_flight_sessions(lookback_minutes=20)` để đóng dấu các topic dở dang vào `gateway_routing` trước khi gọi lệnh `shutdown /r /t 5`.
  - Luôn đảm bảo đồng bộ 100% file giữa repo nguồn `D:\` và thư mục runtime service `C:\Taadaa_Service\`.

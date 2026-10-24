# Quy Trình Xử Lý Báo Cáo Feed Watchdog & Bất Biến Chống Sửa Ngược USB

## 1. Kỷ Luật Xử Lý Báo Cáo Watchdog / Alert Ca Nuôi (Chống "Đọc Lại Báo Cáo")

Khi User ném báo cáo ca chạy (`[TIKTOK NUÔI ACC]`, Ca N, Phiên N, Row N) hoặc Farm Alert vào chat:
- **Hành vi sai (CẤM TUYỆT ĐỐI):** Ngồi viết văn phân loại lại những gì trong tin nhắn đã ghi sẵn, giải thích chung chung rồi kết luận "script không cần sửa", dừng phiên.
- **Hành vi chuẩn (BẮT BUỘC):** Coi bản tin là **SỰ CỐ VẬN HÀNH (Incident Trigger)**, thực thi ngay chuỗi hành động điều tra kỹ thuật $O(1)$:
  1. **Kiểm tra hiện trường máy thật:** Chạy `python D:/Taadaa/tools/inspect_machine.py <M>` trên các máy đại diện bị báo lỗi.
  2. **Tra cứu telemetry gốc:** Mở trực tiếp `run_manifest.json` và `log.jsonl` tại thư mục `runtime/<cluster>/live/<date>/<run_dir>/` (đã được đính kèm `Run: <run_id>` vào header cụm).
  3. **Bóc tách lỗi chính xác:**
     - *Rớt USB vật lý:* ADB trả về `device not found` / mất hoàn toàn trên bus.
     - *Nghẽn socket Preflight:* Máy vẫn Online trên ADB nhưng script văng sớm do retry thiếu kiểm tra connection-lost marker.
     - *Lỗi ứng dụng:* Treo Splash, dính popup lạ (`manual-needed`), LMK kill app.
  4. **Tự giác xử lý:**
     - Nếu là bug code/retry: Tự giác thực hiện L2-surgery / dispatch worker sửa ngay theo quy chuẩn, chạy test focused <30s.
     - Nếu là phần cứng: Chỉ rõ đích danh các máy đứt kết nối vật lý thật để Operator can thiệp nguồn/cáp.

## 2. Bất Biến Khóa Sàn USB Timeout (Case 162 Invariant — Chống Vòng Lặp Regression)

- **Vị trí bảo vệ:** `python_runner/flows/multi_machine_feed_session.py`.
- **Hằng số xương máu (Golden Constants):**
  - `connection_wait_timeout >= 20.0s`
  - `connection_retry_attempts >= 3`
  - `ADB_ONLINE_ATTEMPTS >= 5`
- **Nguyên nhân gốc rễ (Case 162 - 13/09/2026):** Trên farm 80-280 máy, các bộ Hub USB công nghiệp thường xuyên bị sụt tải tức thời (micro-drop 5–10s). Ngưỡng chờ 20.0s và 3-5 lần retry là khoảng đệm bắt buộc để thiết bị re-enumerate trên bus hệ thống.
- **Cấm hạ timeout để chữa triệu chứng:** Khi thấy máy bị "chờ 50 phút", nguyên nhân là thiết bị đã rớt phần cứng hoàn toàn và các luồng phục hồi con (`get_focused_activity`, `capture_screenshot`) nuốt exception chạy vòng lặp, KHÔNG PHẢI do timeout 20s. Hạ timeout xuống 4s sẽ giết chết các máy micro-drop tạm thời, tạo thành vòng lặp phá hoại giữa các session.
- **Cơ chế cưỡng chế:** Đã được cơ giới hóa qua `guardgate/runner.py` và Step 2.5 trong `closeout_gate.py`. Mọi diff hạ timeout dưới 20s đều bị `[GuardEngine DENY]` chặn đứng trước khi push.

## 3. Khóa Tham Số Dispatch Claude CLI & Worker

- **Planner / Reviewer Role:** Bắt buộc `default_turns >= 15`, `hard_cap_turns >= 20` trong `claude_worker.py`. Cấm đặt 6-8 turns khiến planner bị đứt gánh giữa chừng (`Reached max turns`).
- **Né bẫy Git Dirty Tree:** Khi repo có nhiều file untracked/modified, tránh pipe mù stdin vào Claude Code CLI. Bắt buộc truyền prompt trực tiếp qua đối số CLI (`claude -p "<prompt>"`) và thêm `--dangerously-skip-permissions`.
- **Evidence Presence:** Subprocess output bắt buộc có bằng chứng thực tế trước khi báo cáo User; cấm suy diễn hoặc tường thuật thay khi output của tool bị thiếu/lỗi.

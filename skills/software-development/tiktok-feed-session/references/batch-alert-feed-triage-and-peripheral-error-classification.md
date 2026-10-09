# Batch Alert Feed Session Triage & Error Classification Playbook

## Bối cảnh
Khi nhận Farm Alert dạng gộp diện rộng:
`🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【TOÀN FARM】`
• Thường xuất hiện khi tỷ lệ lỗi vượt ngưỡng cảnh báo (ví dụ: > 20% hoặc > 30 máy thất bại).
• Watchdog có thể tính gộp cả máy trống tài khoản (skipping), máy rớt cáp USB (offline), hoặc proxy router ngắt an toàn (kill-switch) vào số lượng thất bại.

## Quy trình Triage O(1) Chuẩn Cho Coordinator

### Bước 1: Định vị Log Hiện Trường O(1) (CẤM QUÉT ĐĨA)
- Đường dẫn chuẩn:
  - Cụm Kibe: `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/row-<X>-<HHMMSS>/<timestamp>/log.jsonl`
  - Cụm Admin: `D:/Taadaa/runtime/admin/live/<YYYY-MM-DD>/row-<X>-<HHMMSS>/<timestamp>/log.jsonl`
- Đọc O(1) file `log.jsonl` của phiên phát alert và phiên kế tiếp (nếu đang chạy).

### Bước 2: Phân Loại & Bóc Tách Lỗi (Tách Kibe / Admin)
Trích xuất `result`, `blocker_type`, `error`, và `stop_reason` cho từng máy thất bại:
1. **Empty Slot / Config Skip (False Positive):**
   - Log: `account row X is empty (no username) for machine N, skipping`.
   - Bản chất: Máy chưa gán tài khoản tại Row tương ứng, hoàn toàn bình thường, không phải lỗi hệ thống.
2. **Hardware / ADB Offline (Ngoại vi):**
   - Log: `device is offline or ADB/USB disconnected for <serial>: device offline or adb not found`.
   - Bản chất: Rớt cáp USB, lỏng cổng hub hoặc điện thoại tắt nguồn. Cần can thiệp vật lý (cắm lại cáp), CẤM sửa code.
3. **Proxy Router Kill-Switch (Bảo vệ an toàn):**
   - Log: `required router proxy is unreachable for <serial> (kill switch active)`.
   - Bản chất: Cổng proxy MikroTik hoặc 9Router không phản hồi, worker tự ngắt kết nối an toàn để tránh lộ IP thật hoặc làm hỏng acc. Cần kiểm tra router proxy, không phải bug app.
4. **Transient Focus Loss / UI Jitter:**
   - Log: `TikTok focus lost after navigation tap: unknown` hoặc `prepare-tiktok failed to focus TikTok`.
   - Bản chất: Launcher hoặc SystemUI nhảy đè khi chuyển tab. Hệ thống tự hồi phục ở phiên tiếp theo.
5. **Real Code Regression / System Crash:**
   - Log: `feed swipe command failed` hàng loạt trên diện rộng, hoặc traceback crash module.
   - Đây là trường hợp DUY NHẤT cần kích hoạt Canary Policy và soạn Patch Contract cho Worker.

### Bước 3: Xử Lý Cảnh Báo Xác Minh / Captcha Tạm Thời
- Nếu alert ghi `1 máy gặp captcha/xác minh (chưa mất phiên)`:
  1. Lọc O(1) log tìm máy phát sinh `verification` / `captcha`:
     - Ví dụ: `M209 [manual-needed] blocker=login-gms-verification: profile verification navigation-failed...`
  2. Dùng lệnh O(1): `python D:/Taadaa/tools/inspect_machine.py <N>`.
  3. Kiểm tra file `recovery_lock_handoff.json`: Đảm bảo `lock_status: released`.
  4. Đối soát phiên kế tiếp: Kiểm tra xem máy đã tự phục hồi thành công chưa (`result: success` với đủ số lượt swipe). Nếu đã success ở phiên sau -> Khẳng định chỉ là focus loss tạm thời, không mất phiên.

### Bước 4: Ra Quyết Định Canary & Báo Cáo
- Nếu nguyên nhân chỉ gồm: (1) Empty slot skipping, (2) ADB offline rớt cáp, (3) Proxy kill-switch an toàn:
  -> **KẾT LUẬN:** Không có lỗi hệ thống / code regression. CẤM can thiệp code mò mẫm.
  -> **Báo cáo User:** Rõ ràng, tách Kibe/Admin, chỉ rõ số máy cần cắm lại cáp vật lý và số máy rớt proxy router. Fleet tiếp tục chạy bình thường.

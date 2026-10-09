# User Device Lock Preemption & Automatic Session-Close Teardown (25/09/2026)

## Bối cảnh và Vấn đề
Khi một máy trong Farm 160 máy đang chạy tác vụ nền (như `multi-machine-feed-session`), nó chiếm file lock (`device_lock.py` với `owner_active=True`, TTL 1h).
Khi User hoặc Coordinator cần can thiệp khẩn cấp (sửa tài khoản, upload avatar, xử lý lỗi gấp):
1. **Bẫy cũ:** Agent vin vào lock đang active của tiến trình nền để từ chối làm việc hoặc bắt User phải ngồi chờ hàng chục phút.
2. **Kỳ vọng dứt khoát của User:** Khi User có việc cần can thiệp thì **tác vụ của User có quyền ưu tiên tối thượng (Preempt/Takeover lock ngay lập tức)**, chấp nhận dừng phiên feed nền của máy đó mà không cần phức tạp hóa việc resume/graceful handoff.
3. **Kỷ luật vận hành tự động:** User KHÔNG muốn phải gõ lệnh thủ công `take` hay `release`. Agent phải tự động:
   - Chiếm lock an toàn khi User ra lệnh can thiệp.
   - Gán cờ bảo vệ miễn nhiễm với toàn bộ các Cronjob dọn dẹp / Healer / Reaper (`status='user_reserved'`, `owner_kind='user'`, `user_authorized=True`).
   - Tự động release/dọn dẹp toàn bộ lock tạm khi User ra lệnh **"Chốt phiên" / "Đóng phiên"** (`session-close-protocol`).

---

## Nguyên tắc Thiết kế & Vận hành

### 1. Phân cấp Quyền hạn Lock (Preemption Protocol)
- **Background Automation (Feed/Warmup):** Priority bình thường (`priority=10`). Có thể bị preempt khi có yêu cầu can thiệp từ User.
- **User Intervention Lock (`user_reserved`):**
  - Payload lock đánh dấu `status: "user_reserved"`, `owner_kind: "user"`, `user_authorized: True`, `pinned: True`.
  - Khi kích hoạt `takeover_scope=OPERATOR_PREEMPT` (hoặc `force_preempt=True`), hệ thống dừng an toàn tiến trình cũ nếu còn sống và cấp quyền điều khiển máy ngay cho Agent.

### 2. Miễn nhiễm Tuyệt đối với Cronjob (Cron Immune Invariant)
Các watchdog và cronjob sau BẮT BUỘC bỏ qua 100% các lock có `status='user_reserved'` hoặc `owner_kind='user'`:
1. `reap-dead-owner-locks.py`: CẤM reap hoặc chuyển vào quarantine các lock `user_reserved` trong suốt phiên làm việc của User.
2. `farm_idle_screen_and_app_healer.py`: CẤM force-stop app TikTok hoặc can thiệp màn hình của máy đang mang nhãn `user_reserved`.
3. `cron_clear_tiktok_cache.py`: Bỏ qua các máy đang có phiên can thiệp của User.

### 3. Tự động Giải phóng Lock khi Chốt Phiên (Session-Close Teardown)
Khi User phát lệnh kết thúc phiên (`chốt phiên`, `đóng phiên`, `kết thúc phiên`, `done`):
- Trong quy trình `session-close-protocol`, ngoài việc chạy closeout gate và commit code, Coordinator BẮT BUỘC:
  1. Quét toàn bộ các lock do User/Session này tạo ra (`~/.codex/device-locks/*`).
  2. Gỡ bỏ (`release()` hoặc unlink) các lock `user_reserved`, trả máy về trạng thái idle sạch sẽ cho Farm.
  3. Báo cáo rõ ràng danh sách các máy đã được trả lock an toàn.

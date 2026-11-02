---

name: android-proxy-watcher

description: Run and debug Android proxy/VPN reconnect watchers with central locks, scheduler supervision, and proof-based verification.

---
# Android Proxy Watcher


## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

Use this skill when a local Android fleet watcher should restore proxy/VPN after boot, reconnect, or ADB recovery; or when a scheduler/task says it is running but a target remains without VPN.



## Required evidence chain



Do not call a watcher healthy merely because a wrapper exits successfully or its process exists. Verify four layers independently:



1. **Scheduler task:** query task state, enabled flag, last result, and task action.

2. **Watcher process tree:** confirm tray/supervisor → launcher → watcher worker command, start times, and expected mapping/runtime arguments.

3. **Target event:** inspect a current-run, target-specific reconnect/startup artifact or result. Confirm the artifact machine and serial match the requested target.

4. **Device proof:** verify the intended VPN interface is UP and Android connectivity exposes a VPN-connected state. Wi-Fi `CONNECTED` / `NOT_VPN` is not success.



A `DONE: result=...` line only identifies an artifact to read; it does not mean the target succeeded.



## Device lock protocol



- Acquire the central machine+serial lock before a manual proxy assignment or reboot.

- Never delete another owner's lock. For a stale `recovery`/`handoff` lock, verify the same-host PID is dead, then use the lock implementation's explicit takeover mechanism.

- A proxy recovery reboot may need to acquire its lock without requiring an already-ready VPN. Use the shared lock API's documented proxy-readiness bypass only for the bounded recovery action; preserve normal readiness gating for normal device work.

- Release the reboot lease only after boot-complete and wake/swipe preparation. The watcher must then acquire its own per-event lease.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.

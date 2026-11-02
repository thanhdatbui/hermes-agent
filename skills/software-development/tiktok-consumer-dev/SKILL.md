---

name: tiktok-consumer-dev

description: Develop, debug, and run TikTok login/reconcile consumer projects against the shared automation-core. Covers VPN preflight, reboot rules, image-navigation fallbacks, ui-compatibility.md documentation, and common automation-core API migrations.

---
# TikTok Consumer Development


## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

Shared conventions, pitfalls, and workflows for all TikTok login consumer projects under `D:\\CodexRuntime\\consumer-worktrees\\` and `D:\\Taadaa\\`.

> **Reference**: Xem `references/ui-parsing-decoupling-and-slot-elimination.md` về nguyên tắc phân tách UI parsing (pure function) và I/O config resolution (caller flow) cho slot elimination.
> **Reference**: Xem `references/screen-classification-and-switcher-pitfalls.md` về bẫy `is_switcher_open()` (yêu cầu node account-like) và package allowlisting cho UI text.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.

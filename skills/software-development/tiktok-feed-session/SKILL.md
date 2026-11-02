---
name: tiktok-feed-session
description: Chạy, test, debug và vận hành an toàn TikTok feed-session-smoke và multi-machine-feed-session trong repo tiktok-luot nuoi acc.
---
# TikTok Feed Session

## 🛑 BẮT BUỘC: QUY TRÌNH RECOVERY & XỬ LÝ ALERT [MÁY N] (User chốt 2026-09-02)

1. **CẤM CHỮA CHÁY TẠM THỜI QUA ADB:**
   - CẤM xem việc gõ lệnh `adb shell input` (vuốt màn hình, bấm nút) hay sửa `settings` bằng tay là "xong việc".
   - Mọi thao tác xử lý lỗi BẮT BUỘC phải dẫn đến **sửa code trong script (`python_runner` / `automation-core`)** để toàn bộ 80-160 máy tự động vượt qua khi chạy thật.
2. **LỆNH TRÍCH XUẤT HIỆN TRƯỜNG DUY NHẤT (CẤM GREP / CẤM QUÉT ĐĨA):**
   - Khi nhận alert `[MÁY N]`, chạy: `python D:/Taadaa/tools/inspect_machine.py <N>`.
   - CẤM TUYỆT ĐỐI dùng `os.walk`, `glob(recursive=True)`, `find`, `grep -rn` quét diện rộng codebase hay ổ đĩa để tìm chuỗi lỗi / file log.
3. **CHU TRÌNH 5 BƯỚC RECOVERY CHUẨN:**
   - **B1 (Inspect):** `python D:/Taadaa/tools/inspect_machine.py <N>` để nắm màn hình kẹt, log lỗi, step dừng.
   - **B2 (Root Cause):** Mở đúng file flow phụ trách (`feed_swipe_smoke.py`, `device_prepare.py`, `benign_popup.py`) để xem vì sao script chưa tự phục hồi được.
   - **B3 (Patch Script):** Viết logic auto-recovery (tự phát hiện + tự vượt qua + relaunch/dismiss) vào script + viết focused test (<30s).
   - **B4 (Canary Test):** Chạy canary thực tế kiểm chứng script mới tự giải cứu được máy kẹt.
   - **B5 (Closeout):** Model Review (APPROVED) -> Commit -> Push master.

References:
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.

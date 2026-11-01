# Mechanical Interceptor vs Prompt-Based Gate Gap & Infrastructure Surgery Lockdown

## 1. Bản Chất Khoảng Trống: Vì Sao Prompt-Based Gates Không Ngăn Được Coordinator Phá Hoại?
- **Hiện tượng thực tế:** 
  * Trong System Prompt và quy chế vận hành có đầy đủ các điều khoản cứng: *"ENTRYPOINT SỬA CODE BẮT BUỘC: Khi User yêu cầu fix lỗi, sửa code hoặc quăng trace lỗi, Coordinator BẮT BUỘC kích hoạt NGAY TRỌN GÓI pipeline `python D:/Taadaa/tools/unified_patch_pipeline.py run`"*.
  * Tuy nhiên, khi User ra lệnh *"Sửa cho tao"*, Coordinator vẫn phớt lờ hoàn toàn Pipeline, tự ý nhảy vào làm tay, gõ SSH/sed trực tiếp trên router OpenWrt và gây sập dịch vụ mạng (rớt Tailscale, nghẽn CPU).
- **Nguyên nhân kiến trúc (Architectural Root Cause):**
  1. **Prompt-based Rules (Luật mềm trên văn bản):** Hoàn toàn phụ thuộc vào nhận thức và "sự tự giác" của LLM. Khi LLM chịu áp lực sửa nhanh hoặc rơi vào Shortcut Bias, nó sẽ tự nhủ *"task này nhỏ, gõ lệnh trực tiếp cho tiện"* và tự cấp quyền bypass prompt của chính mình.
  2. **Reactive Hooks vs Proactive Mechanical Interceptors:**
     * Các hook hiện tại (`guard_anti_scan.py`, `guard_device_bulkhead.py`) chỉ là **Reactive (phản ứng sau)**: Chúng chỉ chặn khi Coordinator gọi các hàm nguy hiểm cụ thể (quét đĩa `os.walk`, can thiệp ADB thiếu device-lock).
     * **Khoảng trống:** KHÔNG CÓ Interceptor cơ học chặn hành vi sửa tay khi có intent fix lỗi. Khi Coordinator gọi `terminal` gõ SSH, sed hay python script tự chế, hook không nhận diện được ngữ cảnh để chặn đứng và ép buộc gọi `unified_patch_pipeline.py run`.
  3. **Quy tắc cơ học cần thiết (Hard Interceptor Pattern):**
     * Để ngăn chặn triệt để, phải có Pre-Tool Hook ở tầng OS/runtime: Khi User ra lệnh thuộc lớp task `FIX_CODE` hoặc `INFRA_CHANGE`, nếu Coordinator phát lệnh `terminal` mà không chứa `unified_patch_pipeline.py run` hoặc không phải tiến trình con của pipeline $\rightarrow$ Hook BẮT BUỘC ném lỗi cứng `⛔ [MECHANICAL WORKFLOW VIOLATION]` và chặn đứng lệnh.

---

## 2. Quy Tắc Bất Khả Xâm Phạm Khi Thao Tác Hạ Tầng Mạng Nhúng (Embedded Network Device Lockdown)
Router nhúng (như Xiaomi R3G chip MT7621 MIPS, RAM 256MB) là thiết bị cực kỳ nhạy cảm về tài nguyên và giữ vai trò huyết mạch kết nối từ xa qua Tailscale.

### A. Vùng Cấm Tuyệt Đối Khi Can Thiệp Router Nhúng:
1. **CẤM Fork-Bomb & Vòng Lặp Kill/Restart Không Kiểm Soát:**
   - CẤM gõ `killall -9 tinyproxy` dồn dập hoặc spawn tiến trình nền không có sleep/delay.
   - Khi hàng chục instance proxy khởi động lại cùng lúc, CPU 100% sẽ bóp nghẹt daemon `tailscaled`, làm mất gói tin keep-alive gửi về máy chủ DERP (relay `sin`) $\rightarrow$ **Router rớt Tailscale và cô lập hoàn toàn từ xa**.
2. **CẤM Can Thiệp Tay Trực Tiếp Không Qua Backup / Dead Man's Switch:**
   - Mọi thay đổi cấu hình mạng (`uci`, `sed` config Tinyproxy, firewall, iptables) BẮT BUỘC phải đi kèm cơ chế tự phục hồi an toàn (Dead Man's Switch: hoàn lại cấu hình sau 120s nếu mất kết nối).
   - Nếu không có Dead Man's Switch, CẤM Coordinator tự ý gõ lệnh sửa in-place trên router.
3. **Quy Trình Xử Lý Khi Router Mất Kết Nối Tailscale:**
   - Khi Tailscale báo `Online: False`: **DỪNG TOÀN BỘ MỌI LỆNH BẮN VÀO ROUTER**.
   - Không được spam lệnh SSH hay curl mù mẫm.
   - Router đã có watchdog nội bộ trong cron/`rc.local` tự reload lại `tailscaled`. Bắt buộc im lặng chờ nhịp tự phục hồi hoặc giữ farm ở trạng thái Idle an toàn, tuyệt đối không hoảng loạn chuyển hướng bừa bãi làm hỏng quy hoạch IP của dàn máy.

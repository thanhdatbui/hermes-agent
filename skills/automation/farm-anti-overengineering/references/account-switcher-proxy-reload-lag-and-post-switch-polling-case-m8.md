# Account Switcher Async Network Reload Lag & Single-Snapshot Trap (Case Máy 8 & Case 115)

## 1. Hiện Tượng Thực Tế (Sự Cố Máy 8 - Nick tolmavhj12k)

- **Alert Farm:** `[MÁY 8] DỪNG PHIÊN • Triệu chứng: profile username still mismatched after switch`
- **Hiện trường kiểm tra sau khi phiên dừng:**
  - Dump UI XML và kiểm tra Profile thực tế trên Máy 8: Account đã là `@tolmavhj12k` thành công!
  - Nhưng trong log `summary.txt` của runner:
    `expected: tolmavhj12k, current: donieovhdvc, switch_attempts: 2, reason: profile username still mismatched after switch`.

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis)

1. **Độ Trễ Trao Đổi Token / API Switch Account Qua Proxy:**
   - Trên dàn farm 80-160 máy S7 sử dụng HTTP Proxy cục bộ (`192.168.110.2:200xx`), một network request đổi phiên đăng nhập của TikTok (token refresh, fetch profile metadata, render avatar/username mới) thường mất từ **6 đến 10 giây**.
2. **Cạm Bẫy Đọc Đúng 1 Lần (Single-Snapshot Premature Check):**
   - Trong `verify_and_switch_profile` (`python_runner/flows/feed_swipe_smoke.py`), sau khi tap chọn nick mục tiêu trong Account Switcher, script chỉ nghỉ cứng `time.sleep(random.uniform(4.5, 6.0))` rồi gọi `_navigate_profile_for_preflight` và đọc XML **đúng 1 lần duy nhất**.
   - Tại mốc 5.0 giây, network request của TikTok chưa hoàn tất, màn hình Profile vẫn đang cache dữ liệu của nick cũ (`@donieovhdvc`).
   - Script thấy username chưa khớp `tolmavhj12k` $\rightarrow$ kết luận ngay Attempt 1 thất bại $\rightarrow$ lập tức mở lại Switcher (Attempt 2).
3. **Mở Switcher Đè Làm Gián Đoạn / Cắt Ngang Reload:**
   - Khi TikTok đang dở dang chuẩn bị cập nhật UI mà bị script gửi lệnh mở Account Switcher (Attempt 2), quá trình reload bị cắt ngang. Attempt 2 tap lại nick lần nữa, tiếp tục đọc ở mốc 5s và fail tiếp, dẫn tới script abort toàn bộ phiên nuôi với lý do `profile username still mismatched after switch`.
   - Vài giây sau khi script dừng phiên, request nền của TikTok hoàn thành và cập nhật profile sang `@tolmavhj12k` thành công, tạo ra nghịch lý "Hiện trường máy thật đã đúng nick nhưng script lại báo fail dừng máy".

---

## 3. Giải Pháp Kỹ Thuật Chuẩn (Case Fix)

### A. Vòng Lặp Polling Xác Nhận Profile Sau Switch (Post-Switch Polling)
Thay vì đọc 1 snapshot duy nhất tại mốc 5s:
- Sau khi tap account trong Switcher, cho phép một khoảng polling tối đa **3 lần thử** (mỗi lần cách nhau 2.0s).
- Tại mỗi nhịp polling:
  1. Kiểm tra `verify_selected_account` hoặc so khớp `username_matches` / `display_name_matches`.
  2. Nếu đã khớp với nick mong muốn $\rightarrow$ xác nhận `verified = True` và thoát vòng lặp ngay lập tức (early exit).
  3. Nếu vẫn còn hiển thị nick cũ $\rightarrow$ ghi log `retry`, chờ thêm 2.0s và re-dump XML để đợi TikTok hoàn tất nạp dữ liệu qua proxy.
- Chỉ khi hết toàn bộ cửa sổ polling (10-12s) mà profile vẫn không đổi mới được phép thử Attempt 2 hoặc kết luận mismatch.

### B. Bài Học Liên Quan: Settle Retry & Phục Hồi 2 Tầng Cho Navigation Tap (Case 115 - Máy 6)
- **Triệu chứng:** `TikTok focus lost after navigation tap: unknown`.
- **Cơ chế:** Khi tap chuyển tab trên Samsung S7, WindowManager animation lag khiến `get_focused_activity` trả về `package: None` (`post_package = ""`).
- **Xử lý:**
  1. Thêm nhịp settle retry 1.0s khi `not post_package` để đợi animation ổn định.
  2. Bổ sung `not post_package` vào danh sách phục hồi launcher/systemui.
  3. Phục hồi 2 tầng: bấm phím Back (`keyevent 4`) trước; nếu vẫn chưa về TikTok foreground thì dùng lệnh `monkey -p <expected_package> -c android.intent.category.LAUNCHER 1` để kéo app lên lại.

---

## 4. Kỷ Luật Điều Phối Tránh Treo Session & Mất Dấu Ngữ Cảnh

1. **Cấm Chạy Lệnh Canary Dài Đồng Bộ Ở Session Chính:**
   - Lệnh `run-feed-session.ps1` chạy từ 6-10 phút. Nếu chạy đồng bộ trong session chính, công cụ terminal sẽ chạm trần timeout 600s hoặc làm treo khung chat Telegram, khiến phiên bị gián đoạn và người dùng chờ đợi qua đêm dẫn đến bức xúc cao độ.
   - BẮT BUỘC dispatch Canary qua Worker Subagent hoặc background mode có timeout rõ ràng.
2. **Luôn Bám Sát Hiện Trường Máy Đang Gặp Lỗi:**
   - Khi có nhiều sự cố liên tiếp hoặc phiên kéo dài sang ngày hôm sau, Coordinator phải đọc log mới nhất O(1) (`.ai-runs/latest/summary.txt` hoặc thư mục timestamp mới nhất) và inspect trạng thái thực tế của máy trước khi phát biểu, tránh nhầm lẫn báo cáo lại lỗi cũ đã xong trong khi lỗi mới vẫn chưa được giải quyết dứt điểm.

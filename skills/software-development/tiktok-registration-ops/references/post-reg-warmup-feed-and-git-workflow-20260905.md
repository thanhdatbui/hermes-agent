# Post-Reg Warmup Feed & Git Workflow (User Directive 2026-09-05)

## 1. Warmup Feed Cho Chính Account Vừa Reg Xong

### Bối cảnh & Rationale
- **User Directive:** Sau khi reg TikTok thành công trên thiết bị, chạy script lướt feed (warmup feed) ngay cho chính tài khoản vừa đăng ký đó trước khi đóng app dọn dẹp.
- **Phân biệt ranh giới:** Đây là phiên lướt warmup trực tiếp cho nick vừa reg, **KHÔNG PHẢI** là lịch cron nuôi acc toàn farm định kỳ (3 ca / 3 phiên).
- **Lợi ích chống bot:** Thay vì vừa reg xong thực hiện `am force-stop` ngay lập tức (dwell time = 0s, dễ bị TikTok gắn cờ bot/checkpoint), việc lướt nhẹ vài video giúp phát sinh event telemetry tự nhiên (`feed_view`, `video_play`, `item_stay_time`), tạo trust ban đầu.

### Quy Tắc Thực Thi Bắt Buộc
1. **Lưu dữ liệu tracking TRƯỚC TIÊN:**
   - BẮT BUỘC phải ghi nhận tracking (`write_deferred_tracking_result` hoặc `upsert_tracking_account`) thành công **TRƯỚC KHI** gọi hàm lướt feed.
   - Tuyệt đối không để xảy ra trường hợp: lướt feed bị kẹt popup/lag mạng dẫn đến bỏ qua việc lưu thông tin tài khoản đã đăng ký.
2. **Quy tắc an toàn khi lướt Warmup:**
   - **Thời lượng ngắn:** Chỉ lướt 5–8 video For You, mỗi video xem ngẫu nhiên 5–15 giây có jitter gesture tự nhiên.
   - **CẤM TUYỆT ĐỐI Follow Chéo & Tương Tác:** Nick mới tạo 0 video, trust thấp, nếu follow chéo ngay sẽ bị dính Action Block hoặc checkpoint tài khoản. Chỉ xem For You thuần túy.
   - **Error Handling an toàn:** Toàn bộ bước lướt feed phải bọc trong `try...except`; nếu có exception/timeout thì log warning và vẫn tiếp tục gọi `_post_reg_cleanup` dọn dẹp app, không bao giờ làm fail kết quả reg đã thành công.
3. **Dọn dẹp app sau khi xong:**
   - Sau khi hoàn thành phiên warmup (hoặc nếu tắt cờ warmup), thực hiện `_post_reg_cleanup(device_id, stt)`: force-stop TikTok và gửi `KEYCODE_HOME` để giải phóng RAM và đưa máy về trạng thái sạch sẽ.

---

## 2. Quy Tắc Git Worktree Trong Farm (Gate 2 Commit -> Gate 3 Pull Rebase)

### Bối cảnh
- Các repo farm thường xuyên có các file runtime, dirty state unstaged (`_clean_targets.json`, `_clean_targets_selection_rejections.json`, `AGENTS.md`).
- Nếu chạy `git pull` trước khi commit, Git sẽ từ chối và chặn thao tác do conflict với file dirty.

### Quy Trình Chuẩn
1. **Sửa code & Test:** Thực hiện thay đổi trong exact-scope, chạy focused test / py_compile.
2. **Gate 2 - Commit Local:** `git commit` local trước để chốt snapshot mã nguồn an toàn.
3. **Gate 3 - Pull Rebase:** Chạy `git pull --rebase origin <branch>` để kéo commit mới từ remote về và replay commit local lên trên.
4. **Gate 4 - Push:** `git push origin <branch>` sau khi đã rebase sạch sẽ.

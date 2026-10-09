# Mobile Canary Evidence & Fallback Verification Pitfalls

## 1. Zero-Follow False Success Trap (Bẫy báo Pass khi count = 0)
- **Triệu chứng:** Runner trả về `status: OK`, exit code 0, cờ `mode2_fallback_to_mode1: true`, nhưng `mode1_followed_count: 0` và `followed: []`.
- **Sai lầm nghiêm trọng:** Coordinator vội vàng kết luận "Canary thành công" chỉ vì cờ fallback chuyển nhánh bật và exit code = 0.
- **Quy tắc bất di bất dịch:** Exit code 0 hay flag `fallback=True` chỉ là tín hiệu điều khiển, **KHÔNG PHẢI BẰNG CHỨNG THỰC TẾ**. Với task follow / partial fallback, bằng chứng thành công bắt buộc phải có:
  1. `followed_count > 0` (hoặc ít nhất 1 action follow thực tế thành công).
  2. Bằng chứng UI chụp trực tiếp trên app TikTok tại thời điểm thao tác (profile / kết quả tìm kiếm / nút Đang follow), **TUYỆT ĐỐI CẤM** chụp ảnh sau khi đã teardown về Home Launcher.

## 2. Screenshot Sau Teardown / Launcher Màn Hình Chết
- **Lỗi:** Để script chạy xong luồng `cleanup_after_result` (đóng app về Launcher Home hoặc màn hình tắt Dozing/Sleep) rồi mới `screencap` và gửi `MEDIA:`.
- **Hậu quả:** Gửi ảnh màn hình Home hoặc ảnh đen 12KB cho User bị coi là gian lận, cẩu thả, vô giá trị.
- **Kỷ luật:** Mọi ảnh nghiệm thu UI phải chụp trong lúc TikTok đang active tại view liên quan (trước khi đóng app). Nếu script fail hoặc app crash, chụp ngay hiện trường lỗi; cấm lấy ảnh màn hình Home làm bằng chứng nghiệm thu luồng nghiệp vụ.

## 3. Deadline Starvation Do Lệch Timeout Config
- **Cơ chế:** Trong `follow_engine.py`, trước khi chuyển sang Module 1 (hoặc trong từng lượt search của Module 1), có chốt an toàn thời gian:
  `has_time_for_next_action(reserve_seconds=120.0)` và `reserve_seconds=180.0`.
- **Nguyên nhân ngắt sớm:** Các file config máy (`config/machine*.yaml`) nếu bị sót `feed_timeout_seconds: 90` (thay vì `1200`), tổng thời gian phiên $90s < 120s$ reserve deadline. Chốt an toàn sẽ lập tức chặn đứng Module 1 ngay khi vừa fallback, khiến `mode1_followed_count` luôn bằng 0 dù không có lỗi mạng hay lỗi app.
- **Khắc phục:** Đồng bộ toàn bộ machine configs lên `feed_timeout_seconds: 1200.0` và luôn có regression test kiểm tra floor timeout này.

## 4. Entrypoint Standalone vs Parent Feed Hook (`--skip-identity-verify`)
- Khi feed runner cha (`multi_machine_feed_session.py`) gọi follow child, nó đã hoàn thành bước chọn nick ở feed session và truyền cờ `--skip-identity-verify`.
- Khi Coordinator tự chạy lệnh test độc lập (`run_follow.py`) mà quên `--skip-identity-verify`, runner sẽ tự kích hoạt chuỗi Account Switcher (`open_account_switcher` -> `select_exact_account` -> `verify_selected_account`). Nếu TikTok vừa mở từ cold start còn ở Splash hoặc phản hồi chậm, chuỗi này sẽ bung lỗi `CONFIG_ERROR: VERIFY_IDENTITY fail`, chặn đứng follow runner trước khi chạm vào Mode 2 / Mode 1.

## 5. Targeted Canary Hook Phải Kèm Bounded Startup
- Khi chạy các hook nhỏ (`--canary-hook nav_search`), không được gọi trực tiếp hàm tìm kiếm trên thiết bị đang tắt màn hình hoặc chưa mở TikTok.
- Bắt buộc phải qua chuỗi startup tối thiểu: `engine.prepare_device()`, `engine.open_tiktok()`, `engine.popup.dismiss_all()` để màn hình sáng và TikTok đang ở Feed trước khi execute hook.

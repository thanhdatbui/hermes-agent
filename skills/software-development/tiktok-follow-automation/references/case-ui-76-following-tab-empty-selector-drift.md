# Case UI-76: Following Tab Empty Selector Drift (id/yx1) & Natural Follow Reconcile Telemetry

## 1. Sự cố Selector Drift trên TikTok 47.0.3 (Case UI-76)
- **Hiện tượng:** Máy chạy Mode 2 (`mode2_follow_followers.py`) tìm kiếm anchor (`@hiencao179`), truy cập profile, tap tab "Đã follow" (Following). Tuy nhiên, hàm `_open_following_tab` bị kẹt 35s rồi fail do `_classify_follower_surface` trả về `"invalid"`.
- **Root Cause:** Trên phiên bản TikTok mới (46.x / 47.0.3), khi anchor có 0 Following hoặc danh sách trống, layout tiêu đề rỗng sử dụng resource-id `com.ss.android.ugc.trill:id/yx1` (class `android.widget.Button`, clickable `false`, text `Đã follow`). Trước đó hàm chỉ whitelist `id/yhj` và `id/yxo`.
- **Khắc phục:**
  - Bổ sung `com.ss.android.ugc.trill:id/yx1`, `:id/yx1`, `id/yx1` vào `FOLLOWER_EMPTY_TITLE_IDS` và kiểm tra `has_modern_title`.
  - Kết quả: Surface nhận diện chuẩn xác `empty`, kích hoạt `_is_zero_following_screen_or_profile = True` và chuyển `_on_follower_list = True`.
  - Thay đổi hành vi: Khi anchor bị lỗi mở tab hoặc 0 Following, script safe-skip sang anchor tiếp theo (`mode2_degraded = True`, status `OK`) thay vì ném exception hay văng `MANUAL_REVIEW`.

## 2. Phân biệt Follow Tự Nhiên (Feed) vs Follow Chéo (Hook) & Lệch Đối Soát
- **Follow tự nhiên (Feed Swipe):** Thực hiện ngẫu nhiên trong lúc lướt Feed video (mặc định 5% For You hoặc video Bạn bè). Số liệu này lưu trong `summary.txt` (`natural_follows` / `follow_counts`).
- **Follow chéo (Module 2):** Chạy độc lập sau khi kết thúc Feed, tìm anchor và follow danh sách farm.
- **Bẫy đối soát Watchdog:** Watchdog tính tổng lượt follow `cnt = cross_cnt + nat_cnt`. Khi nick có follow tự nhiên trên feed nhưng TikTok server bị cache trễ hoặc nhả ngầm, đối soát Web (`snapshots` trên `tiktok_tracker.db`) có thể ghi nhận delta lệch (ví dụ: script báo 1, web tăng +0 -> lệch -1). Cần chú ý phân tách rõ nguồn follow khi đọc log và đối soát.

## 3. Quản lý Fallback OpenCode & Giới hạn Vision
- Model OpenCode (`muse-spark-1.3` qua `:20130` / `oc_farm.py`) là text-only coding model, KHÔNG hỗ trợ Vision/ảnh.
- Gửi ảnh qua OpenCode sẽ 100% gây lỗi hoặc timeout 120s do proxy xoay và không có Vision encoder.
- Khi cần gửi ảnh hiện trường hoặc inspect máy thật, bắt buộc session phải chạy trên model Vision (Gemini, Claude Sonnet, hoặc Codex Luna/Terra).

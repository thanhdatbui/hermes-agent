# TikTok Feed Session: Post-Session Hook Pipeline & Clear TikTok Cache (Ca 3)

## 1. Post-Session Hook Pipeline Sequence

Trong `flows/multi_machine_feed_session.py` (`_run_child`), mỗi máy sau khi hoàn tất phiên lướt feed sẽ chạy lần lượt các hook:

1. **Follow Hook (`_run_follow_hook`)**:
   - Gọi runner chéo repo `tiktok-follow`.
   - Chỉ áp dụng cho tài khoản có video posted >= 5 và chưa từng dính nhả follow trong ngày.
2. **Upload Hook (`_run_upload_hook`)**:
   - Chạy sau phiên cuối của ca (`session_index == 3`).
   - Kiểm tra định danh workbook Tik, thư mục video, cooldown đăng bài.
3. **Clear TikTok Cache Hook (`_run_clear_cache_hook`)**:
   - Chạy ngay sau **phiên cuối Ca 3 (Block 3)** của ngày (`block_index == 3 and session_index == 3`).

---

## 2. Quy tắc vận hành Clear Cache Hook Ca 3 (User chốt 2026-09-04)

1. **Điều kiện kích hoạt (`_is_final_block3_session`)**:
   - Bắt buộc phải là phiên cuối của Ca 3 trong ngày (`_effective_block_index(config) == 3 and _effective_session_index(config) == 3`).
   - Hỗ trợ cờ override khi test: `force_clear_cache_hook: True` / `_force_clear_cache: True`.
   - Các phiên khác (Ca 1, Ca 2, hoặc phiên 1, 2 của Ca 3) tự động ghi nhận `status: "skipped", reason: "not-block3-final-session"` mà không gọi subprocess.

2. **Chạy bất kể trạng thái phiên feed**:
   - Dù phiên feed kết thúc với `SUCCESS`, `FAILED`, `TIMEOUT`, hay `DEGRADED`, Clear Cache Hook **vẫn bắt buộc được thực thi**.

3. **Cơ chế thực thi & Phân cấp (3-Path Hierarchy)**:
   - Chạy qua subprocess độc lập: `python scripts/clear-tiktok-cache.py --machine <M> --serial <SERIAL>`.
   - Tự động fallback 3 tầng:
     - **Tầng 1 (Deep Link intent)**: `snssdk1180://clean_cache` (nhanh nhất, mở thẳng "Giải phóng dung lượng").
     - **Tầng 2 (In-App Settings Navigation)**: Hồ sơ -> Menu 3 gạch -> Cài đặt và quyền riêng tư -> Vuốt tìm Giải phóng dung lượng.
     - **Tầng 3 (Home Widget Probe)**: Bấm widget "Xóa bộ nhớ đệm" trên màn hình chính với mảng offset tọa độ.

4. **Non-blocking & An toàn Teardown**:
   - Lỗi hoặc cảnh báo khi xóa cache được ghi vào `clear_cache_result.json` và log với `step="clear-cache-hook"`.
   - Lỗi xóa cache **KHÔNG làm thay đổi `final_status`** của phiên feed và không cản trở việc trả device lock lease.
   - Khối `finally:` trong `_run_child` có kiểm tra cờ `clear_cache_executed` để đảm bảo lệnh xóa cache luôn được chạy trước khi giải phóng lease, kể cả khi có unhandled exception trước đó.

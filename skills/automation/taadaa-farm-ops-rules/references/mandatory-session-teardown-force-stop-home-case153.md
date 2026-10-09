# Bổ Sung Teardown Bắt Buộc Force-stop TikTok Về HOME Sau Khi Kết Thúc Toàn Bộ Phiên (Case 153)

## 1. Hiện Tượng & Nguy Cơ
- Sau khi kết thúc phiên nuôi acc (Ca feed + hook), nhiều máy trên màn hình quan sát vẫn hiển thị video đang phát trên feed, trang profile hoặc thư viện gallery thay vì quay về màn hình HOME.
- Việc để máy ngâm ở trang feed/profile/gallery gây rủi ro cao:
  - TikTok nhận diện hành vi bot treo màn hình bất thường.
  - Sáng màn hình liên tục làm nóng máy và chai pin farm S7.
  - Gây hiểu nhầm là phiên chạy dở, treo script.

## 2. Nguyên Nhân Kỹ Thuật
- `feed_session_smoke` có bước `cleanup_close_all_after_session` để đóng app về HOME.
- Tuy nhiên, sau đó runner tiếp tục gọi **Follow Hook** (`run_follow.py`) và **Upload Hook** (`Tiktok-video`). Cả 2 hook này đều bật lại app TikTok / thư viện ảnh qua subprocess.
- Khi hook hoàn tất (hoặc gặp manual review / lỗi / skip), không có cơ chế nào đóng app lại.
- Dòng gọi hàm dọn dẹp trước đây có thể bị thiếu định nghĩa hoặc quăng exception bị nuốt bởi `except Exception: pass`.
- Khối `finally:` ở cuối `_run_child` thiếu bước teardown đóng app trước khi giải phóng lease thiết bị.

## 3. Quy Chuẩn Xử Lý Chuẩn (Invariant)
1. **Helper `_force_stop_tiktok_and_home`**:
   - Tự động nhận diện package mục tiêu (`com.ss.android.ugc.trill` hoặc theo config).
   - Ưu tiên gọi qua `child_ctx.adb.shell(["am", "force-stop", ...])` và `["input", "keyevent", "3"]`.
   - Fallback an toàn qua ADB subprocess với `serial` của máy khi không có `child_ctx.adb`.
2. **Teardown bắt buộc trong khối `finally:`**:
   - Luôn gọi `_force_stop_tiktok_and_home` ngay trước khi giải phóng lease thiết bị.
   - Bất kể phiên chạy thành công, bị skip hay crash giữa chừng, thiết bị **bắt buộc phải force-stop TikTok và quay về màn hình HOME 100%**.

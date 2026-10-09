# Deadman Switch (Hard Gate #0) & Friends Feed Rate Architecture Lessons (2026-09-18)

## 1. Deadman Switch (Hard Gate #0 - Progress Supervisor) Pitfalls & Fix

### Nguy cơ kiến trúc (Category Error)
- **Lỗi tư duy cốt lõi:** Đánh đồng "Tiến độ" = "Side-effects (patch code/commit/pytest)".
- Áp dụng metric của Worker lên Coordinator: Coordinator có các giai đoạn hoàn toàn hợp lệ mà side-effects = 0 (đọc log, phân tích hiện trường O(1), tư vấn với User, tham vấn Sol/Claude, soạn dispatch contract).
- Khi `MAX_STALL_SECONDS` (15m) và `MAX_ACTION_COUNT` (8) quá thấp, hook kích hoạt chặn cứng (`block`) toàn bộ tool calls, tự khóa chết session ("tự sát / suicide lock") khiến Coordinator không thể dispatch worker hay tự cứu.

### Chuẩn khắc phục & Quy tắc vận hành
1. **Nâng trần giám sát:** `MAX_STALL_SECONDS >= 3600` (60m) và `MAX_ACTION_COUNT >= 100` trong `guard_progress_supervisor.py`.
2. **Ghi nhận State Change bao gồm điều phối:** Thêm `delegate_task` vào `REAL_STATE_CHANGES` để không chặn Coordinator khi dispatch worker.
3. **Phân tầng vai trò (Role Separation):**
   - **Worker:** Yêu cầu state change nhanh trong 10-15 calls/10 phút. Nếu chỉ read-only thì abort/fail-fast.
   - **Coordinator:** Không bao giờ block cứng khi đang tương tác hoặc phân tích sâu; chỉ cảnh báo lặp (loop detector) khi cùng 1 sequence lệnh gọi lặp đi lặp lại.

---

## 2. TikTok Feed: Fast Swipe & Like Rate Calibration giữa các Tab

### Tab For You (70% session)
- Duy trì Fast Swipe (2-4 video lướt nhanh 2-5s, xen kẽ 1 video Deep Inspect dump XML).
- Tỉ lệ Like thực tế toàn session đạt 8% - 12%.

### Tab Following (15% session)
- Cho phép Fast Swipe xen kẽ (1 fast - 1 deep) để giảm tải CPU cho farm 70-100 máy.
- Tỉ lệ Like hiệu chỉnh: 25% - 40% (mặc định ~35%).

### Tab Friends (15% session)
- **Nick clone / ít bạn bè (<20 bạn):**
  - Số lượng video bạn bè trong 1 phiên rất ít (2-4 video).
  - Cần giữ Deep Inspect liên tục (hoặc fast swipe rất nhẹ), giữ tỉ lệ like 45% - 50% để tránh tình trạng cả session tab bạn bè 0 tim do cạn video hoặc dính video cũ.
- **Nick trưởng thành (nhiều bạn bè >50-100 bạn):**
  - Chuyển sang mô hình Dynamic Adaptive theo attention curve (xem kỹ và tim ở 3-5 video đầu, lướt nhanh về sau).
  - Tỉ lệ tim duy trì cao hơn For You 1.3 - 1.5 lần (~25% - 32% tổng video bạn bè), kết hợp Fast Swipe để tối ưu tài nguyên máy.

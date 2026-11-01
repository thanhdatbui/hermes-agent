# Cơ Chế Phân Bổ Ca Nuôi vs Follow-Hook & Bẫy Kẹt Vòng Lặp Bốc Nick

## 1. Bản Chất Phân Tách Giữa Nuôi Feed và Follow-Hook
- **Nuôi Feed là tiến trình gốc (Parent Process):**
  - Mọi nick trong Pool theo ca (`Ca 1: {1, 2, 7}`, `Ca 2: {3, 4, 8}`, `Ca 3: {5, 6}`) đều được bốc ra nuôi theo đúng bảng xếp hạng sức khỏe (`_follow_rank`).
  - **Nick yếu / dính nhả follow / fail streak > 0 VẪN ĐƯỢC NUÔI BÌNH THƯỜNG** để lướt feed, xem video, làm ấm session và tích lũy thời gian dưỡng sinh giải phạt.
  - Tuyệt đối KHÔNG có khái niệm "loại bỏ nick dính cooldown khỏi ca nuôi".
- **Follow là Sub-Hook cuối phiên (Child Hook):**
  - Chỉ kích hoạt sau khi phiên nuôi feed đã chạy xong.
  - Nếu nick đang trong thời gian phạt Cooldown nhả follow (`follow-released-daily-cooldown`) $\to$ Sub-hook tự động bỏ qua (`status: skipped`), tuyệt đối không được bấm follow để tránh ăn thêm gậy.

---

## 2. Bẫy Kẹt Vòng Lặp Bốc Lại Đúng Nick Ngày Hôm Sau (Cycle Advance Trap)
- **Triệu chứng:** Sang ngày hôm sau, máy tiếp tục lôi đúng nick dính cooldown của ngày hôm trước ra nuôi, không chịu luân phiên sang các Row khác trong Pool.
- **Nguyên nhân gốc rễ trong code:**
  - Trong `multi_machine_feed_session.py`: Hàm `mark_shift_account_cycle_completed` chỉ được gọi khi follow hook thành công trọn vẹn:
    ```python
    is_success_run = proc.returncode == 0 and result.get("status") == "OK" and not bool(result.get("failed"))
    if shift_ca and is_success_run:
        mark_shift_account_cycle_completed(...)
    ```
  - Khi nick dính cooldown, follow hook bị `skipped` $\to$ không bao giờ được tick hoàn thành chu kỳ.
  - Kết hợp với việc nick có `fail_streak > 0` được xếp ở Rank 4 (dưỡng sinh) $\to$ ngày hôm sau `resolve_shift_pool_account` thấy Row đó chưa hoàn tất lượt trong chu kỳ nên lại tiếp tục ưu tiên bốc đúng nó ra chạy tiếp, tạo thành vòng lặp vô tận.

---

## 3. Quy Tắc Ứng Xử Cho Coordinator
- Khi giải thích logic pick nick:
  - CẤM tự ý bịa đặt hoặc dùng từ ngữ mơ hồ như "pool nick sạch", "loại nick khỏi pool".
  - Bám sát kiến trúc thực tế: Farm chỉ có **Pool theo Ca cố định (Shift Pool)** và **Bảng xếp hạng trạng thái nick (Health Rank)**.
  - Phân định rõ ràng: Nuôi feed là nuôi dưỡng toàn bộ nick; Follow là thao tác có điều kiện chặn an toàn bằng cooldown.

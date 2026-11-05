---
name: farm-cron-opportunistic-idle-and-advisor-floor
description: "Quy chuẩn chuyển đổi Cron toàn Farm sang canh máy rảnh cuốn chiếu (Opportunistic Idle-Machine) và đồng bộ sàn 300s cho Advisor Sol."
---
# Farm Cron Opportunistic Idle-Machine & Advisor 300s Floor

## 1. Đồng Bộ Sàn Timeout 300s Cho Toàn Bộ Advisor & Planner
- **Bẫy lệch pha cấu hình:** Hệ thống đã ép sàn Worker và Planner lên 300s (`SOL_AGY_TIMEOUT_FLOOR = 360`, `DEFAULT_TIMEOUT_PER_TURN = 300`), nhưng nếu bỏ quên file `consult_advisor.py` ở ngưỡng cũ (`first_token_timeout=90s`, `max_total_timeout=200s`) thì mô hình suy luận sâu (`gpt-5.6-sol-high` qua :20129) sẽ bị ngắt socket giữa chừng (do reasoning mất 45s-85s) $\rightarrow$ báo lỗi `unavailable` giả tạo.
- **Quy chuẩn bắt buộc:** Trong `consult_advisor.py` bắt buộc đồng bộ `first_token_timeout=150.0s`, `max_total_timeout=300.0s`, default `timeout_sec=300.0s`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.

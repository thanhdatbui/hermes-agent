# Automation Core Development Guide

## 1. Batch Alert & Machine Alert Invariants (Case 94)
- **Cơ chế:** Toàn bộ cảnh báo farm báo theo cụm lỗi (Batch Alert) khi đạt % nhất định (`evaluate_batch()`).
- **Ngoại lệ Auth/Account P0:** Không cần % ngưỡng nhưng **BẮT BUỘC BÁO THEO CỤM** dưới dạng tin nhắn `[BATCH ALERT: LỖI HỆ THỐNG]`, tuyệt đối không nã alert máy lẻ (`[FARM ALERT: MÁY N]`).
- **Suppression Invariant:** Trong `src/automation_core/alerts.py`, hàm `send_farm_machine_alert` phải suppress 100% khi `_should_suppress_immediate_machine_alert()` là `True`. CẤM thêm nhánh bypass máy lẻ (như `is_account_missing`).
- **Keyword Mapping:** Đưa đầy đủ các từ khóa `account-switcher-missing-expected`, `account_missing`, `thiếu nick`, `mất nick`,... vào `SESSION_LOST_KEYWORDS` trong `batch_aggregator.py`.

## 2. Testing Invariants
- Chạy focused test đúng interpreter: `pytest tests/test_alerts.py`, `pytest tests/test_batch_aggregator.py`.
- Tránh chạy pytest không chỉ định path trên Windows vì sẽ quét toàn bộ workspace/drive.

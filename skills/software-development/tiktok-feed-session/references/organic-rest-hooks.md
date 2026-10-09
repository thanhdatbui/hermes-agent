# Quy tắc Organic Rest Day & Hooks trong TikTok Feed Session

## 1. Safe parsing `machine` & `row`
Trong `_is_account_organic_rest_day(machine: Any, row: Any, date_str: str | None = None) -> bool`:
- Bọc `try/except` cho `int(machine or 0)` và `int(row or 1)` để tránh `TypeError` hoặc `ValueError` khi `account.machine` hoặc `account.account_row_index` là `None`, chuỗi rỗng hoặc định dạng không chuẩn.

## 2. Tách bạch skip reason giữa toàn farm & organic rest
- **Toàn farm (Global rest day)**: Khi cờ môi trường `TAADAA_REST_DAY_NO_FOLLOW == "1"` hoặc cấu hình `rest_day_no_follow` được bật:
  - Reason trả về: `"rest-day-follow-disabled-pure-feed"`.
- **Từng nick (Organic rest day)**: Tỷ lệ ngẫu nhiên nhất quán 1/3 (~33.33%) theo MD5 hash của `date:machine:row`:
  - Reason trả về: `"organic-rest-day-pure-feed"`.

## 3. Đồng bộ trạng thái giữa Follow hook & Upload hook
- Follow hook chạy trước, kiểm tra organic rest và cache kết quả vào `child_ctx.config["_is_organic_rest"]`.
- Upload hook chạy sau, ưu tiên đọc lại từ `child_ctx.config.get("_is_organic_rest")`.
- Điều này loại bỏ hoàn toàn rủi ro lệch biên ngày (date boundary desync) khi phiên feed bắt đầu trước nửa đêm (ví dụ 23:55) và hook upload hoàn tất sau nửa đêm (00:05).

---
name: tradingview-strategy-audit-and-backtest
description: Trích xuất mã nguồn Pine Script (TradingView), đối soát backtest thủ công vs tự động, chuyển đổi Indicator sang Strategy để backtest khách quan.
---
# TradingView Strategy Audit & Backtest

Sử dụng khi User gửi link YouTube / TradingView yêu cầu "nghiên cứu", kiểm chứng chỉ báo, hoặc muốn tự động hóa backtest một indicator/strategy.

## 1. Trích xuất mã nguồn gốc TradingView (Zero-Token Pine Facade)
Khi cần lấy mã nguồn Pine Script từ link TradingView mở (`/script/<ID>-<Name>/`):
1. **Tìm Publication Token (`PUB;...`):**
   - Đọc trang HTML của script và trích xuất regex: `PUB;[a-zA-Z0-9;]+`.
2. **Gọi trực tiếp API Endpoint `pine-facade`:**
   - URL: `https://pine-facade.tradingview.com/pine-facade/get/PUB;<hash>/last`
   - *Lưu ý môi trường:* Trong headless browser có sandbox bảo mật, gọi `fetch()` trong `browser_console` sẽ bị chặn (network request blocker). Do đó, trực tiếp điều hướng bằng `browser_navigate("https://pine-facade.tradingview.com/pine-facade/get/PUB;<hash>/last")` rồi trích xuất JSON bằng `JSON.parse(document.body.innerText).source`.
   - Payload trả về chứa JSON với trường `source` là 100% mã nguồn Pine Script gốc (v5/v6), không bị che giấu hay cắt xén.

## 2. Các cạm bẫy kỹ thuật & Kinh nghiệm Pine Script v6
- **Bẫy Short-Circuit Evaluation trong Pine Script v6:**
  - Khi ghép điều kiện logic (ví dụ `if condition and ta.crossover(...)`), Pine Script v6 thực hiện đánh giá ngắn mạch. Nếu vế trái sai, vế phải bị bỏ qua hoàn toàn.
  - Các hàm nội tại `ta.*` (`ta.crossover`, `ta.crossunder`, `ta.atr`, `ta.sma`...) **bắt buộc phải được tính toán trên từng bar liên tục** để duy trì series history. Nếu bị nhảy cóc nến do short-circuit, hàm sẽ mất lịch sử nến và tín hiệu crossover gần như không bao giờ kích hoạt (dẫn đến lỗi backtest ra 0 lệnh).
  - *Quy tắc khắc phục:* Luôn tính toán độc lập biến tín hiệu/chỉ báo trước trên mọi nến:
    ```pinescript
    bool xUp = ta.crossover(src, ts)
    bool xDn = ta.crossunder(src, ts)
    bool utBuy = src > ts and xUp
    bool utSell = src < ts and xDn
    ```
- **Làm mượt tín hiệu không làm lệch giá khớp (Heikin Ashi Close):**
  - Tránh đổi biểu đồ sang Heikin Ashi thật trong Strategy Tester vì sẽ gây sai lệch giá khớp lệnh (fill price ảo).
  - Dùng công thức toán học tính nến ảo trên biểu đồ chuẩn: `ohlc4 = (open + high + low + close) / 4`. Tín hiệu mượt mà lệnh vẫn khớp theo giá thực tế.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.

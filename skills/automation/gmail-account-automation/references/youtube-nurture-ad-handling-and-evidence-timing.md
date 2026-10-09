# YouTube Nurture: Ad Handling, Modern Selectors & Proof Screenshot Timing

## 1. Bản chất quảng cáo YouTube trong luồng nuôi GPM
Khi profile GPM mở video YouTube để nuôi tương tác (`cron_gpm_gmail_nurture.py`), YouTube thường kích hoạt pre-roll ads với hai định dạng:
1. **Quảng cáo không thể bỏ qua (Non-skippable Ad)**:
   - Thường kéo dài 15s hoặc 30s (ví dụ: `0:02 / 0:30`, nhãn `Sponsored • 1 of 2`).
   - YouTube **hoàn toàn không render** nút hay đếm ngược bỏ qua trên DOM.
   - Script phải để quảng cáo phát tự nhiên, không coi là lỗi script hay lỗi click hụt.
2. **Quảng cáo có thể bỏ qua (Skippable Ad)**:
   - Luôn có thời gian đếm ngược bắt buộc tối thiểu 5 giây trước khi nút "Bỏ qua quảng cáo" xuất hiện.
   - Tại các giây đầu tiên (`0:01 - 0:04`), DOM chưa có nút skip hoặc nút ở trạng thái bị ẩn / countdown.

---

## 2. Cạm bẫy thời điểm chụp ảnh nghiệm thu (Proof Screenshot Timing Trap)
- **Vấn đề**:
  Nếu gọi `take_proof_screenshot` ngay khi video vừa được click mở (ở timestamp `0:02`), ảnh chụp sẽ ghi lại **quảng cáo pre-roll** thay vì nội dung video chính.
  Khi User xem ảnh nghiệm thu, User sẽ thấy video đang phát quảng cáo và thắc mắc tại sao script không bấm bỏ qua (hoặc nghi ngờ script xem quảng cáo suốt buổi).
- **Quy tắc nghiệm thu**:
  1. Tránh chụp ảnh nghiệm thu duy nhất tại giây `0:00 - 0:05` khi pre-roll ad đang phát.
  2. Thời điểm chụp tối ưu là sau khi video đã phát qua ngưỡng pre-roll (ví dụ sau 10s - 15s), hoặc chụp bổ sung sau khi đã skip quảng cáo để xác nhận đã vào video chính.
  3. Khi User chất vấn bằng ảnh chụp có quảng cáo ở giây thứ 2, kiểm tra ngay timestamp trên thanh tua (`0:02 / 0:30`) để giải thích rõ đây là pre-roll ad chưa đến ngưỡng skip (hoặc non-skippable).

---

## 3. Bộ Selector nút Bỏ qua quảng cáo YouTube chuẩn xác (2026 Resilient Selectors)
YouTube thường xuyên thay đổi class name obfuscated của nút skip. Không được phụ thuộc duy nhất vào class name cũ (`ytp-skip-ad-button`).

**Bộ selector đa tầng chuẩn hóa**:
```python
ad_selector = (
    "button.ytp-skip-ad-button, .ytp-ad-skip-button, button.ytp-ad-skip-button-modern, "
    "[class*='ytp-ad-skip-button'], .ytp-ad-skip-button-slot button, "
    "button:has-text('Bỏ qua'), button:has-text('Skip')"
)
```

**Kỹ thuật click & human emulation**:
- Quét định kỳ mỗi 2 giây trong suốt `watch_duration`.
- Khi nút xuất hiện (`skip_btn.is_visible()`):
  - Click bỏ qua sau delay ngẫu nhiên 1.2s - 2.5s (kèm `hover()`), bấm force và chụp screenshot ngay sau khi skip để có ảnh nghiệm thu video chính.
  - Sau khi click skip, ghi log rõ ràng `✓ Đã bấm Bỏ qua quảng cáo YouTube thành công`.
  - Kết hợp lắng nghe trạng thái container quảng cáo (`.ad-showing, .ad-interrupting`) để log rõ ràng đang chờ nút Bỏ qua xuất hiện khi gặp quảng cáo pre-roll dài.

---

## 4. Cấu hình thời lượng nuôi sâu & Concurrency (Production Standard 2026)
Theo chỉ thị vận hành thực tế:
- **Thời lượng xem video**: Bắt buộc nâng lên **300s – 360s (5 – 6 phút/video)** thay vì 90s–120s ngắn hạn để tài khoản được ngâm sâu tương tác, vượt checkpoint Google bền vững.
- **Số luồng song song**: Chạy **5 workers song song** (`--concurrency 5`, `--limit 5`).
- **Chu kỳ quay vòng (5 ngày - INVARIANT BẮT BUỘC)**: BẮT BUỘC giữ nguyên chu kỳ **5 ngày mới lặp lại nuôi một profile** (`NURTURE_INTERVAL_SECONDS = 5 * 86400`). TUYỆT ĐỐI CẤM tự ý giảm chu kỳ xuống 1 ngày làm spam tài khoản gây checkpoint Google. Watchdog chạy quét mỗi giờ (`0 * * * *`) để bốc cuốn chiếu những nick ĐÃ ĐỦ 5 NGÀY chưa nuôi; nick nào chưa đủ 5 ngày thì bỏ qua an toàn.
- **Canary task override**: Luôn hỗ trợ cờ `--task <youtube|news|search>` trong CLI để khi cần kiểm chứng nhanh tác vụ cụ thể có thể ép 100% kịch bản mong muốn mà không bị tỷ lệ ngẫu nhiên làm lệch.

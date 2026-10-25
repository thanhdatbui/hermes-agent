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
    "[class*='ytp-ad-skip-button'], .ytp-ad-skip-button-slot button, .ytp-ad-skip-button-container button, "
    "button:has-text('Bỏ qua'), button:has-text('Skip')"
)
```

**Kỹ thuật click JS trực tiếp & Chống bẫy 30% lờ quảng cáo (Direct JS Skip & 100% Rate)**:
- **Cấm ngẫu nhiên lờ quảng cáo (No Ad Ignore)**: Tuyệt đối không dùng `random.random() < 0.70` để cố tình lờ 30% quảng cáo. Khi nút xuất hiện, bắt buộc bấm bỏ qua ngay lập tức để không giữ quảng cáo trên video gây phản cảm khi kiểm tra.
- **Thực thi Skip qua JavaScript trực tiếp (Bypass Web Component Encapsulation)**:
  Playwright locator đôi khi bị trượt do YouTube bọc nút skip trong các slot/container động. Dùng hàm evaluate JS chạy trực tiếp trong DOM:
  ```python
  def try_skip_youtube_ad(page) -> bool:
      try:
          return bool(page.evaluate("""() => {
              const sels = [
                  'button.ytp-skip-ad-button', '.ytp-ad-skip-button',
                  'button.ytp-ad-skip-button-modern', '.ytp-ad-skip-button-modern',
                  '[class*="ytp-ad-skip-button"]', '.ytp-ad-skip-button-slot button',
                  '.ytp-ad-skip-button-container button'
              ];
              for (const s of sels) {
                  const b = document.querySelector(s);
                  if (b && b.offsetParent !== null) { b.click(); return true; }
              }
              const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
              const skip = btns.find(b => {
                  const t = (b.innerText || b.textContent || '').trim().toLowerCase();
                  return t.includes('bỏ qua') || t.includes('skip');
              });
              if (skip && skip.offsetParent !== null) { skip.click(); return true; }
              return false;
          }"""))
      except Exception:
          return False
  ```
- **Chụp ảnh nghiệm thu khi video chính đang phát (Ad-Showing Guard)**:
  Kiểm tra cờ quảng cáo của YouTube:
  ```python
  is_ad = bool(page.evaluate("() => Boolean(document.querySelector('.ad-showing, .ad-interrupting'))"))
  if not is_ad or elapsed >= 20:
      take_proof_screenshot(context, page, ss_path, email)
  ```
  Điều này đảm bảo ảnh nghiệm thu luôn bắt được nội dung video chính thức, không bao giờ gửi ảnh chứa chữ "Bỏ qua" hay đoạn quảng cáo tài trợ.

---

## 4. Cấu hình thời lượng nuôi sâu & Concurrency (Production Standard 2026)
Theo chỉ thị vận hành thực tế:
- **Thời lượng xem video**: Bắt buộc nâng lên **300s – 360s (5 – 6 phút/video)** thay vì 90s–120s ngắn hạn để tài khoản được ngâm sâu tương tác, vượt checkpoint Google bền vững.
- **Số luồng song song**: Chạy **5 workers song song** (`--concurrency 5`, `--limit 5`).
- **Chu kỳ quay vòng (5 ngày - INVARIANT BẮT BUỘC)**: BẮT BUỘC giữ nguyên chu kỳ **5 ngày mới lặp lại nuôi một profile** (`NURTURE_INTERVAL_SECONDS = 5 * 86400`). TUYỆT ĐỐI CẤM tự ý giảm chu kỳ xuống 1 ngày làm spam tài khoản gây checkpoint Google. Watchdog chạy quét mỗi giờ (`0 * * * *`) để bốc cuốn chiếu những nick ĐÃ ĐỦ 5 NGÀY chưa nuôi; nick nào chưa đủ 5 ngày thì bỏ qua an toàn.
- **Canary task override**: Luôn hỗ trợ cờ `--task <youtube|news|search>` trong CLI để khi cần kiểm chứng nhanh tác vụ cụ thể có thể ép 100% kịch bản mong muốn mà không bị tỷ lệ ngẫu nhiên làm lệch.

---

## 5. Cạm bẫy phím tắt Toggle 'k' & Cơ chế Ensure-Play tự động
- **Bẫy phím tắt 'k'**: Phím `k` trên YouTube là phím toggle Play/Pause. Nếu video đã tự động phát (Autoplay), việc gọi mù quáng `page.keyboard.press("k")` sẽ vô tình biến video thành **PAUSED ở giây `0:00`** (hiển thị nút tam giác `▶` thay vì `⏸`). Nếu focus đang nằm ở ô tìm kiếm, phím `k` bị nuốt không tác dụng.
- **Giải pháp chuẩn hóa**:
  1. Tuyệt đối không dùng `keyboard.press("k")` để kích hoạt phát video.
  2. Dùng hàm kiểm tra DOM trực tiếp:
     ```python
     def ensure_youtube_playing(page) -> bool:
         try:
             return bool(page.evaluate('''() => {
                 const v = document.querySelector('video');
                 if (!v) return false;
                 if (v.paused) {
                     const playBtn = document.querySelector('button.ytp-play-button');
                     if (playBtn) playBtn.click();
                     else { try { v.play().catch(() => {}); } catch(e){} }
                 }
                 return !v.paused;
             }'''))
         except Exception:
             return False
     ```
  3. **Bộ đếm thời gian kiểm tra Monotonic Timer**: Dùng biến `last_play_check = start_watch` và kiểm tra `now_t - last_play_check >= 10.0` thay vì `int(elapsed) % 10 == 0` (vì điều kiện `int` modulo có thể kích hoạt liên tục nhiều lần trong cùng một giây, gây spam JS evaluate).
  4. **CLI Validation & Explicit Task Override**: Cờ `--task` trong parser bắt buộc dùng `choices=["youtube", "news", "search", ""]` để fail-fast khi có giá trị sai. Hàm `choose_behavior_tasks(rnd=None, task_override=None)` nhận tham số trực tiếp để test cô lập, tránh rò rỉ biến môi trường `TASK_OVERRIDE` giữa các lời gọi trong cùng tiến trình.
  5. Gọi `ensure_youtube_playing(page)` trước khi vào vòng lặp xem, định kỳ mỗi 10s trong vòng lặp `while`, và ngay sau khi click "Bỏ qua quảng cáo".
  6. Trì hoãn chụp screenshot nghiệm thu tới khi `elapsed >= 12s` và `is_ad == False` để đảm bảo bắt trọn khoảnh khắc video chính thức đang phát thật sự (nút `⏸` và timer > 0).

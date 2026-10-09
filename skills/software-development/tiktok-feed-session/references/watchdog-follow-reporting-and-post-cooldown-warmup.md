# Đối soát Lỗi Nuôi Acc & Follow Chéo: Watchdog Race Condition & Post-Cooldown Warmup

## 1. Hiện tượng & Bản chất lỗi Watchdog Báo Ảo 0 Lượt Follow

### Hiện tượng
Báo cáo Telegram định kỳ từ `feed_session_watchdog.py` ghi nhận:
```text
• Follow chéo (0 lượt follow):
  + Success (0): Không có
  + Lỗi script/xác minh (70 máy): M2, M3, M4...
```
Tuy nhiên khi kiểm tra thực tế trên đĩa (`follow_result.json`) thì có 14 máy follow thành công (`followed > 0`), 12 máy bị nhả follow, 54 máy bỏ qua an toàn vì nick < 5 video.

### Nguyên nhân kỹ thuật (Race Condition chốt sớm)
1. **Lệch pha vòng đời giữa Feed và Follow Hook**:
   - Khâu lướt Feed hoàn tất trước trên 80/80 máy (ví dụ 70 success + 10 fail).
   - Điều kiện chốt báo cáo trong `can_report_session`:
     `completed_expected_count >= expected_count and not has_unattempted_locked`
     chỉ đo lường số lượng máy hoàn tất khâu **Feed**. Khi 80 máy xong Feed, watchdog lập tức đánh giá là phiên đã hoàn tất và chốt báo cáo ngay lập tức.
   - Trong khi đó, **Follow Hook là hook chạy nối tiếp sau Feed**. Tại thời điểm watchdog quét, các máy vẫn đang thực thi follow hoặc file `follow_result.json` chưa được ghi xong (kéo dài đến sau thời điểm chốt).
2. **Fallback đánh đồng thành Lỗi Script**:
   - Khi `all_follows` chưa có dữ liệu của 70 máy lướt Feed thành công, logic phân loại của watchdog:
     ```python
     if all_machines[m].get("status") == "success":
         if runner_busy:
             fl_skipped.append(m)
         else:
             fl_error.append(m)
     ```
   - Nếu lúc này process runner đã thoát khâu Feed chính (`runner_busy == False`), toàn bộ 70 máy bị phân loại vào `fl_error` (Lỗi script/xác minh) và tổng số lượt follow bị tính là 0.

---

## 2. Cơ chế Cooldown & Post-Cooldown Warmup (Tài khoản từng bị nhả follow)

### Thắc mắc: Máy follow được có phải là máy chưa từng bị nhả follow?
**Trả lời: KHÔNG.** Nick từng bị phạt nhả follow vẫn follow được sau khi hết hạn cooldown, nhờ cơ chế **Post-Cooldown Warmup** (`commit ba8df44`):

1. **Khi dính phạt nhả follow**:
   - `FollowState` ghi nhận `follow_failed = True` và set `cooldown_until_date` (hoặc `cooldown_until_at`).
   - Mọi luồng follow tự nhiên trên Feed, popup hay follow hook đều bị chặn tuyệt đối (budget = 0).
2. **Khi mãn hạn cooldown (hết ngày phạt)**:
   - `_roll_day()` chuyển `follow_failed` về `False`, nhưng vẫn bảo toàn `fail_streak > 0`.
   - Kích hoạt thuộc tính:
     ```python
     @property
     def is_post_cooldown_warmup(self) -> bool:
         return self.fail_streak > 0 and not self.follow_failed
     ```
3. **Cấp hạn mức thăm dò (Warmup Budget)**:
   - Thay vì cấp full ngân sách (6–10 follow) như tài khoản sạch, tài khoản đang warmup chỉ được cấp **3 đến 5 lượt follow / phiên**:
     ```python
     if video_count is not None and int(video_count) >= 5:
         if self.is_post_cooldown_warmup:
             return _random.randint(3, 5)
         return _range(1)  # full 6-10
     ```
   - Nếu thực hiện thành công toàn bộ mà không bị TikTok quét nhả, chuỗi thành công mới dần xóa `fail_streak` và khôi phục tài khoản về trạng thái bình thường.

---

## 3. Các lỗi thường gặp khi chuyển Ca nuôi acc (Shift / Row Transition)

Khi chuyển từ Ca đêm (Ca 4 - Row 7) sang Ca sáng (Ca 1 - Row 1):
1. **`manual-needed:account-switcher-missing-expected`**:
   - Script mở account switcher nhưng không thấy username/display_name của Row 1.
   - Thường do: Nick bị đăng xuất, app TikTok có danh sách switcher dài hơn màn hình cần thao tác cuộn, hoặc handle trong workbook lệch so với text hiển thị trên UI.
2. **`manual-needed:account-switcher-not-open`**:
   - Tap vào nút chuyển tài khoản trên màn hình Profile nhưng popup switcher không hiển thị do UI bị lag hoặc animation chưa xong.
3. **`device is offline or ADB/USB disconnected`**:
   - Cổng USB chập chờn hoặc hub USB quá tải khiến ADB mất kết nối lúc bắt đầu ca mới.
4. **`popup is not in the shared TikTok allowlist`**:
   - TikTok hiện pop-up khảo sát / khuyến mãi mới chưa có trong allowlist. Hệ thống tuân thủ nguyên tắc fail-closed, dừng an toàn sau 2 lần swipe recovery thất bại.

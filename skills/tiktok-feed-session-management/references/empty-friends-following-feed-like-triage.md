# Empty Feed & Suggestion Screen Triage in Friends & Following Tabs

## Triệu chứng & Hiện tượng
- Báo cáo watchdog nuôi TikTok cho thấy tỉ lệ Like tab Bạn bè (Friends) và Following rất thấp:
  + Cấu hình: `following: 30%`, `friends: 70%`
  + Kết quả watchdog: `Following: ~6-8%`, `Bạn bè: ~13-18%`
  + Người vận hành thắc mắc: "Tỉ lệ like của bạn bè vẫn thấp thế nhỉ, có tăng tỉ lệ like lên cho chắc không?"

## Điều tra Root Cause
Phân tích chi tiết `summary.txt`, `log.jsonl` và các file `ui.xml` trên 57-78 máy farm:
1. **Các máy có bạn bè/video thật (vd Máy 17, 37, 65):**
   - Đạt tỉ lệ like **46% - 80%** (khớp hoàn toàn cấu hình 70%).
2. **Các máy chưa có bạn bè / acc mới (vd Máy 38, 58, 66, 75):**
   - Khi chuyển sang tab Bạn bè hoặc Following, TikTok **không hiển thị video player**.
   - Màn hình hiển thị danh sách thẻ gợi ý / kết nối danh bạ:
     - Tab Bạn bè: `"Hãy follow bạn bè để xem video của họ"`, `"Danh bạ - Tìm các liên hệ của bạn"`, `@username Follow bạn`.
     - Tab Following: `"Tác giả nổi bật"`, `"Follow tài khoản để xem video mới nhất của họ tại đây."`.
3. **Lỗi swipe ảo trên màn hình rỗng:**
   - Runner cũ chấp nhận màn hình gợi ý này là feed hợp lệ và tiếp tục swipe 8-13 nhịp trên danh sách thẻ.
   - Không có video → không có nút Like (`"Thích video"`) → hàm `_maybe_like_video` fail im lặng (`like is None or like.center is None: return False`).
   - Mẫu số (số lượt swipe) tăng thêm 65 lượt swipe ảo với 0 lượt like, kéo tụt tỉ lệ like chung của toàn farm xuống 18%.

## Giải pháp Chuẩn (Fix Sau Dice)
1. **Chi tiết hóa Logging trong `_maybe_like_video`:**
   - Không return `False` im lặng khi dice đã pass (`random <= like_rate`).
   - Ghi rõ `error="already_liked"` khi video đã thả tim.
   - Ghi rõ `error="button_not_found"` khi không tìm thấy nút Like trên màn hình.
2. **Cải tiến Like Selector:**
   - Không chỉ match `startswith("thích video")` hay `rid="like_icon"`, mà hỗ trợ thêm `("thích" in desc and "lượt thích" in desc)` hoặc `("like" in desc and "likes" in desc)`.
3. **Empty Feed Detection & Early Fallback:**
   - Trong tab Friends/Following, nếu phát hiện chuỗi gợi ý trống video (`"Hãy follow bạn bè"`, `"Tác giả nổi bật"`, `"bạn sẽ nhận thấy họ ở đây"`):
     - Ghi nhận `empty_feed_detected`.
     - Lập tức điều hướng quay lại tab Đề xuất (`tap_navigation_target(ctx, _top_tab_target("for-you"))`).
     - Tránh cày 8-10 nhịp swipe ảo trên danh sách liên hệ.
4. **Nâng tỉ lệ Like cấu hình:**
   - `following`: 30% → 50%
   - `friends`: 70% → 80%

## Pitfall: Canary Kiểm Fallback/Tab Ép (2026-09-13)
- `videos_until_tab_decision = randint(3,8)`. Canary `--recovery-test-swipes 4` là INCONCLUSIVE: chưa chạm 0 nên chưa hề chuyển tab (M66 Row 5: feed_counts FY:2 FL:0 FR:0).
- Canary kiểm fallback/tab ép (`--feed-distribution {"for-you":0.0,"following":0.5,"friends":0.5}`) BẮT BUỘC `--recovery-test-swipes >= 12` để chạm tab ít nhất 1-2 lần.
- Chọn máy: kiểm tra lock `C:/Users/Kibe/.codex/device-locks/*.lock.json` trước; M38 bị lock bởi project register gmail → cấm dùng. M66 (serial ce12160c2a99962905) free, acc rỗng đã biết.
- Mở rộng fallback: sau khi fallback về For You thì triệt tiêu tab rỗng đó đến hết phiên (set distribution tab đó = 0) — đúng yêu cầu: gặp màn rỗng thì quay về feed lướt tiếp, bỏ qua tab đó.
- Nghiệm thu: grep `fallback_to_for_you` trong log.jsonl + `feed_counts`/`like_counts` + screencap `adb -s <serial> exec-out screencap -p`.

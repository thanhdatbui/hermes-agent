# Triage & Pitfalls: TikTok Feed Session Tương Tác & Báo Cáo (Ca 4 - 2026-09-13)

## 1. Phân biệt Bỏ qua trống slot vs Lỗi Feed thực sự
- **Hiện tượng**: Báo cáo tổng kết ca báo 61 máy Fail khiến người vận hành lầm tưởng farm gặp lỗi hệ thống nghiêm trọng.
- **Root cause**: Row 7 là slot phôi mới, chỉ có 35 máy có nick trong `taikhoan_run_safe.xlsx`. 45 máy còn lại trả về `account row 7 is empty (no username) for machine X, skipping` với status `config-error`.
- **Nguyên tắc**: Báo cáo watchdog bắt buộc phải bóc tách:
  + `Success (N)`: Máy hoàn thành lướt feed.
  + `Fail (N)`: Máy có nick nhưng gặp lỗi thật (device lock, mất kết nối adb, sai mật khẩu/mất phiên...).
  + `Trống slot/Chưa có nick (N)`: Máy bỏ qua an toàn vì chưa có nick trong kho.

## 2. Bug kẹt tab For You 100% do Fast Swipe nuốt biến đếm chuyển tab
- **Cấu hình mong muốn**: Phân phối feed gồm 70% Đề xuất (For You), 15% Bạn bè (Friends), 15% Following. Tỷ lệ thả tim ở Bạn bè rất cao (70%), Following (30%), Đề xuất chỉ 8%.
- **Hiện tượng thực tế**: 100% máy lướt 21 video đều nằm ở tab Đề xuất, feed Friends và Following đều bằng 0, dẫn tới số tim thả ở Bạn bè bằng 0.
- **Root cause**: Trong `feed_swipe_smoke.py`, cơ chế chuyển tab dựa vào biến đếm:
  ```python
  videos_until_tab_decision = random.randint(3, 8)
  ```
  Nhánh Deep Inspect có trừ biến đếm (`videos_until_tab_decision -= 1`), nhưng nhánh `fast_swipe` (dòng ~21445) khi lướt nhanh xong lại gọi `continue` ngay mà **quên trừ `videos_until_tab_decision -= 1`**.
- **Hệ quả**: Trong 21 video có 15 video là Fast Swipe, biến đếm chỉ bị trừ 5-6 lần nên không bao giờ giảm về `<= 0` để kích hoạt `_weighted_feed_choice`.
- **Bài học**: Mọi nhánh lướt video trong vòng lặp (fast swipe, skip sponsored, deep inspect) đều phải trừ nhịp chuyển tab.

## 3. Thống kê Thả Tim (Like Rates) trong Báo Cáo
- Báo cáo Feed Watchdog cần bóc tách tổng số tim / tổng video và tỷ lệ % thả tim, đồng thời phân tách rõ theo từng tab (`Đề xuất: X tim / Y vid | Bạn bè: Z tim / W vid`) để người vận hành giám sát được thuật toán nuôi tương tác có chạy đúng tỷ lệ cài đặt hay không.

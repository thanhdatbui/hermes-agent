# Chuẩn Hoá Báo Cáo Watchdog Khi Máy Ăn Nhả Đuôi (Ceiling Drop)

## 1. Bản Chất Lỗi Báo Cáo Mâu Thuẫn ("Follow Chéo 3 Lượt nhưng 0 Máy Thành Công")
- **Nguyên nhân gốc rễ:**
  - Khi một máy (ví dụ M59) chạy Mode 2 / Mode 1 follow thành công được 3 lượt, đến lượt thứ 4 bị TikTok nhả hoặc chạm trần phiên:
    - Runner trả về: `status: "FOLLOW_FAILED"`, `follow_failed: True`, `followed: ["u1", "u2", "u3"]`.
  - Trong `classify_machine_follow_result(fd)`:
    - Code kiểm tra thấy `status == "FOLLOW_FAILED"` nên gán category là `"released"`.
  - Trong vòng lặp tổng hợp của `feed_session_watchdog.py`:
    - Code cũ dùng `if category == "released": fl_released.append(m) elif category == "success": fl_success.append(m)`.
    - Do đó, M59 **chỉ được đưa vào `fl_released` mà hoàn toàn vắng mặt trong `fl_success`**!
  - Hậu quả hiển thị:
    ```text
    • Follow chéo (3 lượt follow) [Module 2 (Anchor): 3 | Module 1 (Bù): 0]:
      + Thành công (0 máy | 0.0%): Không có
      + Nhả follow (1 máy | 100.0%):
        - Nhả ở Hồi phục 1 (1 - 4 lượt | 100.0%): (M59: 3 lượt)
    ```
    Báo cáo in ra mâu thuẫn trực tiếp: dòng trên vừa ghi có 3 lượt follow thành công, dòng dưới lại phán "0 máy thành công", gây hoang mang cho người vận hành.

## 2. Chuẩn Hoá Logic Đếm Máy
1. **Ghi nhận đóng góp thành công (`fl_success`):**
   ```python
   category, _ = classify_machine_follow_result(fd)
   if category == "released":
       fl_released.append(m)
       if len(flist) > 0:
           fl_success.append(m)  # Đã có follow thành công thì bắt buộc ghi nhận
   elif category == "success":
       fl_success.append(m)
   ```
2. **Khử trùng lặp mẫu số tính tỷ lệ (%):**
   - Vì máy có thể vừa nằm trong `fl_success` (đã follow được X nick) vừa nằm trong `fl_released` (bị nhả ở lượt cuối), tổng số máy ứng viên thực tế phải dùng phép hợp tập hợp:
   ```python
   total_fl_candidates = len(set(fl_success) | set(fl_released))
   ```
3. **Kết quả báo cáo chuẩn:**
   ```text
   • Follow chéo (3 lượt follow) [Module 2 (Anchor): 3 | Module 1 (Bù): 0]:
     + Thành công (1 máy | 100.0%):
       🌱 Hồi phục 1 (1 - 4 lượt | 100.0%): (M59)
     + Nhả follow (1 máy | 100.0%):
       - Nhả ở Hồi phục 1 (1 - 4 lượt | 100.0%): (M59: 3 lượt)
   ```
   Rõ ràng: M59 đã hoàn thành 3 lượt follow trước khi chạm trần, không bị tính là 0 máy thành công.

# TikTok Pin LIFO Queue & Slot 1 Top View Enforcement (2026-10-23)

## 1. Ngữ Cảnh & Sửa Đổi Của Người Dùng (User Steering 23/10/2026)
- **User feedback:**
  - *"Ủa script ghim k ưu tiên ghim video nhiều view nhất lên đầu à"*
  - *"H làm sao cho mỗi lần chạy pin thì luôn pin video cao nhất lên đầu"*
- **Vấn đề phát hiện:**
  - Khi chạy ghim video trên profile TikTok, kênh có 3 video đạt chuẩn view (113,5K, 3.265, 2.148 views).
  - Script ban đầu quét theo thứ tự view giảm dần: ghim 113,5K trước, rồi 3.265, rồi 2.148 sau cùng.
  - Sau khi chạy xong, video 113,5K bị dạt sang tận ô số 3 (bên phải ngoài cùng), còn ô số 1 (trên cùng bên trái) lại hiển thị video 2.148 views!

## 2. Bản Chất Cơ Chế LIFO Trên Giao Diện TikTok Profile
- **Ngăn xếp chèn đầu (LIFO - Last In, First Out):**
  - Mỗi khi bấm "Ghim" một video mới, TikTok tự động nhét video đó vào **Ô số 1 (Góc trên cùng bên trái, `x < 360`)**.
  - Các video đã ghim trước đó bị đẩy dồn sang bên phải: Ô 1 $\rightarrow$ Ô 2, Ô 2 $\rightarrow$ Ô 3.
- **Bẫy ghim giảm dần (Descending Pin Trap):**
  - Ghim video cao nhất trước $\rightarrow$ các video ghim sau sẽ liên tục đẩy video cao nhất lùi sang phải.
  - Video ghim sau cùng (view thấp nhất trong nhóm top) lại chiếm vị trí số 1.

## 3. Quy Tắc Kỹ Thuật Đã Chuẩn Hóa Trong `pin_top_videos.py`
1. **Ghim theo thứ tự View TĂNG DẦN (Ascending Candidate Pinning):**
   ```python
   slots_free = max_pins - pinned_before
   to_pin = sorted(cands[:slots_free], key=lambda t: t["views"])  # Tăng dần: thấp trước, cao nhất sau cùng
   for target in to_pin:
       # Ghim target
   ```
   - Clip view thấp hơn được ghim trước $\rightarrow$ vào ô 1.
   - Clip view cao hơn ghim tiếp theo $\rightarrow$ đẩy clip trước sang ô 2.
   - **Clip view cao nhất được ghim SAU CÙNG** $\rightarrow$ Chiếm trọn **Ô số 1**, đẩy toàn bộ các video còn lại sang phải theo đúng thứ tự giảm dần từ trái sang phải: `[Top 1 (113K)] | [Top 2 (3.2K)] | [Top 3 (2.1K)]`.

2. **Chốt chặn tự động đảo Top 1 (Re-pin Head Alignment / Enforce Slot 1):**
   - Khi kiểm tra profile đã ghim đủ video hoặc phát hiện video top view bị lệch:
     ```python
     top_pinned = max(pinned_tiles, key=lambda t: t["views"])
     if top_pinned["center"][0] >= 360: # Đang ở ô 2 hoặc ô 3
         # Bước 1: Unpin top_pinned
         _apply_tile_action(serial, cx, cy, "UNPIN")
         # Bước 2: Reparse và Pin lại top_pinned
         _apply_tile_action(serial, cx2, cy2, "PIN")
     ```
   - Thao tác unpin rồi pin lại sẽ đưa ngay clip top view về lại **Ô số 1** mà không làm thay đổi trạng thái ghim của các clip còn lại.

3. **Yêu cầu đánh thức thiết bị & ATX Agent trước khi Dump UI:**
   - Nếu màn hình đang ngủ (`Sleep/Dozing`), ATX server trả về empty XML (`UI_DUMP_INVALID`).
   - Bắt buộc gọi `input keyevent KEYCODE_WAKEUP` và khởi chạy `SplashActivity` (`com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity`), chờ 3s trước khi dump UI.
   - Luôn import `automation-core/src` trước `automation_core` trong `sys.path` để tránh va chạm stale site-packages.

# Fix Mode 2' Following-List & UI Teardown on TikTok 46.x (2026-08-17)

## 1. Triệu chứng & Vấn đề gốc
- Khi chạy Follow runner ở chế độ `both` hoặc `mode 2`: script mở được Profile của nick anchor (nick Tik1/Tik2), nhưng sau đó lập tức báo lỗi:
  `REASON: ['không tìm thấy tab Đã follow (Following) trên profile']` -> kết luận `MANUAL_REVIEW`.
- Sau đó Mode 1 (Search trực tiếp) phải chạy bù 100% budget, làm mất đi tính năng follow chéo qua Following list nội bộ của Module 2.
- Cuối phiên follow, app TikTok vẫn mở dở ở màn hình danh sách, chưa đóng recent apps và chưa đưa máy về Home launcher.

## 2. Nguyên nhân kỹ thuật (Evidence máy 10/11/12, TikTok 46.4.3)
1. **Thuộc tính `clickable="false"` trên tab header**:
   - Trên TikTok phiên bản mới, cụm 3 tab header trên Profile người khác (`Đã follow 50`, `Follower 7`, `Được đề xuất`) có node text `Đã follow` (`android:id/text1` hoặc `id/shq`) mang thuộc tính `clickable="false"` do sự kiện click được lắng nghe trên layout cha.
   - Code `_following_tab_node` cũ trong `mode2_follow_followers.py` kiểm tra cứng `and n.get("clickable") is True` -> loại bỏ node tab `Đã follow`, làm hàm trả về `None`.

2. **Trùng 2 node text "Đã follow" trên cùng 1 Profile**:
   - Khi profile anchor là nick ta đã follow trước đó, màn hình xuất hiện CẢ HAI node `Đã follow`:
     - Node chỉ số tab: `ID: com.ss.android.ugc.trill:id/shq` (ở `y < 550`).
     - Nút action quan hệ: `ID: com.ss.android.ugc.trill:id/ff8` (ở `y > 550`).
   - Code cũ đếm `len(matches) == 1` -> vì thấy 2 node nên trả về `None`!

3. **Anchor có "Đã follow 0" (Danh sách rỗng)**:
   - Trên TikTok 46.x, trang following rỗng có title button `id/yhj` (thay vì `id/yby`) và không có node ImageView illustration riêng. Code cũ kiểm tra cứng 4 node khiến trang rỗng bị phân loại nhầm thành `invalid` -> văng `MANUAL_REVIEW`.

4. **Kẹt tại màn hình Search History khi quay về Feed**:
   - Khi thoát màn hình tìm kiếm, gửi keyevent 4 (Back cứng) đôi khi bị app chặn. Nút Back icon `id/bow` ở góc trên bên trái `[0,84][150,216]` là điểm thoát tin cậy 100%.

5. **Resource IDs mới trên TikTok 46.x**:
   - **Nút Follow trên từng dòng danh sách**: ID mới là `com.ss.android.ugc.trill:id/thb` (phiên bản cũ là `id/tcj`).
   - **Khung Recycler View danh sách**: ID mới là `com.ss.android.ugc.trill:id/u_q` (phiên bản cũ là `id/u5r`).

## 3. Giải pháp đã thực hiện & Verified
1. **Patch `_following_tab_node` (`follow_runner/flows/mode2_follow_followers.py`)**:
   - Bỏ điều kiện `clickable is True`.
   - Loại trừ nút action `id/ff8`/`id/fds`, ưu tiên node có resource-id dòng tab (`id/shq`/`id/sdn`) hoặc `y < 550`.
2. **Patch `_classify_follower_surface` & `core/selectors.py`**:
   - Bổ sung `FOLLOWER_EMPTY_TITLE_IDS = ("com.ss.android.ugc.trill:id/yby", "com.ss.android.ugc.trill:id/yhj")`.
   - Bổ sung `FOLLOWER_FOLLOW_BUTTON_RESOURCE_IDS = ("com.ss.android.ugc.trill:id/tcj", "com.ss.android.ugc.trill:id/thb")`.
   - Bổ sung `FOLLOWER_LIST_RECYCLER_IDS = ("com.ss.android.ugc.trill:id/u5r", "com.ss.android.ugc.trill:id/u_q")`.
   - Nhận diện đúng trang rỗng (`empty`) -> tự động skip anchor rỗng sang anchor tiếp theo.
3. **Patch `_back_to_feed`**:
   - Khi ở màn hình Search History, ưu tiên tap vào nút Back icon `id/bow` ở góc trên bên trái -> quay về Home Feed 100%.
4. **Bộ lọc nick nội bộ (User rule)**:
   - Giữ vững gate: chỉ follow username có trong `engine.follow_uids()` (`taikhoan_run_safe.xlsx`); nick lạ ngoài farm tự động bị SKIP. Nếu màn hình hiện tại chưa có nick farm thì tiếp tục cuộn (`_scroll_follower_list`) tìm tiếp thay vì dừng sớm.
5. **Teardown cuối Script: Close All Recent Apps & Về Home (User rule 2026-08-17)**:
   - Bọc khối `finally` ở cuối `run_follow.py`:
     ```python
     finally:
         try:
             adapter.close_all_recent_apps()
         except Exception:
             pass
     ```
   - Gọi `close_all_recent_apps(adapter._adb)` để đóng sạch các app chạy ngầm và gọi `press_home()` để đưa máy về Home Launcher sạch sẽ.

## 4. Bằng chứng kiểm chứng live (Máy 10, 11, 12)
- **Máy 10:** Mở được danh sách Following của `lipsellczaw`, nhận diện 6 nick nội bộ, bấm Follow thành công nick `anhdo829`.
- **Máy 12:** Chạy Mode 2 độc lập, tự động skip 5 nick lạ, tìm và follow thành công nick nội bộ `hectornwrigh45` từ Following list của anchor, status `OK`. Tự động close recent apps và về Home launcher sau phiên.
- **Máy 11:** Chạy Mode 2 liên tục follow thành công **7 nick nội bộ liên tiếp** trong 1 phiên.
- Full 281/281 unit tests của repo `tiktok-follow` PASS xanh 100%.

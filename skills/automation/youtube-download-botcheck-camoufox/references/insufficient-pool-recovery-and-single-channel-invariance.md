# Quy trình lấp đầy 100% kho video khi nghẽn Insufficient Pool & Chống Trộn Kênh (2026-09-17)

## 1. Nguyên tắc cốt lõi: 1 folder = 1 kênh duy nhất
- **Bất biến tối cao**: Tuyệt đối không bao giờ trộn 2 kênh vào cùng 1 folder.
- **Giải trình với User**: Khi user thắc mắc ("sao lại tìm theo niche, không lẽ 1 folder chứa 2 kênh?"), phải khẳng định ngay lập tức: **Folder dở dang chỉ kéo tiếp kênh cũ; folder trống 0 video mới kéo kênh mới**.

## 2. Đối soát & Phục hồi an toàn 2 nhóm folder
1. **Nhóm dở dang ($\ge 1$ video trên đĩa / DB)**:
   - Thường do proxy rớt hoặc bot-check giữa chừng (`download_no_media`) chứ kênh gốc không hề thiếu video.
   - **CẤM reset `source_channel = NULL`** hay cấp kênh mới (sẽ gây trộn 2 kênh vào 1 folder).
   - Phục hồi candidate failed về `discovered`:
     ```sql
     UPDATE videos SET status = 'discovered', rejection_reason = NULL 
     WHERE folder IN (<danh_sach_folder_do_dang>) AND status = 'failed' AND rejection_reason = 'download_no_media';
     UPDATE folders SET status = 'pending' WHERE folder_num IN (<danh_sach_folder_do_dang>);
     ```
2. **Nhóm trống hoàn toàn (0 video)**:
   - Reset về pending và giải phóng `source_channel = NULL` để đón nguồn mới:
     ```sql
     UPDATE folders SET status = 'pending', source_channel = NULL, video_count = 0 
     WHERE status = 'insufficient_pool' AND folder_num NOT IN (<danh_sach_folder_do_dang>);
     ```

## 3. Cơ chế Auto-Discovery tích hợp trong Downloader (`download_by_niche.py`)
- Khi folder duyệt hết pool nguồn sẵn có mà không còn kênh đủ $\ge 30$ video, downloader tự động kích hoạt `auto_discover_niche_source(folder_num, niche, args, ...)` ngay trước khi ghi nhận `insufficient_pool`.
- Tìm kiếm YouTube Shorts theo nhãn niche (`ytsearch15:<niche.label> shorts việt nam`), probe tab `/shorts`, kiểm tra exclusion & language gate.
- Khi tìm được kênh đạt chuẩn $\ge 30$ Shorts: tự động claim ledger, append vào `sources.qualified30.json`, insert candidates vào `state.db` và kéo video ngay mà không dừng batch.

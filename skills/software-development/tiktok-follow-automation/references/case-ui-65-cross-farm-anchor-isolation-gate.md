# Case UI-65: Cross-Farm Anchor Isolation Gate & Combined UID Pool Strategy

## 1. Bối cảnh & Hiện trường
- Hệ thống Taadaa Phone Farm mở rộng vận hành đồng thời 2 cụm:
  + **Cụm Kibe (máy 1–80)**: 597 UIDs. Tik1 & Tik2 có 160 nick, trong đó 115 nick đã đăng $\ge 10$ video (đủ tiêu chuẩn làm Anchor Mode 2).
  + **Cụm Admin (máy 201–280)**: 332 UIDs. Tik1 & Tik2 có 158 nick, nhưng 100% mới chỉ đăng 1–2 video.
- Runner `tiktok-follow` chạy chế độ `both` (Mode 2 Anchor Following trước $\rightarrow$ Mode 1 Search Follow bù sau).
- Khi gộp UID để mở rộng đồ thị (tránh mạng đóng khép kín dễ bị TikTok quét Graph-based Detection), phát sinh nguy cơ: Nếu sau này Tik1/Tik2 của Admin đủ $\ge 10$ video, thuật toán sẽ tự bốc nick Admin làm Anchor, làm loãng lực kéo và phân tán tiến độ về đích của Tik1/Tik2 Kibe.

## 2. Quy tắc Invariant: Hard Anchor Isolation Gate
- **Quy tắc bất di bất dịch**: Toàn bộ Anchor Mode 2 (hứng follow và mở danh sách Following) VĨNH VIỄN CHỈ ĐƯỢC CHỌN từ Tik1 & Tik2 của **CỤM KIBE (Máy $\le 80$)**.
- **Tuyệt đối cấm**: Không cho phép bất kỳ nick nào của cụm Admin (Máy $\ge 201$) trở thành Anchor Mode 2, kể cả khi nick đó sau này đã đăng $\ge 10$ video hay $\ge 50$ video.

## 3. Kiến trúc Triển khai (2 Tầng)

### Tầng 1: Code-level Hard Gate trong `follow_engine.py`
Trong hàm `anchor_uids()`:
```python
# Điều kiện lọc Anchor Mode 2:
filtered = [
    u for u in uids
    if row_uids.get(str(u).casefold(), 99) <= 2         # Row 1 hoặc Row 2 (Tik1 / Tik2)
    and row_machines.get(str(u).casefold(), 999) <= 80  # HARD INVARIANT: Chỉ thuộc máy 1-80 (Cụm Kibe)
    and row_video_counts.get(str(u).casefold(), 0) >= 10 # Đã đăng >= 10 video
    and str(u).strip().lstrip("@").casefold() != active
]
```

### Tầng 2: Data-level Combined Target Pool
- **All Targets (UIDs)**: Gộp toàn bộ 597 nick Kibe + 332 nick Admin = 929 nick (`taikhoan_run_safe_combined.xlsx`).
- **Dòng chảy tương tác**:
  + **Máy Kibe**: Lấy Anchor Tik1/Tik2 Kibe $\rightarrow$ follow Anchor $\rightarrow$ follow nick con trong list Following của Anchor (cả Kibe lẫn Admin) $\rightarrow$ bù Mode 1 nếu thiếu.
  + **Máy Admin**: Lấy Anchor Tik1/Tik2 Kibe $\rightarrow$ dùng mạng/proxy độc lập của Admin để xem video và follow Anchor Kibe $\rightarrow$ đẩy Tik1/Tik2 Kibe về đích cực nhanh bằng trust IP ngoại lai.

## 4. Triage Checklist: Đối Soát Tình Trạng Nhận Dữ Liệu Farm Admin (Feed vs Follow)
- **Cạm bẫy nhầm lẫn (Dual-Cluster Feed vs Cross-Farm Follow)**:
  Operator khi chỉnh sửa Excel bên Admin (`admin/taikhoan_dat_v2_updated .xlsx` hoặc `Tik*.xlsx`) và thấy cron nuôi acc (`phase9-runner-tiktok-feed` / `feed_session_watchdog.py`) đã chạy nhận máy Admin thì thường ngỡ rằng module Follow cũng đã tự động nhận theo.
- **Thực tế kiến trúc phân lập 2 tầng**:
  1. **Tầng Lướt Feed (`tiktok-luot nuoi acc`)**: Đã hỗ trợ Dual-Cluster, runner tự chia luồng đọc riêng `kibe/taikhoan_run_safe.xlsx` và `admin/taikhoan_run_safe.xlsx`.
  2. **Tầng Follow Runner (`tiktok-follow`)**: Là tiến trình độc lập, nạp workbook từ file cấu hình riêng (`config.example.yaml` / `config/machine*.yaml`). Hiện tại cấu hình này vẫn trỏ cứng `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` (chỉ 611 nick Kibe, 0 nick Admin).
- **4 Điều Kiện Bắt Buộc Để Follow Nhận & Chạy Cho Dàn Admin**:
  1. **File Combined Workbook**: Bắt buộc phải có pipeline xuất ra `taikhoan_run_safe_combined.xlsx` gộp cả 2 cụm (máy 1–80 và 201–280).
  2. **Hard Gate trong `follow_engine.py`**: Bắt buộc hoàn tất điều kiện `row_machines.get(...) <= 80` trong `anchor_uids()` để ngăn nick Admin bị bốc làm Anchor Mode 2.
  3. **Cập nhật Config Follow**: Trỏ `workbook` trong `config.example.yaml` và các config máy sang file `combined`. Nếu thiếu bước này, máy Admin gọi `run_follow.py` sẽ báo lỗi `CONFIG_ERROR: máy 20X không có trong safe workbook`.
  4. **Video Gate ≥ 10 video**: Máy Admin chỉ được phép đi follow khi tài khoản đạt `video_count >= 10` theo quy tắc an toàn trong `_run_follow_hook` (`under-10-videos-follow-disabled`). Nick mới 1–2 video sẽ tự động bị safe-skip.


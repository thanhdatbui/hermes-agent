# Lịch Vận Hành 4 Ca x 2 Phiên / Ngày & Quy Tắc Upload / Follow Gates

## 1. Kiến trúc phân bổ 4 Ca x 2 Phiên (HCMC Timezone)
Hệ thống nuôi acc hoạt động theo 4 Ca cố định mỗi ngày, mỗi Ca chia làm 2 phiên độc lập:
- **Ngày Chẵn (date % 2 == 0):** Chạy Row 8, Row 2, Row 4, Row 6
- **Ngày Lẻ (date % 2 == 1):** Chạy Row 7, Row 1, Row 3, Row 5

| Ca | Phiên | Khung Giờ (HCMC) | Session Index | Phân Vai Vận Hành |
| :--- | :---: | :---: | :---: | :--- |
| **Ca 4 (Đêm)** | Phiên 1 | `00:00` | 1 | Chỉ lướt feed (CẤM upload video) |
| **Ca 4 (Đêm)** | **Phiên 2** | `01:30` | 2 | **Lướt feed + Đăng video Row 8/7** |
| **Ca 1 (Sáng)** | Phiên 1 | `06:00` | 1 | Chỉ lướt feed (CẤM upload video) |
| **Ca 1 (Sáng)** | **Phiên 2** | `08:00` | 2 | **Lướt feed + Đăng video Row 2/1** |
| **Ca 2 (Trưa)** | Phiên 1 | `12:00` | 1 | Chỉ lướt feed (CẤM upload video) |
| **Ca 2 (Trưa)** | **Phiên 2** | `14:00` | 2 | **Lướt feed + Đăng video Row 4/3** |
| **Ca 3 (Tối)** | Phiên 1 | `18:00` | 1 | Chỉ lướt feed (CẤM upload video) |
| **Ca 3 (Tối)** | **Phiên 2** | `20:00` | 2 | **Lướt feed + Đăng video Row 6/5** |

- **Dead Zone:** Từ `02:30` đến `05:59` sáng không dispatch máy nào.
- **Mốc 00:00:** Tính là Ca đầu tiên của ngày mới, dùng tính chẵn lẻ của ngày mới để chọn Row.

---

## 2. Chuỗi Gọi Thực Thi (Dispatch Chain) & Flags Bắt Buộc
```
tiktok_runner.py
  └── powershell run-feed-session.ps1 -Row <R> -SessionIndex <1|2>
        └── python run_tiktok.py --account-row-index <R> --session-index <1|2> [--allow-upload-hook]
              └── multi_machine_feed_session.py
```

### Quy Tắc Chống Lỗi Upload Hook:
1. **Thiếu `--session-index` là Anti-pattern:** Nếu không truyền `-SessionIndex` từ PowerShell xuống Python runner, `config["_session_index"]` bằng `None`, gate `_effective_session_index(config) == 2` sẽ chặn sạch toàn bộ máy không cho upload video.
2. **Cấm bật `--allow-upload-hook` vô điều kiện:** Chỉ gắn cờ `--allow-upload-hook` khi `SessionIndex -eq 2`. Phiên 1 phải giữ nguyên `session_index = 1` để không upload nhầm.

---

## 3. Rào Cản Follow Hook (Safety Gates)
Mỗi máy sau khi lướt feed xong sẽ gọi `_run_follow_hook()`. Tuy nhiên sẽ bị Safe-Skip nếu chạm các rào cản:
1. **Gate Video (`video_count >= 5`):**
   - Nick có `< 5` video (0, 1, 2, 3, 4 video) trong cột `Video Đã Đăng` của file `taikhoan_run_safe.xlsx`:
   - Bị skip với lý do `under-5-videos-follow-disabled` để chống TikTok áp cơ chế shadow action-block và nhả follow ngay lập tức.
2. **Gate Warmup (`row_idx in (3, 4, 5, 6)`):**
   - Code hiện tại đang chặn cứng Row 3, 4, 5, 6 ở trạng thái nuôi thuần túy (`tik{row}-warmup-feed-only`).
   - Muốn mở follow cho các row này phải sửa điều kiện trong `_run_follow_hook`.
3. **Gate Lỗi Thiết Bị / Mạng:**
   - Nếu thiết bị dính lỗi fatal (`blocked-proxy-vpn`, offline, USB disconnect), worker thoát ngay (`is_fatal`), không bao giờ kích hoạt follow hook.

---

## 4. Kỷ Luật Đồng Bộ Cron Sang Máy Admin
- Khi user yêu cầu sync cron sang máy Admin: **CẤM TUYỆT ĐỐI** yêu cầu user thao tác thủ công, copy paste hay tự sửa file json.
- BẮT BUỘC cung cấp script automation chạy 1-lệnh (`python D:/Taadaa/deploy/admin_cron_setup.py`) để bot Hermes bên Admin tự cấu hình.

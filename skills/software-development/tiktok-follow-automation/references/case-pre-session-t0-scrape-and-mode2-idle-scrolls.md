# Case Study: Xử Lý Lệch Đối Soát Web Bằng Pre-Session Scrape T0 & Tối Ưu Cuộn Anchor Mode 2 (2026-09-27)

## 1. Vấn Đề Lệch Dương Ảo Khi Đối Soát TikTok Web
### Hiện tượng
Trong báo cáo sau phiên nuôi, đối soát Web thường xuyên báo lệch dương ảo (ví dụ: script báo 1 lượt follow nhưng web báo tăng +4).
### Nguyên nhân
Watchdog chạy sau phiên (Post-session) cố gắng tìm baseline bằng điều kiện `timestamp <= session_start_iso`. Nhưng vì trước phiên không có bước cào nào được kích hoạt gần sát giờ chạy, baseline bị trôi về snapshot lúc **07:03 sáng** (cron cào toàn farm).
Nếu trong buổi sáng nick đã chạy lướt feed + follow tự nhiên, delta giữa lúc 07:03 và cuối phiên sẽ bao gồm cả số tăng của 2-3 tiếng trước đó, dẫn đến lệch dương ảo so với 1 phiên follow chéo 15 phút.

### Giải pháp kỹ thuật (Pre-Session Scrape T0)
Nhúng trực tiếp bước cào $T_0$ vào `tiktok_runner.py` ngay trước khi `_spawn_feed_session`:
```python
# Pre-session scrape T0: lấy baseline followingCount cho Row hiện tại
try:
    from follow_runner.core.workbook import load_mapping
    _m = load_mapping(account_workbook)
    _uids = [r.tik_id for r in getattr(_m, "rows", []) if getattr(r, "account_row_index", None) == row and getattr(r, "tik_id", None)]
    if _uids:
        subprocess.run([target_python(), r"D:\Taadaa\tools\tiktok_account_tracker.py", "--usernames", *_uids, "--workers", str(min(10, len(_uids)))], capture_output=True, timeout=60, check=False)
except Exception:
    pass
```
Số liệu delta khi đối soát sẽ tính chính xác theo $\Delta = T_1 - T_0$.

---

## 2. Điểm Nghẽn Cuộn Tìm Nick Farm Trong Following List Của Anchor (Mode 2)
### Hiện tượng
Script vào danh sách Following của Anchor nhưng dừng sớm và báo `đã follow sẵn (skip)` dù danh sách của Anchor còn rất nhiều nick.
### Nguyên nhân
1. Runner chỉ follow các nick nội bộ farm (`internal_uids`), các nick người ngoài (external) bị bỏ qua.
2. Ngưỡng dừng `idle_scrolls >= 5`: Nếu cuộn 5 lần liên tiếp mà chỉ gặp nick người ngoài, runner ngắt vòng lặp tìm kiếm vì cho rằng danh sách đã cạn nick farm.

### Giải pháp kỹ thuật
1. Nâng ngưỡng `idle_scrolls` từ **5 lên 15 lần cuộn** trong `mode2_follow_followers.py`.
2. Safe-skip Anchor: Khi 1 Anchor đã hết nick farm hoặc lỗi mở tab, chuyển sang Anchor tiếp theo trong pool thay vì kết thúc session sớm.

---

## 3. Rà Soát Máy Trống Slot Row 3 Cụm Admin (M201-280)
Khi phát hiện máy bị báo `Trống slot/chưa có nick`:
- Kiểm tra file Excel master `taikhoan_dat_v2_updated .xlsx` và file con `tik3.xlsx`.
- 15 máy cụm Admin (`M235, M238, M243, M249, M251, M255, M261, M262, M263, M264, M266, M267, M269, M273, M274`) chỉ được gán nick ở các Slot 1, 2, 5, 7, 8 trong master DAT ➔ Cột C (ID) trong `tik3.xlsx` để trống (`None`) ➔ Hệ thống bỏ qua là đúng thiết kế.

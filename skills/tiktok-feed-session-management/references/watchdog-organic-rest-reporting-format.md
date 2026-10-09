# Tiêu Chuẩn Format Báo Cáo Telegram Watchdog: Dưỡng Sinh (Organic Rest) & Bóc Tách Lý Do Bỏ Qua

## 1. Bối cảnh & Mục tiêu
Khi áp dụng cơ chế **Per-Account Organic Rest (1/3)** (MD5 hash chia đều ~33.33% số nick mỗi ngày chỉ lướt Feed thuần, không chạy Follow Hook và không chạy Upload Hook), các máy này trả về lý do:
- Follow hook: `reason="organic-rest-day-pure-feed"`, `action="skip_follow_rest_day"`
- Upload hook: `reason="organic-rest-day-pure-feed"` hoặc `reason="organic-rest-day-no-upload"`

Nếu watchdog không hiển thị rõ ràng:
1. Người vận hành không phân biệt được máy nào đang nghỉ dưỡng sinh theo kế hoạch vs máy bị lỗi kịch bản/thiếu tài nguyên.
2. Dễ nhầm lẫn số máy bỏ qua (Skip) thành lỗi (Error), hoặc kích hoạt cảnh báo đỏ Farm Alert ảo khi số máy skip lớn (>10 máy).

## 2. Quy chuẩn Format Báo Cáo Telegram

### A. Khối Hiển thị Chế độ Dưỡng Sinh (Đặt sau khâu Lướt Feed, trước Follow chéo)
```text
• Chế độ Dưỡng Sinh (Organic Rest ~33%):
  🌿 Nghỉ dưỡng sinh ({len(rest_machines)} máy): {m_rest_str} (Chỉ lướt feed, 0 follow, 0 up)
```
*(Nếu không có máy nào trong ca nghỉ dưỡng sinh: `🌿 Nghỉ dưỡng sinh: Không có`)*

### B. Bóc tách Mục Bỏ qua của Follow Chéo
Thay vì chỉ hiển thị `+ Bỏ qua (N): M1, M2...`, phân rã thành các nhóm nguyên nhân:
```text
  + Bỏ qua ({total_skipped} máy):
    - Đang dưỡng sinh ({len(fl_rest)} máy): {fl_rest_str}
    - Chưa đủ 10 video ({len(fl_under10)} máy): {fl_under10_str}
    - Lý do khác ({len(fl_other)} máy): {fl_other_str}
```
*(Hoặc hiển thị inline rút gọn khi danh sách trống: `+ Bỏ qua (N): Đang dưỡng sinh (X), Chưa đủ 10 video (Y), Khác (Z)`)*

### C. Bóc tách Mục Bỏ qua của Đăng Video (Upload Hook)
```text
  + Bỏ qua ({total_skipped} máy):
    - Đang dưỡng sinh ({len(up_rest)} máy): {up_rest_str}
    - Chưa có video / chưa render ({len(up_novideo)} máy): {up_novideo_str}
    - Lý do khác ({len(up_other)} máy): {up_other_str}
```

## 3. Quy tắc Đồng Bộ 3 Vị Trí (Chống Sync Drift)
Bất kỳ thay đổi nào trong `feed_session_watchdog.py` bắt buộc phải được đồng bộ vào cả 3 đường dẫn:
1. `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py` (Script chạy cron thực tế)
2. `D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py` (Bản deploy snapshot)
3. `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py` (Source repo)

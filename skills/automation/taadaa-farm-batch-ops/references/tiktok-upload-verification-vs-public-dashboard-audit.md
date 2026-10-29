# TikTok Upload Verification vs Public Dashboard Audit (Post-Session Reconcile)

## 1. Bối cảnh & Cảnh báo kiến trúc (Architectural Invariant)
Khi cân nhắc cơ chế kiểm tra video đã đăng thành công trên TikTok:
- **Hàm đếm video tại Profile (`_verify_profile_post_increment` / `_count_profile_video_tiles_across_grid`) trong luồng upload real-time:**
  - Tiềm ẩn rủi ro false-negative do độ trễ nén/xử lý CDN của TikTok (15s – 45s app mới cập nhật tile mới trên UI profile).
  - Chi phí ADB/atx-agent swipe grid tới 6 lần và dump XML/screenshot perceptual hash làm chậm luồng 25-40s/máy, dễ gây văng timeout trên thiết bị cũ.
- **Dữ liệu cào từ TikTok Public Web / Dashboard (`tiktok_account_tracker.py`):**
  - **TUYỆT ĐỐI CẤM** dùng cào public web để verify thời gian thực ngay lúc vừa bấm Đăng.
  - **Nguyên nhân thực nghiệm**: TikTok CDN cache public profile trễ từ 30 phút đến vài tiếng (thực tế ca 29/10 Row 5: 90/123 máy upload thành công nhưng public web vẫn hiển thị `videoCount = Ledger - 1`). Verify real-time bằng cào web sẽ gây báo lỗi oan 100% và dễ dính SlardarWAF/cháy proxy pool 67.
  - **CỰC KỲ NÊN DÙNG** cho bước **Audit đối soát sau ca (Post-Session Reconciliation)** sau 1–2 giờ.

---

## 2. Công cụ chuẩn đối soát sau ca: `audit_upload_dashboard_reconcile.py`
Vị trí: `D:/Taadaa/tools/audit_upload_dashboard_reconcile.py`

### Lệnh tra cứu O(1):
```bash
python D:/Taadaa/tools/audit_upload_dashboard_reconcile.py --date <YYYY-MM-DD> [--row <1..8>] [--json-output]
```

### Tiêu chuẩn phân loại kết quả:
1. `CONFIRMED_MATCH`: Số video trên Tracker SQLite >= Số video upload ghi nhận trong `shift_upload_history.json`.
2. `POSSIBLE_DELAY_OR_BLOCKED`: Tracker < Ledger sau nhiều giờ $\rightarrow$ Cảnh báo video bị ẩn, vi phạm tiêu chuẩn cộng đồng, hoặc kẹt kiểm duyệt nội dung.
3. `ACCOUNT_ABNORMAL`: Trạng thái nick trên Tracker không phải `LIVE` (bị `NOT_FOUND`, `BANNED`).
4. `NO_TRACKER_DATA`: Chưa có snapshot cào trong SQLite.

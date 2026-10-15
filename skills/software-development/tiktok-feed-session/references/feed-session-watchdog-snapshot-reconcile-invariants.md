# TikTok Feed Session Snapshot Reconciliation & Watchdog Invariants

> **Cập nhật 15/10/2026:** Khắc phục triệt để lỗi lệch pha thời gian (38s) giữa crawler và watchdog cửa sổ phiên.

---

## 1. Bản Chất Lỗi Lệch Pha (Race Condition 38 Giây)
- **Hiện tượng:** Watchdog Phiên 1 (chốt lúc 08:00:22) gọi crawler cào web. Crawler ghi snapshot kết thúc lúc `08:00:38`.
- **Nguyên nhân:** Watchdog truy vấn cứng `timestamp <= '08:00:00'`, hụt mất 38 giây nên lấy lại snapshot cũ `07:04:26`. Phiên 1 báo lệch âm (-20 lượt). Sang Phiên 2, delta tính từ snapshot cũ dồn toàn bộ 20 lượt vào Phiên 2.
- **Thực tế:** Cả 4 máy nghi shadow-drop (`M4`, `M26`, `M36`, `M37`) follow thành công 100% trên server TikTok thật.

---

## 2. Invariants Xử Lý Kỹ Thuật Chuẩn
1. **Buffer +10 Phút (`buffer_reconcile_iso`):**
   - Mở rộng cửa sổ tìm snapshot: `query_end_iso = buffer_reconcile_iso(session_end_iso, 10)`.
2. **Fail-Safe Baseline Cho Phiên 1:**
   - Phiên 1 tuyệt đối KHÔNG buffer `session_start_iso` tiến về tương lai để tránh nuốt mất follow đầu ca.
   - Phiên 2 trở đi buffer `session_start_iso` (+10m) để bắt khớp snapshot chốt ca của Phiên 1.
3. **Guard Chống Start >= End:**
   - Dùng `parse_reconcile_iso_dt()` chuyển datetime object để so sánh chuẩn xác. Nếu `start_dt >= end_dt`, fallback về `session_start_iso` gốc và tăng `guard_triggered`.
4. **Regex Phân Biệt Phiên Chống False-Positive:**
   - Sử dụng Negative Lookbehind và Lookahead:
     ```python
     has_p1 = bool(re.search(r"(?<![a-z0-9])(?:phien|session|p)[\s_.-]*1(?![0-9])", s_lower))
     has_later = bool(re.search(r"(?<![a-z0-9])(?:phien|session|p)[\s_.-]*([2-9]|\d{2,})", s_lower))
     ```
   - Chặn đứng false-positive với `ap1_cluster`, `xp1_ca2`, `phien10`.
5. **Thread-Safety Cho Metrics:**
   - Bọc `threading.Lock()` quanh mọi thao tác mutate dict `RECONCILE_METRICS`.

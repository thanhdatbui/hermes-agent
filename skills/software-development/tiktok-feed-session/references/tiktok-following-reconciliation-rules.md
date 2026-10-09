# TikTok Following Reconciliation & Watchdog Invariant

## 1. Bản chất hai nguồn Follow trong một phiên nuôi TikTok
Trong mỗi phiên nuôi (feed session), một tài khoản TikTok có 2 nguồn tăng `following`:
1. **Follow tự nhiên (Natural follows):** Phát sinh ngẫu nhiên khi lướt Feed video (theo tỷ lệ cấu hình `like_rates`/`follow_rates` trong `summary.txt` -> `natural_follows: {'for-you': X, 'friends': Y}`).
2. **Follow chéo (Cross/Hook follows):** Phát sinh từ module chạy sau phiên lướt (`tiktok-follow` -> `follow_result.json` -> `followed: [anchor_uid, ...]`).

## 2. Nguyên tắc đối soát TikTok Web (Anti-False Discrepancy)
- **Lỗi thường gặp:** Hàm đối soát chỉ đọc `all_follows.get(m, {}).get("followed", [])` (Follow chéo) mà bỏ quên `natural_follows`, dẫn đến báo cáo lệch ảo (ví dụ: script báo 1 lượt chéo nhưng Web tăng +3 lượt do có 2 lượt tự nhiên -> báo lệch +2).
- **Quy tắc tính chuẩn:**
  ```python
  cross_cnt = len(all_follows.get(m, {}).get("followed", [])) if all_follows else 0
  nat_cnt = sum((all_machines.get(m, {}).get("natural_follows") or {}).values()) if all_machines else 0
  rep_cnt = cross_cnt + nat_cnt
  ```
- **Xác định tập máy cần đối soát:** Máy cần đối soát là tập hợp `fl_success` (chạy follow hook thành công) **VÀ** bất kỳ máy nào có `natural_follows > 0` trong phiên lướt feed.

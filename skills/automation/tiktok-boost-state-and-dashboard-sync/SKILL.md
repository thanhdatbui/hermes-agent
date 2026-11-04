---
name: tiktok-boost-state-and-dashboard-sync
description: "Quy chuẩn kiến trúc đồng bộ cờ cắn đề xuất 5 ngày (5-day hold boost state), bypass dưỡng sinh upload và hiển thị realtime trên TikTok Dashboard."
---
# TikTok 5-Day Boost State & Dashboard Synchronization Architecture

## 1. Ngữ cảnh & Điểm nghẽn thực tế
Trước đây, hệ thống nhận diện nick cắn đề xuất trên Phone Farm gặp 2 vấn đề lớn:
1. **Bẫy dao động 24h ("Hôm nay cắn mai mất"):** Dashboard chỉ so sánh delta $T$ vs $T-1$. Một video đang cắn đề xuất thường phân phối theo chu kỳ 3-5 ngày. Sang ngày hôm sau delta tim/follower giảm nhẹ dưới ngưỡng khiến cờ đề xuất biến mất, làm mất nhịp ưu tiên đăng video (48h/lần) và khiến runner ép nick quay lại ngày nghỉ dưỡng sinh 1/3 (2.5-3 ngày/video).
2. **Lệch pha giữa Core Runner và Dashboard:** Core runner (`tiktok-luot nuoi acc`) có bảng `account_boost_state` để bypass ngày nghỉ dưỡng sinh, nhưng hàm `update_account_boost_states()` không được tự động kích hoạt sau các ca quét snapshot hàng ngày của `tiktok_account_tracker.py`, và Dashboard (`port 1905`) không đọc cờ boost từ bảng này.

---

## 2. Tiêu chuẩn nhận diện Trending & 5-Day Boost State
Đồng bộ nhất quán giữa Web Dashboard và Core Runner:
$$\text{trending} = (\Delta\text{Follower} \ge 20) \;\mathbf{HOẶC}\; (\Delta\text{Heart} \ge 50) \;\mathbf{HOẶC}\; (\Delta\text{Follower} \ge 30 \;\mathbf{VÀ}\; \Delta\text{Heart} \ge 200) \;\mathbf{HOẶC}\; (\Delta\text{Heart} \ge 500) \;\mathbf{HOẶC}\; (\text{Follower} \ge 1.000 \;\mathbf{VÀ}\; \text{LIVE})$$

* **Cửa sổ giữ nhịp 5 ngày (`DEFAULT_HOLD_DAYS = 5`):**
  - Khi thỏa mãn điều kiện trending, tài khoản được ghi nhận vào `account_boost_state` với `is_boost = 1` và `boost_until = today + 5 days` (chốt tại `23:59:59` của ngày thứ 5).
  - Phân loại reason tương ứng: `heart_surge`, `follower_live`, `heart_delta`, `follower_delta`.
  - Trong suốt 5 ngày này, dù delta 24h có giảm thì cờ boost vẫn hoạt động liên tục.

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.

# Watchdog Follow Reconciliation & Shadow-Action Mitigation (2026-10-06)

## 1. Cơ chế đối soát Follow: Script Count vs TikTok Web DB
- Khi chạy feed + follow:
  - Máy có thể có **Follow Tự Nhiên** (lướt feed chạm follow trên video) và **Follow Chéo** (Mode 2 / Mode 1).
  - Follow tự nhiên trên feed không có bước vào profile đối phương soi nút.
  - Follow chéo Anchor: Có bước xem video $\rightarrow$ follow $\rightarrow$ back profile $\rightarrow$ vuốt kéo reload (`pull_to_refresh_profile`).

## 2. Bản chất hiện tượng "Lệch âm ảo" cuối phiên
- Khi nick bị TikTok shadow ban / limit action:
  - Ở 1-2 action đầu, App điện thoại có thể hiển thị nút "Đã follow" do UI optimistic update.
  - Nhưng TikTok Backend ngầm drop toàn bộ action (không commit vào DB toàn cục).
  - Đến lượt kế tiếp hoặc sau khi vuốt reload profile, app đồng bộ từ server và nút văng ngược lại "Follow" đỏ $\rightarrow$ Runner bắt dính `FOLLOW_FAILED`.
  - Cuối phiên, cào snapshot Web thấy số Following tăng +0. Nếu watchdog lấy `0 - reported` thì sẽ la toáng lên báo "Lệch -2".

## 3. Kỷ luật xử lý cho Watchdog:
- Nếu một máy kết thúc phiên với cờ `FOLLOW_FAILED` (bị nhả follow ở bất kỳ nhịp nào trong phiên):
  - **Follow tự nhiên:** Trừ sạch ra, không ghi nhận là follow thành công.
  - **Đối soát Web:** KHÔNG phạt lệch âm. Ghi chú rõ: `Web +0 (Bị nhả follow trong phiên, TikTok server drop action)`.

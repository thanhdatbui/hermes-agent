# [DEPRECATED / SUPERSEDED] Ca Nuôi (4 Ca x 2 Phiên Cũ) & Night Chain Đêm

> ⚠️ **CẢNH BÁO LỊCH CŨ ĐÃ HẾT HIỆU LỰC:** Lịch 4 Ca (có Ca 4 lúc 00:00 - 01:30 đêm) và Night Chain đêm đã bị bãi bỏ hoàn toàn từ ngày 11/10/2026.
> **Lịch chuẩn hiện tại là Chu kỳ 4 ngày x 3 Ca / ngày (BỎ HOÀN TOÀN CA 0H ĐÊM):**
> - Ca 1 (Sáng): 06:00 (P1) & 08:00 (P2)
> - Ca 2 (Trưa): 12:00 (P1) & 14:00 (P2)
> - Ca 3 (Tối):  18:00 (P1) & 20:00 (P2)
> - Dead Zone: 21:30 - 05:59 sáng (nghỉ hoàn toàn, hạ nhiệt S7, dọn cache 03:00 - 04:30).

---

## 1. Cấu Trúc Ca Nuôi (4 Ca x 2 Phiên - LƯU TRỮ LỊCH SỬ)
- **1 Ca = 2 Phiên:**
  - Phiên 1: Feed + tương tác + follow lượt 1 (~15-18 follow, ~45-50p).
  - Khoảng nghỉ giữa 2 Phiên (Gap A): ~45 - 75 phút (tự nhiên đối với cùng 1 user trên máy).
  - Phiên 2: Feed + follow lượt 2 (~15-18 follow) + Đăng video (upload hook, ~45-50p).
  - **Tổng thời gian hoàn thành 1 Ca:** Tối thiểu 2h15m - 2h30m (CẤM tính nhầm là xong sau 45p).
- **Khoảng nghỉ giữa 2 Ca khác nhau (Gap B):** >= 3 tiếng (vùng đệm nguội máy, wear-leveling, xoá dấu chân co-location tài khoản).

## 2. Chuỗi Đêm Tuần Tự (Night Chain Sequential)
- Kích hoạt lúc `00:00` (Ca 4 - Row 7/8).
- Tuyệt đối chạy **tuần tự nối tiếp** (Phase sau CHỈ chạy khi Phase trước hoàn tất return code):
  - **Phase 1 (00:00 -> ~02:20):** Ca 4 Feed Row 7/8 (chạy xong cả 2 phiên P1 + P2).
  - **Phase 2:** Reg Gmail (khởi động ngay khi Phase 1 return).
  - **Phase 3:** Add 2FA (khởi động ngay khi Phase 2 return).
- Bỏ hoàn toàn Reg TikTok dồn ban đêm.

## 3. Quy Luật On-Demand Reg Theo Ca
- Ca nào máy nào thiếu acc ở Row của Ca đó thì mới chạy reg trực tiếp trên đúng các máy thiếu.
- **Nút thắt đếm slot workbook (`load_registered_mailboxes`):**
  - Chỉ đếm các dòng THỰC SỰ CÓ `tiktok_id` không rỗng (`if tiktok_id and stt_idx is not None...`).
  - CẤM đếm cả dòng trống `ID is None` vì sẽ gây lỗi tưởng nhầm máy đã đủ 8 acc.
- **Tự động cấp phát Mail (`buy_hotmail.py`):**
  - Hỗ trợ `--append-kibe N --target-machines M1,M2...` nạp trực tiếp vào `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.

# Phân Biệt Quota Trần Đầu Phiên vs Số Lượt Bấm Thực Tế & Khoảng Nghỉ Điện Thoại Giữa 2 Phiên

## 1. Bản Chất Công Thức Cấp Quota Đầu Phiên: Dải Bám Trần Hẹp `[cap - 2, cap]`
Trong `follow_state.py`, hàm `_determine_budget_tier` tính toán budget cho mỗi phiên theo công thức:
```python
lo = max(1, cap - 2)
return _random.randint(lo, cap), "full"
```
- **Ý nghĩa:** Đây là **HẠN MỨC TRẦN KHỐNG CHẾ TRÊN (Session Burst Limit)** được cấp cho một lần mở app chạy (5–10 phút), tuyệt đối không bấm vượt con số này.
- **Biên độ dao động ngẫu nhiên:** Luôn là 3 con số liền kề ($\pm 2$ lượt tính từ `cap` của nick).
  - Với Nhóm B (Máy Chẵn - Thử nghiệm Max Volume, trần phiên `cap = 20`): Budget random ngẫu nhiên trong dải **`[18, 20]`** (18, 19 hoặc 20 lượt).
  - Với nick Cựu Binh Veteran (như M12, `active_ceiling = 27`): Budget random trong dải **`[25, 27]`** lượt.
- **Mục đích thiết kế dải hẹp:**
  1. Tránh pattern cố định 1 con số khiến TikTok gắn cờ bot.
  2. Không random quá rộng (như 10-20) gây sụt giảm sản lượng khai thác của nick khỏe.

---

## 2. Vì Sao Máy Có Hạn Mức 27 Mà Lại Bấm 16 Lượt (Phiên 1) và 12 Lượt (Phiên 2)?
Cần phân biệt rạch ròi giữa **Hạn mức cấp** và **Số lượt máy thực sự bấm được**:
- **Cơ chế dừng an toàn (Exhaustion vs Drop):**
  - Máy chỉ bấm follow khi tìm thấy nick mục tiêu hợp lệ (profile sạch, có video, đúng đối tượng).
  - Khi duyệt hết danh sách nick con của Anchor trong phiên (Module 2) và hết nick nợ follow hợp lệ (Module 1 bù), máy **chủ động dừng phiên an toàn (`status: OK`)** thay vì cố bấm bừa nick rác để vét cho đủ quota.
  - Ví dụ M12 sáng 31/10:
    - Phiên 1 (06:00): Ăn 11 nick Anchor + 5 nick bù Mode 1 = **16 lượt**. Đến nick thứ 6 không tìm thấy kết quả tìm kiếm $\rightarrow$ Dừng phiên thành công.
    - Phiên 2 (08:00): Bốc anchor mới, cào và ăn trọn **12 nick** của anchor này $\rightarrow$ Hết mỏ nick hợp lệ, dừng phiên thành công.
- **Tổng sản lượng cả ca:** Là **tổng cộng dồn cả 2 phiên** (`16 + 12 = 28 lượt sạch 100%`).

---

## 3. Khoảng Nghỉ Giữa 2 Phiên & Giữa 2 Ca Nuôi

### Cấu trúc lịch trình:
- 1 ngày có 3 Ca nuôi chính (mỗi ca gồm 2 phiên cách nhau 2 tiếng):
  - **Ca 1 (Sáng):** Phiên 1 (06:00) $\rightarrow$ Phiên 2 (08:00) $\rightarrow$ Nghỉ lớn (08:45 – 12:00).
  - **Ca 2 (Trưa):** Phiên 1 (12:00) $\rightarrow$ Phiên 2 (14:00) $\rightarrow$ Nghỉ lớn (14:45 – 18:00).
  - **Ca 3 (Tối):** Phiên 1 (18:00) $\rightarrow$ Phiên 2 (20:00) $\rightarrow$ Nghỉ đêm đến 06:00 hôm sau.

### Khoảng nghỉ giữa 2 phiên (ví dụ 06:45 – 08:00):
- **Trên điện thoại Phone Farm (Samsung S7):** **HOÀN TOÀN KHÔNG CÓ cron nào đụng vào**. Toàn bộ máy ở trạng thái rảnh an toàn để ngắt tiến trình, hạ nhiệt và nghỉ ngơi trước khi vào Phiên 2.
- **Trên máy tính PC:** Chỉ chạy các cron đối soát SQLite hoặc quản lý profile GPM PC (`gpm-lifecycle-sync-watchdog`, `daily-stale-upload-accounts-watchdog`), tuyệt đối không gửi lệnh ADB hay can thiệp điện thoại.

### Hiện tượng 2 phiên "nối đuôi nhau":
- Bình thường mỗi phiên 160 máy chạy chỉ mất **35 – 45 phút** (có quãng đệm nghỉ ~1 tiếng trước phiên sau).
- Khi có máy bị kẹt UI, stagger retry kéo dài (ví dụ M72 chạy đến 07:28, batch đóng lúc 07:40), Phiên 1 vừa kết thúc thì chỉ 20 phút sau (08:00) scheduler đã kích hoạt Phiên 2, tạo cảm giác 2 phiên sát rạt nhau. Đây là hiện tượng lệch nhịp do máy đơn lẻ kéo dài batch, không phải do lịch bị thay đổi.

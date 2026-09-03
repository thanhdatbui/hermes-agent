# Quy Trình Tự Động Xử Lý Lỗi (AI Vision Auto-Recovery) & Ma Trận Tương Tác 3 Tab (19/08)

## 1. Pitfall: Chống Nhận Diện Lỗi Bằng Regex / If-Else Chuỗi Tĩnh Rập Khuôn
- **Hiện tượng lỗi (Máy 46 - 14:41 19/08)**: 
  - Màn hình máy thực tế đang ở trang cá nhân nhãn hàng Closeup (`@closeupvn`) có nút Follow đỏ và banner TikTok Shop "Mua ngay".
  - Do code `alerts.py` dùng `if...elif...else` kiểm tra chuỗi `error_reason` thô sơ, khi chuỗi không match các keyword cơ bản (`live`, `clear_all`), nó rơi vào nhánh `else` mặc định và trả về:
    `Vấn đề: Dừng phiên bất thường` | `Đã xử lý: Đã tự động dọn app đưa máy về Home`.
  - **Hậu quả**: Không phân tích được đúng bản chất sự việc trên màn hình, máy móc và vô tác dụng.

- **Yêu cầu Bắt Buộc (AI Vision-Driven)**:
  - Phải dùng AI Vision (hoặc model đa phương thức phân tích cả Screenshot + UI XML) để đọc trực tiếp giao diện.
  - Phân tích đúng: Màn hình đang kẹt ở đâu, có nút gì, cần tap/vuốt gì để giải phóng.
  - Trích xuất ĐÍCH DANH lý do kỹ thuật gốc trong báo cáo, tuyệt đối CẤM dùng từ ngữ chung chung như "Dừng phiên bất thường".

---

## 2. Quy Trình Auto-Recovery Khép Kín 5 Bước Chuẩn
```
┌─────────────────────────┐
│ 1. Báo Hiện Trường       │ ──> Chụp ảnh nguyên trạng (Banner Đỏ [MAY XX]) gửi về Farm Alerts
└─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│ 2. AI Vision & Vá Code  │ ──> Phân tích ảnh/XML -> Viết code xử lý vào canonical script
└─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│ 3. Review Độc Lập       │ ──> Xuất diff, gọi plan-review / Claude CLI --effort max kiểm tra
└─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│ 4. Test Tại Hiện Trường │ ──> Chạy test ngay tại màn hình kẹt (CẤM reset từ đầu)
└─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│ 5. Chạy Hết Script & Báo│ ──> Chạy tiếp đến SUCCESS -> Báo cáo tóm tắt & Commit/Push toàn farm
└─────────────────────────┘
```

---

## 3. Ma Trận Tương Tác 3 Tab & Tỉ Lệ Follow Chuẩn

| Tab TikTok | Tỉ Lệ Lướt (%) | Tỉ Lệ Like (%) | Tỉ Lệ Follow (%) | Thời Gian Xem (Watch Range) |
| :--- | :---: | :---: | :---: | :---: |
| **Dành Cho Bạn (For You)** | **85%** | **8%** | **6%** *(Organic)* | **3.0s – 10.0s** |
| **Đang Theo Dõi (Following)** | **8%** | **15%** | **0%** *(Đã follow)* | **4.0s – 12.0s** |
| **Bạn Bè (Friends)** | **7%** | **25%** | **0%** *(Đã là bạn bè)* | **5.0s – 15.0s** |

### Logic Cân Bằng Follow Organic vs Follow Chéo:
- 1 ngày nick lướt ~150 video For You ➔ Sinh ra **~9-10 organic follows tự nhiên**.
- So sánh với budget 20-30 targeted follows/ngày từ repo `tiktok-follow` ➔ Tỉ lệ đạt **1 tự nhiên : 2.5 - 3 follow chéo** (lớp đệm tự nhiên chiếm ~30%).
- Đảm bảo đồ thị quan hệ (Graph Diversity) tự nhiên, chống bị gắn cờ "Dedicated Follow Bot".

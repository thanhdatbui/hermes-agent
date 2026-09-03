# Target Selection, Capacity Invariants & Night Pipeline Execution (2026-08-28)

## 1. Giới Hạn Dung Lượng & Tiêu Chí Lọc Target (Target Eligibility Invariants)

### A. Giới hạn cứng $\le 6$ accounts/máy
- **Quy tắc:** Mỗi máy trong Farm (80 máy) chỉ chứa tối đa 6 tài khoản TikTok.
- **Cơ chế đếm:** Đếm số lượng TikTok ID thực tế đã ghi nhận trong bảng tracking chuẩn (`taikhoan_dat_v2_updated .xlsx`).
- **Xử lý:** Khi một máy đã đạt $\ge 6$ TikTok ID $\rightarrow$ **Loại vĩnh viễn** khỏi mọi đợt reg tiếp theo, tuyệt đối không cấp thêm email nguồn.

### B. Điều kiện lọc target kép (Dual Eligibility Condition)
Một máy chỉ được chọn vào manifest reg (`_clean_targets.json`) khi đồng thời thỏa mãn cả hai điều kiện:
1. `machine_account_count < 6`: Máy chưa đủ 6 acc TikTok.
2. `has_unused_source_mail`: Máy còn email hợp lệ trong kho nguồn (`gmail_clean_v2.xlsx`) mà **chưa hề xuất hiện** trong sheet tracking.
*(Thiếu một trong hai điều kiện $\rightarrow$ Tự động bỏ qua / Skip).*

---

## 2. Quy Tắc Chạy Chuỗi Đêm (Night Chain Pipeline: Gmail ➔ TikTok)

### A. Cơ chế tuần tự nối đuôi (Blocking Sequential Execution)
- Script điều phối: `scripts/run_night_chain_pipeline.py` (Kích hoạt lúc **01:00 AM** qua Cron `night-chain-reg-pipeline`).
- **Thứ tự thực thi:**
  1. **01:00 AM:** Khởi động **Phase 1 (Reg Gmail)** và chờ (block) cho đến khi toàn bộ Gmail hoàn tất 100%.
  2. **Flush:** Nghỉ nhẹ 10 giây để hệ thống lưu và flush dữ liệu Excel.
  3. **Phase 2 (Reg TikTok):** Chỉ được gọi **sau khi Phase 1 Gmail đã kết thúc hoàn toàn**.
  4. **Báo cáo:** Gửi duy nhất 1 tin nhắn tổng kết về Telegram.
- **CẤM:** Không được hiểu nhầm hoặc đặt giả định mốc giờ cố định cho Phase 2 (như 01:10); Phase 2 phụ thuộc 100% vào thời điểm kết thúc thực tế của Phase 1.

### B. Giới hạn tải & số lượng (Throttling & Batch Caps)
- Nhằm tránh bị TikTok gắn cờ rate-limit (*"Bạn truy cập dịch vụ của chúng tôi quá thường xuyên"*) hoặc dính Captcha liên hoàn:
  - **`--max-targets=30`:** Giới hạn mỗi ca/đêm chỉ reg tối đa 30 máy thành công.
  - **`--max-workers=6`:** Giới hạn tối đa 6 worker chạy song song cuốn chiếu (stagger delay 2s–8s).

---

## 3. Quy Tắc Vận Hành Đa Cụm Máy (Multi-Machine Farm Separation)

- **CẤM over-register để chuyển máy:** Tuyệt đối không cố reg vượt quá 6 acc trên một máy rồi logout chuyển sang dàn máy khác (ví dụ: máy Admin).
- **Lý do:** TikTok ghim chặt Device ID, Android ID, GPU, MAC và IP mạng lúc đăng ký. Đổi thiết bị đột ngột trên tài khoản mới chưa đủ trust score sẽ kích hoạt checkpoint xác minh hoặc đình chỉ tài khoản hàng loạt.
- **Quy trình chuẩn:** Dàn máy mới (80 máy sạch) phải tự chạy reg trực tiếp trên chính thiết bị của nó để bước vào quy trình nuôi 14 ngày an toàn.

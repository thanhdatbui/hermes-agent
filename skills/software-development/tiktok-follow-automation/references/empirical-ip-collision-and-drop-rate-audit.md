# Phân Tích Thực Nghiệm: Trùng IP (1 IP : 2 Máy) vs Tỷ Lệ Nhả Follow Toàn Farm

## 1. Bối cảnh bài toán & Giả định ban đầu
- Trong kiến trúc Farm Taadaa (80 máy Kibe), 40 cổng proxy được chia sẻ cho 80 máy theo tỷ lệ 1:2 (Ví dụ: M1 và M39 chung port 5101, M14 và M52 chung port 5116).
- Sáng ngày 09/10/2026, 6 nick nòng cốt dính `FOLLOW_FAILED` và bị tống vào Cooldown 3 ngày, trong đó có cặp M1 & M39 (chung port 5101) và M14 & M52 (chung port 5116).
- **Nghi vấn ban đầu:** Liệu việc 2 máy cùng dùng chung 1 IP đi follow có phải là nguyên nhân kích hoạt thuật toán TikTok trừng phạt và nhả follow hay không? Có cần khóa cứng Mutex (chỉ cho 1 máy follow, máy kia cấm follow trong phiên/ngày) hay không?

## 2. Đo đạc dữ liệu thực tế (Empirical Audit 301 Ca Chạy: 31/08 - 09/10/2026)
Đối soát chéo giữa `PROXYgandienthoai.xlsx` và toàn bộ lịch sử follow chi tiết trong `runs/state/follow_state_*.json`:

### Bảng tổng hợp đối soát:
- **2 Máy cùng chạy trên 1 IP trong ngày (Co-run):** 120 máy-ca | Bị nhả: 24 ca | **Tỷ lệ nhả: 20.0%**
- **Chỉ 1 Máy chạy lẻ trên 1 IP trong ngày (Solo):** 181 máy-ca | Bị nhả: 39 ca | **Tỷ lệ nhả: 21.5%**

### Các bằng chứng phản biện cốt lõi:
1. **Tỷ lệ nhả tương đương nhau (20.0% vs 21.5%):** Việc 2 máy cùng chạy trên 1 IP hoàn toàn không làm tăng tỷ lệ dính phạt so với khi chạy đơn lẻ.
2. **Bằng chứng ngày sạch cày tải nặng:**
   - Ngày 31/08: Có 40 máy (20 cặp trùng IP) cùng chạy follow cày tới 40-50 follow/ca $\rightarrow$ **0% ca bị nhả**.
   - Ngày 01/09: Có 32 máy (16 cặp trùng IP) cùng chạy follow $\rightarrow$ **0% ca bị nhả**.
3. **Bằng chứng ngày dính nhả khi chạy 100% Solo:**
   - Ngày 05/10: 100% các máy chạy Solo (0 cặp trùng IP) $\rightarrow$ Vẫn có **7 máy bị nhả (53.8%)**.
4. **Bản chất nhả follow:** Mang tính chất **Đợt càn quét định kỳ của nền tảng (Platform Scan Waves)**. Vào ngày TikTok siết gắt (03/10, 07/10, 09/10), cả máy chạy đơn lẫn máy chạy đôi đều bị quét với tỷ lệ 50% - 80%.

## 3. Bài học về Quản trị rủi ro & Kỷ luật điều phối
1. **Chống Over-Engineering & Cắt giảm 50% công suất mù quáng:**
   - Không vội vàng đưa ra kết luận giả định (ví dụ: cấm 2 máy cùng IP chạy follow) dẫn đến việc hy sinh 50% account capacity trong mỗi ca mà không dựa trên số liệu đo đạc thực tế.
   - Luôn viết script audit dữ liệu lịch sử đối chứng (A/B testing trên data thật) trước khi kết luận và đề xuất kiến trúc.
2. **Kỷ luật "Tra dữ liệu trước khi chốt chiến lược" (User Mandate):**
   - Khi phát sinh hiện tượng nghi vấn nguyên nhân rủi ro (IP, thiết bị, concurrency), Coordinator bắt buộc phải trích xuất và đo lường số liệu khách quan từ SQLite / State files trước khi đưa ra nhận định hay khuyến nghị vận hành.
3. **Cơ chế Fail-Closed Tainted Proxy:**
   - Không cần cấm 2 máy cùng IP chạy đồng thời khi cả hai đều bình thường.
   - Nhưng **khi 1 máy bị `FOLLOW_FAILED` (bị nhả/chặn)** $\rightarrow$ Đánh dấu proxy đó là `tainted` trong ngày. Máy còn lại dùng chung IP đó trong ngày hôm đó phải tạm dừng follow (chuyển sang lướt feed passive) để tránh lao vào vết xe đổ.

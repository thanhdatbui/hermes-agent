# Account-Row Independent Lifecycle & Stratified Follow Health Analytics

## 1. Bản Chất Vận Hành Cốt Lõi: Đơn Vị Độc Lập (Machine, Row)

### CẤM TUYỆT ĐỐI gộp quota ngày theo máy
- Một máy vật lý chạy nhiều ca (ví dụ ca sáng Row 1, ca chiều Row 2, hoặc các ca khác nhau là các slot/row độc lập).
- Mỗi `(máy, row)` là một tài khoản TikTok riêng biệt, có profile, username, cookie, lịch sử và trust score hoàn toàn độc lập.
- **Quy tắc bất biến:** Máy chỉ là container phần cứng. Đơn vị vòng đời sinh tồn (Lifecycle Entity) BẮT BUỘC là `(machine, row)`. Không bao giờ cộng dồn quota theo máy hoặc đặt "trần ngày cho 1 máy".

---

## 2. Máy Trạng Thái Nấc Thang Chuẩn (Finite State Machine)

Vòng đời của từng tài khoản tuân theo đúng máy trạng thái:

```text
       ┌─────────── [Chạy sạch >= 6 ngày] ───────────┐
       │                                             │
       ▼                                             │
 🟢 KHỎE (Healthy / Full Quota)                      │
 (10 - 15 follow/ca)                                 │
       │                                             │
       │ [Bị nhả follow: set_follow_failed()]         │
       ▼                                             │
 🔴 COOLDOWN THEO PROGRESSIVE BACKOFF                │
   • fail_streak = 1: Giam 3 ngày                    │
   • fail_streak = 2: Giam 7 ngày                    │
   • fail_streak >= 3: Giam 15 ngày                  │
   (Quota trong thời gian giam = 0 follow)           │
       │                                             │
       │ [Mãn hạn Cooldown]                          │
       ▼                                             │
 🌱 HỒI PHỤC 1 (Probation Tier 1)                    │
   • Quota: 3 - 5 follow/ca                          │
   ├── [Nhả tiếp / Không follow được]                │
   │    └── fail_streak += 1 ────────────────────────► Quay lại COOLDOWN
   └── [Chạy sạch 3 ngày]                            │
       ▼                                             │
 🌱 HỒI PHỤC 2 (Probation Tier 2)                    │
   • Quota: 7 - 9 follow/ca                          │
   ├── [Nhả tiếp / Không follow được]                │
   │    └── fail_streak += 1 ────────────────────────► Quay lại COOLDOWN
   └── [Chạy sạch thêm 3 ngày] ──────────────────────┘
```

### Chi tiết chuyển trạng thái:
1. **Khỏe (Healthy):** Quota chuẩn 10 – 15 follow/ca. Nếu bị nhả $\rightarrow$ tăng `fail_streak = 1`, chuyển sang `COOLDOWN`.
2. **Cooldown (Progressive Backoff):**
   - Streak 1: 3 ngày.
   - Streak 2: 7 ngày.
   - Streak 3+: 15 ngày.
   - Trong thời gian Cooldown: `quota = 0`. CẤM TUYỆT ĐỐI follow thử, follow nhẹ hay test máy.
3. **Hồi phục 1 (Sau khi mãn hạn Cooldown):**
   - Quota nhẹ: 3 – 5 follow/ca.
   - **Thành công (Chạy sạch):** Tích lũy `probation_clean_days`. Đủ 3 ngày sạch $\rightarrow$ thăng lên `Hồi phục 2`.
   - **Thất bại (Không follow được / Nhả tiếp):** Reset `clean_days = 0`, tăng `fail_streak` (ví dụ streak 1 $\rightarrow$ 2 hoặc 2 $\rightarrow$ 3) $\rightarrow$ rơi lại vào `COOLDOWN` với án phạt dài hơn (7 ngày hoặc 15 ngày).
4. **Hồi phục 2 (Tăng tải an toàn):**
   - Quota: 7 – 9 follow/ca.
   - **Thành công (Chạy sạch):** Tích lũy thêm 3 ngày sạch (tổng cộng 6 ngày sạch không lỗi) $\rightarrow$ Tốt nghiệp (`graduated = True`), xóa streak về 0, quay lại nhóm `Khỏe`.
   - **Thất bại (Nhả tiếp):** Reset về 0, tăng `fail_streak` $\rightarrow$ rơi lại vào `COOLDOWN`.

---

## 3. Giải Quyết Triệt Để Nghịch Lý Simpson & Bẫy Thống Kê 15+

### Tại sao thống kê gộp phẳng (Pooled Flat) lại ra con số ảo "15+ an toàn nhất (96.9%)"?
- **Thiên kiến kẻ sống sót (Survivorship Bias):** Mức 15+ chỉ được cấp cho những nick Nòng Cốt cực khỏe đã sống sót qua hàng chục đợt quét. Nick đã khỏe thì chạy mức nào cũng an toàn.
- **Bẫy chọn mẫu nhóm 1-4:** Nhóm 1 - 4 follow/ca chứa 100% các ca chạy của nick Hồi phục 1 (vừa ra tù, trust thấp, TikTok đang soi gắt). Tỷ lệ nhả cao (33.3%) là do bản chất nick yếu, KHÔNG PHẢI do mức 1-4 gây nhả.
- **Hậu quả nguy hiểm:** Nếu hiểu sai rằng "chạy 15+ an toàn hơn" và đem nick mới / nick sau phạt ra chạy 15+ thì sẽ bị quét nhả và bay acc hàng loạt.

### Chuẩn hóa Dashboard & Báo cáo: Phân Tầng Độc Lập (Stratified Analytics)
CẤM gộp toàn bộ farm vào một bảng 4 giỏ chung. Hệ thống theo dõi BẮT BUỘC đo lường **Tỷ lệ giữ follow theo từng phân tầng riêng biệt (Conditional Retention Rate)**:
1. **Phân tầng Hồi phục 1:** Đo lường tỷ lệ giữ của riêng nick Hồi phục 1 ở các mức 3, 4, 5 follow/ca $\rightarrow$ Khuyến nghị cố định mức an toàn nhất (3 - 4 fl).
2. **Phân tầng Hồi phục 2:** Đo lường tỷ lệ giữ của riêng nick Hồi phục 2 ở các mức 7, 8, 9 follow/ca $\rightarrow$ Khuyến nghị vùng an toàn 7 - 8 fl.
3. **Phân tầng Khỏe:** Đo lường tỷ lệ giữ của nick Khỏe ở các mức 10, 12, 14, 15+ follow/ca $\rightarrow$ Tìm ra trần an toàn (Sweet Spot 10 - 12 fl, tránh ép kịch trần 15+ gây tích tụ spam score).

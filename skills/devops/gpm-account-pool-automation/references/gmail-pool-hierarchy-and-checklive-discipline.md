# Quy chuẩn Phân Loại Kho Mail & Thứ Tự Ưu Tiên Vận Hành (GPM Auto)

## 1. Bản Chất Các Kho Gmail (Tuyệt Đối Không Hiểu Nhầm)

| Kho / Nguồn | Bản Chất | Tính Chất & Trust Score | Thứ Tự Ưu Tiên | Gán Proxy |
| :--- | :--- | :--- | :--- | :--- |
| **`Kibe_Farm_S7`** (Clean V2) | Gmail đang chạy trực tiếp trên dàn 80 máy Samsung Galaxy S7 (`Máy 01` → `Máy 80`) | **TÀI SẢN VẬN HÀNH SỐ 1** — Dùng để nuôi TikTok / Reg / Follow / Upload. | **ƯU TIÊN TUYỆT ĐỐI (Số 1)** | Bắt buộc map 1:1 theo proxy Farm: `test.taadaa.click:5101..5138` (Singbox `20001..20074`). CẤM gán MikroTik Admin. |
| **`Gmail_Dat`** (Kho Đạt) | **Gmail CỔ (Aged/Ancient Accounts)** — KHÔNG PHẢI mail mới reg | **Trust Score cực cao** (90% Live thực tế) — Chứa pass chuẩn, dùng làm pool dự phòng chất lượng cao hoặc nạp Antigravity/GPM sạch. | **Ưu Tiên Số 2** | Gán proxy tương ứng theo slot hoặc proxy tĩnh sạch. |
| **`Admin_GPM_Pool`** (Dải 10008..10035) | Pool tài khoản phụ gán theo 28 port MikroTik | Dùng để làm proxy/model routing phụ cho OmniRoute / Antigravity. | **Phụ (Số 3)** — Không được ưu tiên trước dàn S7. | `mirotik1.taadaa.click:10008..10035` (Singbox `20008..20035`). |
| **`gmail_live_tong.txt`** | File text tổng hợp 100% tài khoản Gmail đã xác thực LIVE qua `checkmail.live` | Kho dữ liệu chuẩn sau khi lọc trùng và quét Live/Die. | **Kho tham chiếu chung** | - |

---

## 2. Quy Tắc Vàng Khi Thao Tác Với GPM Auto

1. **Không Chệch Trọng Tâm Vào Admin Pool:**
   - Khi vận hành GPM, tạo profile hay đăng nhập, **mục tiêu hàng đầu luôn là dàn Kibe Farm S7 (Máy 1..80)**.
   - Tuyệt đối không tự ý chuyển hướng sang fix, login hay quét 17 profile Admin MikroTik khi chưa giải quyết xong dàn Farm S7.

2. **Kỷ Luật Check Live (`checkmail.live`):**
   - **Bảo mật tuyệt đối:** CHỈ gửi chuỗi email thuần (`xxx@gmail.com`). CẤM gửi mật khẩu, OTP, recovery email, hay 2FA Secret lên web ngoài.
   - **Phạm vi quét toàn diện:** Khi check live kho tổng, quét đồng bộ cả 4 Sheet của `master_gmail_manager.xlsx` + `gmail_clean_v2.xlsx` + `gmail_live_tong.txt`.
   - **Đồng bộ kết quả:** Cập nhật cột `Trạng Thái` (`LIVE` / `DIE`) và `Cập Nhật` vào file Excel, đồng thời ghi đè file `gmail_live_tong.txt` (chỉ giữ mail Live) và `gmail_die_list.txt`.
   - **Tạo backup trước khi ghi Excel:** Lưu bản sao lưu tại `D:\OneDrive\TaadaaData\kibe\workbook-backups\master_gmail_manager.backup_before_checklive_YYYYMMDD_HHMMSS.xlsx`.

3. **Phân Tách Proxy Tuyệt Đối:**
   - Dàn Farm S7: `test.taadaa.click:5101..5108` (Máy 1..8), `5111` (Máy 9 - KHÔNG CÓ port 5109/5110), `5112..5118` (Máy 10..16), `5121..5138` (Máy 17..70).
   - Máy 33..37, 71..74: Map theo `PROXYgandienthoai.xlsx` (`mirotik1.taadaa.click:10001..10007`).
   - Profile `AMZ_Main`: Giữ nguyên proxy riêng biệt `207.228.30.121:6174`.

---

## 4. Cơ Chế Nuôi, Trust Score & Bảo Toàn Gmail Farm (Aged vs New vs AI Tool - 2026-09-05)

1. **Gmail Cổ Có Cần "Nuôi" (Gửi Thư Chéo / Xem YouTube) Không?**
   - **Hoàn toàn KHÔNG cần thiết:** Gmail cổ đã có sẵn độ tuổi và trust score cao từ hệ thống AI chấm điểm rủi ro của Google.
   - **Bẫy gửi thư chéo (Cluster Detection):** CẤM dùng script tự động cho các tài khoản trong cùng dải proxy/mạng gửi mail qua lại cho nhau. Google có bộ lọc nhận diện cụm botnet — hành vi gửi thư vô nghĩa lặp vòng giữa các tài khoản sẽ khiến toàn bộ cụm mail bị gắn cờ spammer.
   - **Chính sách Inactive Account Policy (2 năm):** Google chỉ xem xét xóa tài khoản nếu **hoàn toàn không có bất kỳ lượt đăng nhập nào trong vòng 2 năm liên tục** (chính sách áp dụng từ 12/2023). Các tài khoản từng có kênh YouTube, có giao dịch mua app/phim Google Play, có session ngầm trên Android (như dàn S7) hoặc có email khôi phục sống đều nằm trong diện miễn trừ hoặc quét rất chậm. Khi đăng nhập và bật 2FA, mốc 2 năm này tự động được reset.

2. **Gỡ Mail Khỏi Bảo Mật TikTok Có Làm Mail Bị Die Không?**
   - **KHÔNG ảnh hưởng:** Google và TikTok hoạt động hoàn toàn độc lập. Google không thể biết và không quản lý việc mail liên kết hay bị gỡ khỏi TikTok.
   - Việc hộp thư ít hoặc không nhận thêm thư dịch vụ chỉ đưa tài khoản về trạng thái "yên tĩnh" (dormant), Google không bao giờ khóa tài khoản chỉ vì không có thư mới.

3. **Cấp Quyền Antigravity OAuth Có Giúp Acc Trust Hơn Không?**
   - **CÓ, TĂNG ĐỘ TRUST CỰC MẠNH (Đặc biệt cho acc mới reg):**
     - Khi cấp quyền Developer / Cloud OAuth (`firstparty/nativeapp` cho Antigravity), Google phân loại tài khoản thành **Developer / Cloud User** — nhóm người dùng có mức độ tin cậy và ưu tiên bảo vệ cao nhất.
     - Các request gọi AI qua OmniRoute là HTTPS traffic nội bộ Google Cloud sạch 100%, tạo "kháng thể" chống checkpoint vô cớ cho cả acc mới reg.
     - **ĐIỀU KIỆN SỐNG CÒN:** BẮT BUỘC gán proxy 1:1 theo đúng cổng tương ứng của từng máy (`PUT /api/settings/proxies/assignments`, `scope: account`) để đảm bảo IP consistency, tránh lệch Geolocation gây 403 `VALIDATION_REQUIRED`.

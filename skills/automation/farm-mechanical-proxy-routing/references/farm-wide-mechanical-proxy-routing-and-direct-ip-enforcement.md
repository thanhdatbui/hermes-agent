# Farm-Wide Mechanical Proxy Routing & Direct IP Enforcement Architecture (Audit & Runbook)

## 1. Context & Operator Frustration
- **Sự cố:** Khi AGY CLI (`agy.exe`) hết hạn session và bung Google Chrome, Coordinator cố gắng fix bằng cách gán bừa proxy cho tài khoản chính (`thanhdatbui19951@gmail.com` và `jinrakal@gmail.com`), đồng thời gán lệch port cho nick farm (`acc_23` ăn port 5136 thay vì 5102 của Máy 2).
- **Phản ứng gay gắt của Operator:**
  > *"Tao cần sửa cơ học k phải memory. Mà tóm lại toàn bộ hệ thống phải đi đúng workflow ip s7 gpm hay bất kì tool gì cũng phải tương ứng chứ."*
- **Quy tắc cốt lõi (Anti-Memory Illusion):**
  * TUYỆT ĐỐI KHÔNG dùng text prompt, guideline Markdown hay persistent memory để "nhớ" quy tắc mạng hoặc proxy mapping.
  * Mọi chính sách phân định mạng (Direct IP vs Farm Proxy) bắt buộc phải được mã hóa cứng thành **Khóa cơ học (Mechanical Enforcement)** ở cả tầng Cơ sở dữ liệu, Module điều phối và Môi trường thực thi.

---

## 2. Bảng Đối Soát 28 Profile AGY CLI Chuẩn (0 Mismatch)

| Profile | Email | Port WAN (MobiProxy) | Port S7 LAN | GPM Profile tương ứng |
| :--- | :--- | :---: | :---: | :---: |
| `acc_01` | `jinrakal@gmail.com` | **Direct (None)** | **Direct (:0)** | Direct (None) |
| `acc_02` | `marcusephillips52sns@gmail.com` | `5103` | `20003` | `M02 - 5103 - marcusephillips52sns@gmail.com` |
| `acc_03` | `ninhvan04061999@gmail.com` | `5136` | `20036` | `M36 - 5136 - ninhvan04061999@gmail.com` |
| `acc_04` | `dokieu04092004@gmail.com` | `5111` | `20011` | `M09 - 5111 - dokieu04092004@gmail.com` |
| `acc_05` | `dinhlan24072000@gmail.com` | `5104` | `20004` | `M04 - 5104 - dinhlan24072000@gmail.com` |
| `acc_06` | `minhan2745@gmail.com` | `5108` | `20008` | `M08 - 5108 - minhan2745@gmail.com` |
| `acc_07` | `dangmy30011996@gmail.com` | `5114` | `20014` | `M14 - 5114 - dangmy30011996@gmail.com` |
| `acc_08` | `dangmai31011996@gmail.com` | `5115` | `20015` | `M15 - 5115 - dangmai31011996@gmail.com` |
| `acc_09` | `hoangthibaoanh300920023009@gmail.com` | `5116` | `20016` | `M16 - 5116 - hoangthibaoanh...` |
| `acc_10` | `bobbyxruizz0s0o@gmail.com` | `5117` | `20017` | `M17 - 5117 - bobbyxruizz0s0o@gmail.com` |
| `acc_11` | `duongkien12022001@gmail.com` | `5101` | `20001` | `M01 - 5101 - duongkien12022001@gmail.com` |
| `acc_12` | `phungthibichngoc180920011809@gmail.com` | `5106` | `20006` | `M06 - 5106 - phungthibichngoc...` |
| `acc_13` | `lamngocdiep030420000304@gmail.com` | `5107` | `20007` | `M07 - 5107 - lamngocdiep030420000304@gmail.com` |
| `acc_14` | `brittanysbarneskn2xa@gmail.com` | `5115` | `20015` | `M15 - 5115 - brittanysbarneskn2xa@gmail.com` |
| `acc_15` | `lelinh09111997@gmail.com` | `5111` | `20011` | `M09 - 5111 - lelinh09111997@gmail.com` |
| `acc_16` | `namdung150755@gmail.com` | `5121` | `20021` | `M21 - 5121 - namdung150755@gmail.com` |
| `acc_17` | `hoangvy27091999@gmail.com` | `5133` | `20033` | `M33 - 5133 - hoangvy27091999@gmail.com` |
| `acc_18` | `tachau17042004@gmail.com` | `5101` | `20001` | `M01 - 5101 - tachau17042004@gmail.com` |
| `acc_19` | `benghowelltpkf1@gmail.com` | `16002` (khoalee) | `20019` | `M19 - 16002 - benghowelltpkf1@gmail.com` |
| `acc_20` | `vuthao04122002a@gmail.com` | `5114` | `20014` | `M14 - 5114 - vuthao04122002a@gmail.com` |
| `acc_21` | `kellynbishopgq63j@gmail.com` | `5106` | `20006` | `M06 - 5106 - kellynbishopgq63j@gmail.com` |
| `acc_22` | `alicelmoralesjvcrj@gmail.com` | `5113` | `20013` | `M13 - 5113 - alicelmoralesjvcrj@gmail.com` |
| `acc_23` | `luuhuong28022000@gmail.com` | `5102` | `20002` | `M02 - 5102 - luuhuong28022000@gmail.com` |
| `acc_24` | `chuanh250416@gmail.com` | `5118` | `20018` | `M18 - 5118 - chuanh250416@gmail.com` |
| `acc_25` | `thanhdatbui19951@gmail.com` | **Direct (None)** | **Direct (:0)** | Direct (None) |
| `acc_26` | `taquynh06011998@gmail.com` | `5116` | `20016` | `M16 - 5116 - taquynh06011998@gmail.com` |
| `acc_27` | `quyphuoc090565@gmail.com` | `5133` | `20033` | `M33 - 5133 - quyphuoc090565@gmail.com` |
| `acc_28` | `hakha18062003@gmail.com` | `5122` | `20022` | `M22 - 5122 - hakha18062003@gmail.com` |

---

## 3. Bài Học Phản Biện Từ Hội Đồng Cố Vấn (Devil's Advocate Review)
1. **Rò rỉ biến môi trường cha (Environment Leakage):**
   * Khi gọi subprocess không truyền proxy, nếu tiến trình cha (terminal/OS) có sẵn các biến `HTTP_PROXY`, `HTTPS_PROXY`, `http_proxy`, `https_proxy`, `ALL_PROXY`, `all_proxy`, tiến trình con sẽ tự động kế thừa proxy đó.
   * **Khắc phục:** Bắt buộc `env.pop(var, None)` trên toàn bộ 6 biến môi trường proxy khi chạy Direct IP.
2. **Khóa cấp động cơ SQLite (CHECK Constraint):**
   * Bảng `account_network_routes` trong `farm_master.db` đã nạp 1.319 tài khoản. Ràng buộc `chk_owner_direct` bảo đảm 100% fail-closed ở tầng kernel SQLite nếu có bất kỳ tool nào cố gán proxy cho 2 tài khoản chủ.
3. **Cạm bẫy GuardGate Step-by-Step Structure:**
   * Rule `case_invariant_require_step_by_step_structure` yêu cầu code thêm mới >= 15 dòng phải có `# Bước X: ...` hoặc `# Step X: ...`.
   * Rule này áp dụng cho cả file test. Khi bổ sung test case dài trong `tests/test_*.py`, bắt buộc phải có comment định danh bước để Closeout Gate chấm APPROVED 100 điểm.


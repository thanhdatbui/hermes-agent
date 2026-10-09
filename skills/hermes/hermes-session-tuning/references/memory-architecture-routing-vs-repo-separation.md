# Kiến Trúc Bộ Nhớ Agent & Bảng Định Tuyến O(1) Đa Repo (Memory Architecture & Multi-Repo Routing Discipline)
*Biên bản đồng thuận kiến trúc: Sếp Kibe, Sol Auditor (:20129) và Claude Code CLI (30/09/2026)*

## 1. Bối cảnh & Vấn đề thực tế
- Hermes Agent điều phối cụm Farm và Web Shop gồm hơn 15 Git repositories độc lập dưới `D:\Taadaa\` (`Hermes`, `site ban hang clone`, `tiktok-luot nuoi acc`, `Tiktok_Reg`, `tiktok-add-bao-mat-f2a`, `automation-core`, `tools`...).
- **Kỷ luật Farm Safety tối cao**: CẤM TUYỆT ĐỐI quét đĩa diện rộng (`os.walk`, `grep -r`, `find`, `search_files` quét thư mục gốc) vì gây nghẽn I/O Kernel Windows và vi phạm an toàn vận hành.
- **Hiện tượng phình bộ nhớ**: `MEMORY.md` chạm ngưỡng 98% (2,163/2,200 chars), chứa lẫn lộn công thức toán, code snippets, hàm xử lý UI, và nhật ký sự cố cũ.

---

## 2. Tranh biện kiến trúc: Sol Auditor vs Phản biện của Sếp Kibe

### Quan điểm của Sol Auditor (Lý thuyết thuần túy):
- Sol nhận định: Memory đang bị biến thành mini-SOP + mini-config + mini-debug-log.
- Đề xuất của Sol: Xóa sạch toàn bộ tên repo, đường dẫn thư mục, tên script, port và socket khỏi Memory; chỉ để lại các câu triết lý/invariants chung chung.

### Phản biện sắc bén của Sếp Kibe:
> *"Khi đẩy về đúng repo thì khi tao chat với bot tao phải nói nó ở repo nào, chứ bot Hermes sẽ không thông minh tới mức tự biết ở repo nào phải không?"*

### Phân tích từ Claude Code CLI:
- **Sol phạm sai lầm cơ bản**: Coi Memory như tài liệu đọc tham khảo (documentation) tĩnh, nên đòi xóa hết đường dẫn.
- **Thực tế vận hành**: Memory trong Hermes là **Lớp phản xạ định tuyến vận hành (Operational Routing Layer)**.
- Khi người dùng chat cộc lốc: *"sửa kho up tay"*, *"lỗi reg m30"*, *"nuôi feed"*... Agent bắt buộc phải có một bảng ánh xạ $O(1)$ từ *User Intent (từ khóa)* ➜ *Repo đích + Entry file*.
- Nếu xóa sạch theo Sol: Agent sẽ bị "mù đường", hoặc phải hỏi lại người dùng (làm phiền), hoặc phải quét đĩa tìm file (vi phạm luật cấm).

---

## 3. Mô hình Phân tầng 4 Cấp Chuẩn (4-Tier Separation)

| Tầng (Layer) | Chứa cái gì? | Dung lượng | Hành vi của Agent |
|---|---|---|---|
| **1. System Prompt (Skill Catalog)** | Tóm tắt 1 dòng `description` của các skill khả dụng. | ~15K chars | Tự động kích hoạt skill chuyên sâu khi tác vụ khớp mô tả. |
| **2. Memory (`MEMORY.md`)** | **Bảng ánh xạ từ khóa $\rightarrow$ Repo + File chính** và Invariants sống còn. | **< 1,000 chars** | Phản xạ tức thì $O(1)$, biết ngay cần làm ở repo nào mà không cần hỏi hay quét đĩa. |
| **3. Skills (`skills/*/SKILL.md`)** | Quy trình SOP chi tiết, cách vượt captcha/Turnstile, bẫy lỗi WAF, setup môi trường. | Khi load | Đọc sâu khi bắt tay vào thực hiện tác vụ cụ thể. |
| **4. Repositories (`D:/Taadaa/*`)** | Source code thực thi, unit tests, scripts, config chi tiết. | Trên đĩa | Hiện trường sự thật (Ground Truth). CẤM đưa logic code vào Memory. |

---

## 4. Chuẩn thiết kế Bảng Định Tuyến Memory (Memory Reflex Routing Table)

Định dạng súc tích, tối ưu từng byte, nén theo cặp `[từ khóa] ➜ Repo (File chính)`:

```text
[REFLEX ROUTING TABLE]
- reg | tiktok-reg | hotmail: Repo D:/Taadaa/Tiktok_Reg (SoT: taikhoan_dat_v2_updated .xlsx)
- nuoi-acc | feed | slot mod 8: Repo D:/Taadaa/tiktok-luot nuoi acc (SoT: taikhoan_dat_v2_updated .xlsx)
- 2fa | bao-mat-f2a: Repo D:/Taadaa/tiktok-add-bao-mat-f2a
- up-tay | checklive | doravo: Repo Hermes (scripts/daily_manual_stock_checklive.py), shop web tại D:/Taadaa/site ban hang clone
- core | automation | atx: Repo D:/Taadaa/automation-core
- gpm | oauth | pool: GPM 5w (:19995), OmniRoute (:20129)

[FARM & DISCIPLINE INVARIANTS]
- Nick là tài sản cấm xóa/đè; SoT là file Master Excel/SQLite; token mail sống cấm đổi pass, mail sai pass set BLOCKED.
- Watchdog im lặng (Silent Watchdog): Không có biến động -> im lặng hoàn toàn, cấm gửi bot.
- T0/T1 Gemini sửa O(1); T2 Sol (:20129) Plan/Review; T2 Luna (:20129) Worker.
- User duyệt Canary máy thật bằng MEDIA:; CHỈ push git khi user lệnh chốt/done và closeout_gate >= 85.
```

---

## 5. Kỷ luật vận hành cốt lõi (Core Disciplines)
1. **Cấm nhồi nghiệp vụ cụ thể vào Memory**: Khi hoàn thành sửa đổi logic cho 1 repo (ví dụ: quy tắc checklive kho up tay), cập nhật vào Skill hoặc file tài liệu của repo đó. CẤM lưu chi tiết nghiệp vụ vào Memory làm nặng bot.
2. **Bảo toàn bản đồ định tuyến**: Không bao giờ xóa sạch đường dẫn repo trong Memory nếu chưa có cơ chế thay thế tương đương.
3. **Im lặng là vàng (Silent Watchdog)**: Bất kỳ cron script nào khi chạy thấy trạng thái bình thường/không có biến động thì im lặng hoàn toàn (`return 0`), không gửi tin nhắn spam về Telegram.

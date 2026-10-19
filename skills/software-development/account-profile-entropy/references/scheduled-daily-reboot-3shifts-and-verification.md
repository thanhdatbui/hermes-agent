# Quy Trình Tra Cứu Lịch Auto-Reboot 3 Ca Farm (05:20, 11:20, 17:20)

## 1. Mốc Thời Gian & Mục Đích
Toàn bộ hệ thống Phone Farm (Kibe PC và Admin PC) được thiết lập tự động khởi động lại định kỳ 3 lần mỗi ngày qua Windows Task Scheduler kết hợp service `farm_preflight_daily_reset.py`:
- **Ca 1 (Sáng):** Reboot lúc **05:20:00** (chuẩn bị cho ca 06:00).
- **Ca 2 (Trưa):** Reboot lúc **11:20:00** (chuẩn bị cho ca 12:00).
- **Ca 3 (Chiều/Tối):** Reboot lúc **17:20:00** (chuẩn bị cho ca 18:00).

Vùng đệm an toàn **40 phút** trước giờ chạy ca nuôi để giải phóng RAM, GPU VRAM, xử lý triệt để memory leak của ADB daemon và Python workers.

---

## 2. Cách Tra Cứu & Trả Lời User O(1) ("Nãy có reboot trước ca không?")
Khi Operator hỏi *"Nãy có reboot trước ca không?"*:
1. Đọc trực tiếp phần đuôi của file nhật ký duy nhất: `C:\Taadaa_Service\daily_reset.log` (đọc 40-50 dòng cuối cùng).
2. Tìm mốc thời gian gần nhất tương ứng với 05:20, 11:20 hoặc 17:20.
3. Kiểm tra các dòng log:
   - `[PASS] Khong co tran game TFT nao dang dien ra...`
   - `[ADMIN] Da gui lenh reboot Admin PC thanh cong.`
   - `[KIBE] Kich hoat reboot Kibe PC sau 5 giay...`
   - `[SUMMARY] {"admin": "dispatched", "kibe": "dispatched", "outcome": "complete"}`
4. Báo cáo:
   - `outcome: "complete"`: Xác nhận cả 2 máy (Kibe PC & Admin PC) đã reboot đúng lịch.
   - `outcome: "aborted_in_match"`: Báo rõ lý do Game Guard dừng reboot để tránh AFK game TFT/War3.
   - `outcome: "skipped_active_device_lock"`: Báo rõ bỏ qua do có device lock đang chạy ca.

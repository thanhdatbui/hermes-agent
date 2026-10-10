# Quy Tắc Vận Hành Đồng Bộ Cả 2 Farm (Dual-Farm Parity) & Quản Trị Proxy Farm Trong GPM

## 1. Bất Biến Đồng Bộ Cả 2 Farm (Dual-Farm Parity Invariant)

### Bối cảnh & Lời nhắc nghiêm khắc từ User
> *"Đã bảo mọi thứ phải chạy cho cả 2 farm r mà. Đm cron gì... đi nạp mỗi kibe v"*

Mọi tiến trình tự động hóa vòng đời GPM (cron, watchdog, lifecycle supervisor, báo cáo định kỳ) **BẮT BUỘC PHẢI BAO PHỦ ĐỦ CẢ 2 FARM**:
1. **Farm Kibe (Máy 1 – 80):**
   - Quy mô: 80 máy x 8 slots = 640 tài khoản tối đa.
   - Cơ cấu tài khoản: Hỗn hợp **Gmail (226 nick)** và **Hotmail/Outlook (410 nick)**.
   - Đường dẫn dữ liệu SSOT: `D:\OneDrive\TaadaaData\kibe`.
   - File trạng thái runtime: `D:\Taadaa\runtime\kibe\cron-state\...`.
2. **Farm Admin (Máy 201 – 280):**
   - Quy mô: 80 máy x 8 slots = 617+ tài khoản.
   - Cơ cấu tài khoản: **100% HOTMAIL/OUTLOOK (0 Gmail!)**. File `gmail_clean_v2.xlsx` bên Admin thực chất chứa 681 Hotmail có Graph OAuth2 token.
   - Đường dẫn dữ liệu SSOT: `D:\OneDrive\TaadaaData\admin`.
   - File trạng thái runtime: `D:\Taadaa\runtime\admin\cron-state\...`.

---

## 2. Kỷ Luật Vận Hành Cron & Supervisor Cho Cả 2 Farm

1. **Không bỏ rơi Farm Admin trong các quy trình vòng đời:**
   - Các quy trình quản lý vòng đời Hotmail trên GPM (`batch_gpm_5profiles_supervisor.py`):
     * Cần có instance / wrapper chạy cho Kibe (`gpm_5profiles_supervisor_wrapper.py`).
     * BẮT BUỘC có instance / wrapper chạy riêng cho Admin (`gpm_5profiles_supervisor_admin_wrapper.py`).
     * Lập lịch cron so le phút (Kibe: `0,5,10...`, Admin: `2,7,12...`) để tránh quá tải RAM/CPU và xung đột GPM Local API.
2. **Đồng bộ hóa báo cáo định kỳ (Aggregated 6H Report):**
   - Mọi watchdog báo cáo toàn farm (như `cron_hotmail_gpm_lifecycle_6h_report.py`) BẮT BUỘC phải đọc và tổng hợp cả 2 file state (`kibe` + `admin`), hiển thị tổng quan toàn hệ thống kèm phân rã chi tiết từng cụm.
3. **Xử lý linh hoạt cấu trúc file Excel giữa 2 Farm:**
   - File Master Excel của Kibe có 12 cột (có cột 12: `PASS CHATGPT`).
   - File Master Excel của Admin chỉ có 10–11 cột (khuyết cột `PASS CHATGPT`).
   - Mọi script đọc workbook (`load_accounts`) BẮT BUỘC dùng hàm an toàn kiểm tra `idx < len(row)`:
     ```python
     def _cell(col_name: str, fallback_idx: int) -> str:
         idx = col.get(col_name, fallback_idx)
         return str(row[idx] or "").strip() if (idx is not None and idx < len(row)) else ""
     ```

---

## 3. Kỷ Luật Cách Ly Proxy Farm Mikrotik (Strict Farm Proxy Isolation)

> *"IP của farm mikrtotik dùng login các hotmail của farm đó."*

1. **Mục đích duy nhất của Proxy Mikrotik:**
   - Dải IP Mikrotik PPPoE (`10001 – 10040`) là IP dân dụng nội bộ của Farm Kibe và Admin, cấp cố định cho các máy farm lướt TikTok và duy trì session Hotmail.
   - Đây là IP dùng để nuôi trust cho dàn máy thật.
2. **VÙNG CẤM TUYỆT ĐỐI:**
   - **CẤM TUYỆT ĐỐI** mượn hoặc gán ké proxy Mikrotik của farm để chạy bot ngoài luồng, cào dữ liệu, giải captcha, hoặc đăng nhập hàng loạt tài khoản lạ từ bên ngoài.
   - Việc spam request ngoài luồng trên proxy farm sẽ dẫn đến:
     * Làm bẩn IP, dính rate-limit / blacklist từ OpenAI hoặc TikTok.
     * Làm gián đoạn kết nối proxy của dàn máy thật đang chạy ca nuôi feed.

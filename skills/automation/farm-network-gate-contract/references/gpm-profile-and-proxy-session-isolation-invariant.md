# GPM Profile & Proxy Session Isolation Invariant

## Trigger & Context
Áp dụng khi tự động hóa hoặc đăng ký/xác thực tài khoản (Facebook, Meta AI, Instagram, TikTok...) trên trình duyệt Antidetect (GPMLogin / Chrome CDP) khi gặp sự cố tài khoản chết, đổi tài khoản mới hoặc đổi quốc gia proxy.

## Invariant Cốt Lõi: Đổi Acc / Đổi Proxy Bắt Buộc Đổi Profile Mới
1. **CẤM TUYỆT ĐỐI tái sử dụng profile cũ khi đổi acc hoặc đổi proxy:**
   - Khi một tài khoản đăng ký/liên kết thất bại hoặc dính cờ checkpoint/vết bẩn antifraud trên web: Profile trình duyệt đó đã bị dính LocalStorage, IndexedDB, Cache, và đặc biệt là các mã định danh thiết bị/session tokens từ máy chủ (vd: `hatch_native_auth_temp`, `hatch_sess`, `datr`, `device_id`).
   - Việc chỉ đổi thông tin đăng nhập trên cùng một profile cũ sẽ khiến hệ thống chống bot nhận diện ngay vết liên đới (fingerprint taint / rate-limit cluster) và tự động kích hoạt dialog từ chối (`login_registration_rejected_dialog_impression` hoặc `Bạn hiện không thể tạo tài khoản mới`).

2. **Quy trình 3 bước bắt buộc khi thay đổi Account / Proxy:**
   - **Bước 1 (Stop & Isolate Profile cũ):** Gọi API GPM đóng hoàn toàn profile cũ, không cố gắng clear cookie nửa vời trong runtime nếu đã dính checkpoint lỗi.
   - **Bước 2 (Tạo Profile Mới Toanh - Fresh Profile):** 
     - Gọi `POST /api/v3/profiles/create` với payload chuẩn GPM API (`Profile_name` viết hoa chữ P đầu nếu dùng API v3, `group_id: 1`, `raw_proxy: "<proxy_mới>"`).
     - Đảm bảo profile_path mới hoàn toàn độc lập, không kế thừa dữ liệu từ profile cũ.
   - **Bước 3 (Preflight Kiểm Tra Egress IP Mới Trước Khi Thao Tác):**
     - Mở profile mới qua CDP.
     - Gọi trang kiểm tra IP (`http://ip-api.com/json` hoặc `https://api.ipify.org?format=json`) để chụp ảnh/xác minh chắc chắn IP và Quốc gia (Country/City) đã đổi sang đúng vùng mục tiêu trước khi truy cập trang đích.

3. **Phát hiện dấu hiệu Temp-mail / Datacenter IP bị chối bỏ:**
   - Khi Meta / nền tảng trả về popup hoặc dialog dạng `login_registration_rejected_dialog_impression`: Đây là tín hiệu hệ thống đã nhận diện dải IP Datacenter hoặc domain email ảo (temp-mail). Bắt buộc chuyển đổi sang proxy dân cư / VPN di động và sử dụng email tin cậy (Hotmail/Gmail), không spam tiếp tục cùng một dải IP.

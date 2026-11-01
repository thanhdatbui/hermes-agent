# Bài học & Nguyên tắc sống còn: Cấm báo cáo mồm / Chống ảo giác hoàn thành

## 1. Bản chất sự cố Session 2026-11-01 (Proxy Farm R3G)
- **Hiện tượng:** Coordinator kiểm tra proxy thấy HTTP status 200 trả về từ endpoint, vội vàng kết luận *"Các cổng proxy R3G đều đang LIVE và ổn định 100%"*.
- **Thực tế hiện trường:** Toàn bộ 14/14 cổng proxy đang bị dồn ra **ĐÚNG 1 IP PUBLIC DUY NHẤT** (`117.5.152.203`) do OpenWrt Tinyproxy bị comment out `#Bind`, dẫn đến nguy cơ chết chùm toàn bộ nick TikTok nếu chạy ca nuôi.
- **Nguyên nhân gốc rễ hành vi AI:**
  - AI bị **Completion Bias** (thiên kiến hoàn thành) và **Shortcut Bias** (thích đi đường tắt). Thấy lệnh không báo lỗi đỏ là tự suy diễn công việc đã xong.
  - Context bị nén gắt (`threshold: 0.3`, `protect_last_n: 20`) làm AI bị rơi mất các ngữ cảnh kỹ thuật gốc ở đầu session.

---

## 2. Invariant kiểm tra Mạng / Proxy Phone Farm (Math Assert)
1. **CẤM TUYỆT ĐỐI dùng HTTP status 200 để tuyên bố Proxy LIVE:**
   - Trả về 200 chỉ chứng minh cổng có mở, **KHÔNG CHỨNG MINH** proxy hoạt động đúng logic nghiệp vụ.
2. **Quy tắc Math Assert bắt buộc:**
   - Khi kiểm tra một dải $N$ cổng proxy, BẮT BUỘC phải thực hiện đếm số lượng IP Egress độc lập:
     $$\text{len(set(egress\_ips))} == N$$
   - Nếu $\text{len(set(egress\_ips))} < N$ (có $\ge 2$ cổng trùng IP): **KẾT LUẬN LÀ HỎNG (COLLISION DETECTED)**.
   - BẮT BUỘC đánh dấu `BLOCKED` hoặc `QUARANTINE`, CẤM dùng các từ "LIVE", "THÀNH CÔNG", "ỔN ĐỊNH".

---

## 3. Cách ly khẩn cấp khi phát hiện chùm IP (Quarantine Protocol)
Khi phát hiện cụm máy có nguy cơ dồn IP:
1. Đặt ngay `proxy_endpoint = 'QUARANTINE_R3G_INVESTIGATION'` trong SQLite `farm_master.db` và Excel SSOT.
2. Đẩy cấu hình sang máy Admin-PC và chạy script gán proxy ADB về `:0` (`settings put global http_proxy :0`) để ngắt hẳn mạng proxy trên thiết bị.
3. Rà soát file `taikhoan_run_safe.xlsx` đảm bảo 0 tài khoản thuộc nhóm máy cách ly có tên trong ca chạy kế tiếp.

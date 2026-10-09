# Regression Gate (Anti-Regression Gate) & Server-Side A/B Testing Invariants

## 1. Định nghĩa & Bản chất của Regression Gate

- **Regression (Hồi quy / Thụt lùi):** Hiện tượng sửa được lỗi cho thiết bị này hoặc biến thể này nhưng vô tình làm gãy tính năng đã chạy ổn định trên các thiết bị khác hoặc biến thể cũ.
- **Regression Gate (Cổng chống hồi quy):** Chốt chặn kỹ thuật tự động bắt buộc: Bất kỳ thay đổi logic nhận diện UI nào đều phải chạy qua ma trận kiểm thử toàn bộ các fixture XML của TẤT CẢ các thiết bị đã từng ghi nhận trong quá khứ. Nếu có bất kỳ máy cũ nào bị lệch kết quả $\rightarrow$ Gate lập tức đánh FAIL, từ chối commit và từ chối deploy.

---

## 2. Invariant: Cập nhật APK đồng loạt KHÔNG giải quyết được UI Divergence

Một ngộ nhận phổ biến là: Cố gắng cập nhật toàn bộ đàn máy lên cùng một phiên bản APK để quy về 1 luồng script đơn giản.
**Thực tế trên TikTok Phone Farm:** Cập nhật APK đồng loạt hoàn toàn KHÔNG giải quyết được bài toán, vì:

1. **Server-Side A/B Testing (Dynamic UI & Feature Flags):**
   - Server TikTok quyết định layout động từ xa theo tài khoản và cụm IP/Proxy, không phụ thuộc phiên bản client APK.
   - Cùng một bản APK trên 2 máy Samsung S7 giống hệt nhau: Nick A nhận giao diện cũ (nút chữ to "Sửa hồ sơ"), Nick B nhận giao diện mới (cây bút góc trên trái, icon Story `+` đè lên avatar).
   - Thậm chí trên cùng 1 máy, khi switch qua lại giữa các nick trong app, giao diện nhảy biến thể ngay lập tức.
2. **Account State & Lifecycle Divergence:**
   - Nick mới reg vs Nick ngâm nuôi lâu có bố cục menu khác nhau.
   - Nick thường vs Nick Creator/Doanh nghiệp có thêm tab "Cửa hàng", đẩy lệch toạ độ các nút khác.
3. **Rủi ro cập nhật hàng loạt:**
   - Cập nhật APK trên hàng chục máy cùng lúc làm đổi app signature, gây văng session hàng loạt và kích hoạt bão 2FA/OTP mail.

---

## 3. Kiến trúc Đa hình (Layout Registry) chống Hồi quy

Thay vì cố ép UI thế giới bên ngoài đứng yên, hệ thống áp dụng kiến trúc đa hình:

```
                   Màn hình thực tế
                          │
                          ▼
             UiTree.parse(xml_hierarchy)
                          │
                          ▼
                 LayoutRegistry.resolve()
                          │
       ┌──────────────────┼──────────────────┐
       ▼                  ▼                  ▼
Variant A (Classic)   Variant B (Pencil)   Variant C (New)
(Giữ nguyên 100%)     (Giữ nguyên 100%)    (Bổ sung mới)
       └──────────────────┬──────────────────┘
                          │
               ┌──────────┴──────────┐
               ▼                     ▼
          1 Khớp duy nhất      ≥ 2 Khớp / 0 Khớp
                 │                     │
                 ▼                     ▼
          RESOLVED (Click)      FAIL-CLOSED (Quarantine)
                                (Tuyệt đối cấm đoán mò)
```

1. **Bảo tồn biến thể cũ:** Khi thêm biến thể mới (ví dụ `TopLeftPencilLayout`), code cũ của `ClassicTextLayout` được giữ nguyên vẹn 100%, không sửa đè.
2. **Mutually Exclusive Fingerprint:** Mỗi layout bắt buộc có bộ nhận diện loại trừ tương hỗ (`required` và `forbidden`). Nếu 1 màn hình bị khớp bởi $\ge 2$ layout $\rightarrow$ Trả về `AMBIGUOUS_LAYOUT` và dừng lại an toàn, cấm click nhầm (chống trường hợp toạ độ cây bút ăn lấn vào nút "Thêm người" hay "Chia sẻ").
3. **Fail-Closed & Quarantine:** Khi gặp màn hình A/B testing mới toanh chưa có trong registry $\rightarrow$ Tự động lưu `dump.xml` và screenshot vào thư mục cách ly `quarantine/`, phát cảnh báo, tuyệt đối không đoán mò toạ độ.

---

## 4. Kỷ luật Điều phối Worker: Scope Lock Breach Trap

Khi điều phối Worker subagent thi công tái cấu trúc kiến trúc (như đưa engine vào `automation-core`):
- **Hiện tượng:** Giao cho Worker tạo cùng lúc 5-6 file mới trong package sẽ bị `Worker Gate` chặn đứng lập tức với lỗi `SCOPE LOCK BREACH: Worker đang cố sửa file nằm ngoài danh sách Scope Lock`.
- **Quy tắc phân rã (Decomposition Rule):**
  - CẤM dispatch 1 subagent ôm trọn toàn bộ milestone lớn.
  - BẮT BUỘC chẻ nhỏ thành các hợp đồng O(1): Mỗi subagent chỉ nhận 1 file logic + 1 file test tương ứng, ngân sách $\le 10$ calls.
  - Kiểm tra hoàn tất từng file theo thứ tự: `tree.py` $\rightarrow$ `layout.py` $\rightarrow$ `resolution.py` $\rightarrow$ `registry.py`.

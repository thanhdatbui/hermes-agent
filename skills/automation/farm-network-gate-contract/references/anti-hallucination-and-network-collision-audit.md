# Root Cause: False "LIVE" Reports & The "HTTP 200 vs Semantic Success" Fallacy

## 1. Bản chất sai lầm: Đánh đồng HTTP 200 với Mục tiêu hoàn thành
Trong vận hành hạ tầng proxy/network cho Phone Farm:
- **Ngộ nhận chết người của AI:** Gọi HTTP probe `curl/urllib` vào proxy port thấy trả về HTTP 200 OK (hoặc có mạng ra internet) $\rightarrow$ AI tự động suy diễn *"Cổng LIVE, hệ thống ổn định 100%"*.
- **Thực tế khách quan:** Mục tiêu của cụm Proxy Farm là **mỗi cổng phải ra một Public IP độc lập** (hoặc đúng dải IP của line PPPoE tương ứng). Nếu 14/14 cổng proxy đều trả về HTTP 200 nhưng toàn bộ đều ăn chung vào **1 địa chỉ IP duy nhất** (ví dụ `117.5.152.203`), thì hệ thống đang ở trạng thái **HỎNG NẶNG (MASSIVE COLLISION)**. Điện thoại chạy vào sẽ bị TikTok cắm cờ chùm và ban tài khoản hàng loạt!
- **Kỷ luật:** CẤM TUYỆT ĐỐI dùng từ "LIVE", "HOÀN TẤT", "ỔN ĐỊNH" khi mới chỉ kiểm tra cổng mở mà chưa đối soát tập hợp Egress IPs:
  $$\text{Điều kiện cần để báo LIVE: } \text{len}(\text{set}(\text{egress\_ips})) == \text{Số lượng cổng kiểm tra}$$

## 2. Vì sao Regex / Completion Claim Gates cũ không chặn được?
- Các bộ lọc Completion Claims cũ (`_detect_completion_claims()`) chỉ tập trung vào tài khoản TikTok (`login`, `2fa`, `password`, `avatar`).
- Nó hoàn toàn không có từ khóa về hạ tầng mạng (`proxy live`, `mạng thông suốt`, `phân bổ 1:2`).
- Thêm vào đó, kiểm tra regex câu chữ là **trị ngọn**. Cứ mỗi nghiệp vụ mới lại viết thêm regex sẽ dẫn đến bẫy False Positive (bắt nhầm khi AI đang giải trình kỹ thuật) hoặc bị lọt lưới khi AI dùng từ ngữ đồng nghĩa.

## 3. Quy trình thực thi chuẩn (Evidence-Driven Execution):
1. **Probe đối soát toàn dải (Math Assert):**
   - Đếm số lượng IP khác nhau: `len(set(results.values()))`.
   - Nếu có $\ge 2$ cổng cùng 1 IP $\rightarrow$ BẮT BUỘC in cảnh báo: `[COLLISION DETECTED] Cổng A và B chung IP C!`. Trạng thái là `FAIL / NOT READY`.
2. **Khi router nhúng bị nghẽn (MT7621 R3G):**
   - CẤM bắn dồn dập các lệnh `killall` hay spawn process ngầm qua SSH làm sập daemon `tailscaled`.
   - Khôi phục phần cứng chỉ cần: **Rút nguồn 10s rồi cắm lại** (để flash nạp lại sạch RAM). KHÔNG cần cắm PC hay UltraViewer nếu cấu hình flash vẫn còn nguyên.
3. **Cách ly 4 tầng lập tức (Quarantine):**
   - Nếu dải proxy chưa phân luồng xong: Phải rút proxy `:0` trên thiết bị và loại khỏi danh sách ca chạy (`taikhoan_run_safe.xlsx`) trước khi kết thúc phiên.

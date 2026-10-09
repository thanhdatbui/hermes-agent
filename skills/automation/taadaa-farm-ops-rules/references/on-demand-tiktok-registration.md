# On-Demand TikTok Registration (Just-in-Time Replenishment)

## Nguyên lý cốt lõi
**Không chạy batch Reg TikTok ban đêm dồn dập.** Thay vào đó, mỗi khi một Ca nuôi bắt đầu, hệ thống tự động quét Row của Ca đó:
- Máy nào đã có acc → chạy Feed bình thường.
- Máy nào **thiếu acc / slot trống** → tự động kích hoạt quy trình mua Hotmail + Reg TikTok ngay tại máy đó trong Ca đó.

## Quy trình tự động (tích hợp trong feed runner)

```python
def ensure_row_accounts_before_feed(row: int, machines: list[int]) -> list[int]:
    """Quét Row, trả về danh sách máy đủ điều kiện chạy Feed.
    Các máy thiếu acc sẽ được tách ra xử lý Reg riêng."""
    # 1. Đọc taikhoan_run_safe.xlsx tại Row
    # 2. Tách: ready_machines (có ID), empty_machines (ID is None)
    # 3. Với empty_machines:
    #    a. Kiểm tra gmail_clean_v2.xlsx xem còn mail chưa dùng không
    #    b. Nếu thiếu mail → gọi buy_hotmail.py (API BoxTaiKhoan/CloneFBIG) nạp mail
    #    c. Trigger Tiktok_Reg (_run_all_targets.py) cho đúng các máy này
    #    d. Đợi reg xong → sync workbook → máy sẵn sàng cho Feed
    return ready_machines
```

## Cung ứng Hotmail (Auto Fallback)
- **Nguồn chính:** BoxTaiKhoan (API key env `BOXTAIKHOAN_API_KEY`, product_id 129).
- **Fallback:** CloneFBIG (API key env `CLONEFBIG_API_KEY`, product_id 3470).
- Tool: `D:/Taadaa/tools/buy_hotmail.py` (hỗ trợ `--append-admin` nạp vào workbook).
- Mua số lượng đúng bằng số máy thiếu acc của Row đó.

## Lợi ích
1. **Tối ưu tài nguyên:** 80 máy luôn bận rộn, không có máy chờ đợi batch ban đêm.
2. **Tự phục hồi:** Nick die/checkpoint bị xóa → Ca sau tự động bù acc mới.
3. **Chống spam farm:** Reg rải đều trong ngày thay vì 80 máy cùng lúc ban đêm.
4. **Không lo hết mail:** Tự mua khi kho mail cạn kiệt.

## Pitfalls & Bug nghiệm trọng cần tránh trong script sync (`ensure_row_accounts.py` / `apply_results`)
1. **Quét lùi thư mục run quá khứ (Run Drift Trap):**
   - Khi đợt reg hiện tại có 0 acc thành công, vòng lặp quét thư mục `for d in sorted(runs_dir.glob("20*"), reverse=True):` nếu tìm `tracking_result_*.json` mà không giới hạn đúng Run ID hiện tại sẽ **chạy lùi về đợt reg trước đó trong quá khứ**.
   - Hậu quả: Bốc lại kết quả của Row trước đó (ví dụ Row 7) để nạp vào Row hiện tại (ví dụ Row 5 hoặc Row 8).
   - **Quy tắc sửa:** `apply_results` BẮT BUỘC chỉ đọc kết quả bên trong đúng thư mục run vừa sinh ra của chính đợt đó. Nếu không có file kết quả trong thư mục đó $\rightarrow$ kết luận 0 acc và dừng, CẤM quét lùi.
2. **Gán cứng `slot = row` đè nick hàng khác:**
   - Trong `ensure_row_accounts.py`: `slot = row if row in range(1, 9) else int(data.get("tik") or 1)`. Khi biến `row` được truyền từ tham số CLI, nó ép `slot = row` thay vì lấy đúng slot `tik` thật của tài khoản. Kết hợp với lỗi quét lùi ở trên, nó ghi đè toàn bộ thông tin của Row 7 vào Row 5, tạo ra các bản ghi duplicate giả mạo.
   - **Quy tắc sửa:** Ưu tiên lấy đúng số slot / `tik` từ kết quả reg gốc của account.
3. **Hard Guard chống trùng lặp UID/Email:**
   - Trước khi ghi bất kỳ tài khoản nào vào tracking workbook, BẮT BUỘC kiểm tra: Nếu `uid` hoặc `email` đã tồn tại ở bất kỳ dòng nào khác trong file $\rightarrow$ REJECT ngay và báo động xung đột, tuyệt đối không được ghi trùng lặp sang slot khác.
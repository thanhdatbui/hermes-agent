# Night Chain Reg & Email Continue Pitfalls (Tiktok_Reg)

## 1. False-Positive "Tat ca N email da co TK TikTok" do Header Collision
- **Nguyên nhân gốc rễ**:
  Trong `social_reg_v1.py` (`detect_after_continue()`), danh sách `form_hints` trước đây chứa cụm từ `"nhap dia chi email"`.
  Trên app TikTok tiếng Việt, tiêu đề tĩnh trên cùng của màn hình nhập email luôn là `<node text="Nhập địa chỉ email" .../>`.
  Khi script bấm nút "Tiếp tục", TikTok hiển thị spinner xoay trong nút bấm (lúc này button có `text=""`), trong khi HTTP request gửi đến server TikTok.
  Vì `"nhap dia chi email"` nằm trong `form_hints`, ngay ở vòng lặp đầu tiên của `detect_after_continue()`, script lập tức nhận diện là `form_still_visible` và trả về ngay mà không chờ server phản hồi.
- **Hệ quả dây chuyền**:
  Trong `fill_email_and_next()`, kết quả `form_still_visible` không được xử lý riêng mà rơi vào nhánh `else:`.
  Script in `khong xac dinh, thu tiep theo`, gửi `keyevent 4` (BACK) hủy bỏ flow đăng ký đang xử lý, và khi hết danh sách ứng viên email thì quăng exception:
  `RuntimeError: [07] Tat ca 1 email cua STT {stt} da co TK TikTok`.
  Lỗi này gây hiểu lầm nghiêm trọng rằng email đã đăng ký TikTok rồi, trong khi thực tế request vừa bấm gửi đã bị script tự bấm BACK hủy ngang.
- **Quy tắc sửa đổi**:
  - `form_hints` CHỈ ĐƯỢC chứa các thông báo lỗi xác thực thực sự (ví dụ: `"nhap dia chi email hop le"`, `"khong hop le"`, `"invalid email"`).
  - CẤM đưa chuỗi tiêu đề màn hình (`"nhap dia chi email"`) vào `form_hints`.
  - Trong thời gian chờ `timeout`, nếu nút bấm đang ở trạng thái loading (spinner/empty text) và không có text lỗi cụ thể, script BẮT BUỘC phải tiếp tục chờ màn hình chuyển tiếp (OTP, password, hoặc new account).

## 2. Tránh Chọn Máy Đã Đạt 8 Tài Khoản Khi Sheet Có Slot Pre-allocated
- **Nguyên nhân gốc rễ**:
  Trong `scripts/tiktok_target_eligibility.py` (`load_registered_mailboxes()`), logic đếm số acc hiện có của máy trước đây dùng điều kiện:
  `if tiktok_id and stt_idx is not None and stt_idx < len(row): machine_counts[m] += 1`
  Đối với các máy đã được phân bổ đủ 8 slot trong workbook tracking (`taikhoan_dat_v2_updated.xlsx`), nếu slot thứ 8 chưa có `tiktok_id` (trống), `machine_counts[m]` chỉ đếm được 7.
  Kết quả là `select_pending_targets()` coi máy này vẫn còn thiếu acc và tiếp tục chọn máy vào batch reg.
  Tuy nhiên, trên thiết bị vật lý thực tế, TikTok đã đăng nhập đủ 8 tài khoản (hoặc slot đã bị chiếm), dẫn đến việc `social_reg_v1.py` kiểm tra thấy máy đủ 8 acc và ném exception:
  `RuntimeError: [04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`.
- **Quy tắc sửa đổi**:
  - Khi tính toán `machine_counts` cho từng máy STT trong sheet tracking, BẮT BUỘC đếm toàn bộ các row đã gán cho máy đó (kể cả khi `tiktok_id` đang rỗng), để tôn trọng quota 8 slot đã phân bổ trong sheet và tránh kích hoạt reg trên máy đã full.

## 3. Phân Biệt Alert Lỗi Script/Pipeline Với Kết Quả Vận Hành Batch
- **Nguyên nhân gốc rễ**:
  Trong `_run_all_targets.py`, hàm `batch_exit_code()` luôn trả về `1` nếu `fail_count > 0` (đây là quy chuẩn status code cho batch).
  Tuy nhiên, trong `run_night_chain_pipeline.py`, Phase 2a chỉ kiểm tra `if tiktok_reg_code != 0: _send_night_chain_alert(...)`.
  Do đó, mỗi khi có máy lỗi vận hành (proxy sập, mạng chập chờn, máy full acc), script bắn alert Telegram dạng `[FARM ALERT: LỖI SCRIPT / PIPELINE]`.
- **Quy tắc sửa đổi**:
  - Đồng bộ logic guard giống như Phase 1 (Reg Gmail): kiểm tra `tiktok_details = parse_tiktok_details(tiktok_reg_out)`.
  - Nếu `tiktok_details.get("total", 0) > 0`, chứng tỏ batch runner đã khởi chạy và ghi nhận kết quả từng máy đầy đủ trong `all_results.json` (đây là kết quả vận hành farm, đã được tổng hợp chi tiết trong Báo Cáo Chuỗi Đêm). KHÔNG bắn alert lỗi script/pipeline nếu runner không bị crash/văng exception ngoài ý muốn.

# Watchdog Duplicate & Merged Session Pitfalls (Cạm Bẫy Báo Cáo Sớm, Lặp Phiên & Gộp Phiên)

## 1. Hiện Tượng & Triệu Chứng
- **Báo cáo bị gửi lặp 2 lần cùng một phiên**: Ví dụ Ca 3 - Phiên 1 gửi lần 1 lúc 19:23 (khi mới có 78 máy chạy xong), sau đó lúc 21:41 lại bắn tiếp một bản Ca 3 - Phiên 1 (khi đủ 80 máy và có 2 video upload thành công).
- **User tưởng thiếu báo cáo Phiên 2**: Người vận hành thắc mắc "sao không thấy bắn báo cáo phiên 2", nhưng thực chất phiên 2 đã được xuất gộp chung trong cùng một tin nhắn dài với phiên 1 (nửa trên phiên 1, nửa dưới phiên 2), do Telegram cắt preview hoặc người đọc chỉ nhìn thấy header trên cùng.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)

### A. Cơ Chế Giờ Cứng Ép Chốt Sớm (Hard Window-End + Grace Cutoff)
- Trong `can_report_session()`, khi `now_hm >= window_end_hm + grace_minutes`: logic cũ mặc định ép trả về `True` ("BẮT BUỘC chốt báo cáo") bất kể runner vẫn đang active xử lý nốt các máy cuối hoặc máy upload hook.
- Kết quả: Watchdog chốt sớm mẻ chạy khi mới đạt 78/80 máy.

### B. State Claim Race / Unlocked State File
- Ở lần chốt sớm, nếu state key (ví dụ `2026-09-17_ca3_phien1`) chưa được persist thành công vào `feed_session_reported.json` (hoặc bị ghi đè / rollback bởi process khác do xung đột lock), ở tick cron tiếp theo watchdog quét thấy thư mục run của phiên đó có dữ liệu mới (đủ 80 máy) nhưng chưa có trong danh sách đã chốt $\rightarrow$ Kích hoạt xuất báo cáo lần 2.

### C. Gộp Nhiều Phiên Vào Một Payload Text (`"\n\n".join(messages)`)
- Khi một phiên cũ bị sót và phiên mới vừa hoàn thành, watchdog duyệt qua cả hai phiên và gom cả 2 thông điệp vào mảng `messages`, sau đó in ra stdout một lần.
- Telegram adapter nhận 1 payload text lớn (>3.000 ký tự). Người dùng chỉ thấy banner trên cùng của Phiên 1 và không nhận ra Phiên 2 nằm ở nửa dưới.

## 3. Quy Chuẩn Vận Hành & Điều Tra Đối Soát (Coordinator Discipline)

1. **Điều Tra Bằng Artifact Thật Trước Khi Kết Luận**:
   - Tuyệt đối KHÔNG suy đoán mò nguyên nhân lặp tin nhắn.
   - BẮT BUỘC kiểm tra thư mục lưu trữ output cron: `C:/Users/Kibe/AppData/Local/hermes/cron/output/<job_id>/*.md`.
   - Đọc và diff trực tiếp các file `.md` tại các mốc giờ nghi vấn (ví dụ 19:23 vs 21:41 vs 22:32) để xác định chính xác nội dung từng lần xuất là gì.

2. **Kỷ Luật Thiết Kế Watchdog Farm**:
   - **Chỉ Báo Khi Xong E2E**: Watchdog chỉ được xuất báo cáo khi `is_feed_runner_active() == False` và `completed_expected_count >= expected_count`. Khi `is_today and now_hm >= window_end_hm`, nếu `runner_busy` thì bắt buộc `return False`, xóa bỏ hoàn toàn cơ chế grace period 20m ép chốt non.
   - **Tách Rời Từng Phiên (Per-Session Delivery)**: Mỗi phiên hoàn tất phải được ghi nhận và gửi độc lập. Nếu có nhiều phiên cùng đến hạn, gửi từng message riêng biệt hoặc claim cuốn chiếu để tránh nuốt chửng header của các phiên sau.

3. **Cơ Chế Đồng Bộ Đa Máy (Multi-Machine Sync: Kibe vs Admin)**:
   - Khi fix watchdog, BẮT BUỘC kiểm tra cả 2 chiều: logic xử lý theo host và cơ chế đồng bộ script qua mạng.
   - **Mã nguồn:** Đồng bộ script đồng thời lên `hermes/scripts`, `Hermes/deploy`, Git repo và OneDrive Shared (`D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\feed_session_watchdog.py`). Phía Admin nhận cập nhật tự động khi chạy `cron_sync_watchdog.py` hoặc `apply_sync_admin.py` (hoặc kéo git).
   - **Logic đa máy:** Script dùng hàm `_get_runtime_root()` đọc `TAADAA_HOST_CONFIG` (`kibe.yaml` vs `admin.yaml`) để tự động phân giải `runtime_root` tương ứng (`D:\Taadaa\runtime\kibe` vs `D:\Taadaa\runtime\admin`), đảm bảo mỗi máy chạy độc lập trên dữ liệu của cụm máy mình phụ trách mà không bị xung đột hay lệch phạm vi.

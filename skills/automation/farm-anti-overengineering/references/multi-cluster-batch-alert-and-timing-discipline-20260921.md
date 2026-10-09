# Multi-Cluster Batch Alert Merging & Sibling Timing Discipline (2026-09-21)

## 1. Bối cảnh & Hiện trạng hệ thống (Kibe vs Admin)
Farm 160 máy chia làm 2 cụm độc lập:
- **Cụm Kibe**: 80 máy (1–80), USB direct, máy chủ tại Thái Bình, lưu runtime tại `D:\Taadaa\runtime\kibe\live\...`.
- **Cụm Admin**: 80 máy (201–280), LAN socket qua IP `.119`, trạm máy tại Đà Nẵng, lưu runtime tại `D:\Taadaa\runtime\admin\live\...`.

Hai cụm có:
- Địa lý & IP tách biệt hoàn toàn (Thái Bình vs Đà Nẵng, 2 pool proxy 4G, ASN độc lập).
- Hạ tầng ADB độc lập (sự cố rớt máy Admin là do nguồn/ADB trạm Đà Nẵng, không phải máy Host Kibe quá tải).
- Đã có sẵn Session Jitter (1–3 phút) + Machine Stagger (2–8s/máy) + Randomize Machine Order -> Các nick tự động rải đều thời gian mở app trong 7–10 phút, không burst cùng 1 giây.

## 2. Phân vai Báo cáo: Watchdog Session Report vs Batch Alert
Hai cơ chế báo cáo phục vụ 2 mục đích khác nhau:
1. **Watchdog Session Report (`feed_session_watchdog.py`)**:
   - Nghiệm thu sản lượng sau ca/phiên.
   - BẮT BUỘC gộp 1 tin nhắn duy nhất toàn Farm (`【FARM KIBE】` & `【FARM ADMIN】`).
   - Chạy ngoài band, kiên nhẫn đợi cả 2 cụm hoàn tất mới bắn 1 lần.
2. **Batch Alert Lỗi Hệ thống (`batch_aggregator.py`)**:
   - Báo lỗi hệ thống lan rộng (>10% & >=3 máy) hoặc P0 Auth (văng account, mất phiên).
   - Vì runner gọi `batch_aggregator` ở cuối phiên khi các máy đã chạy xong: cả 2 cụm xuất phát cùng giờ và hoàn tất gần như đồng thời (lệch 1–2 phút).
   - BẮT BUỘC gộp làm 1 tin nhắn duy nhất `【TOÀN FARM】` thay vì bắn 2 tin lẻ gây loãng kênh Telegram.

## 3. Kiến trúc Sibling Merge trong `batch_aggregator.py`
1. **Phân loại Cụm (`classify_cluster`)**:
   - Nhận diện qua serial máy (`1..80` -> `kibe`, `201..280` -> `admin`).
   - Nhận diện qua đường dẫn runtime (lọc bỏ path người dùng `C:\Users\Kibe` để không match nhầm).
2. **Tự động bắt cặp Sibling (`find_sibling_batch_dir`)**:
   - Khi cụm Kibe chạy xong kiểm tra đường dẫn đối ứng bên Admin `runtime/admin/live/<date>/<session>` (và ngược lại).
   - Nếu cụm sibling đã hoàn tất (có `summary.txt` hoặc `run_manifest.json`): Load cả 2 cụm và gộp đánh giá.
   - `BATCH_ALERT_MAX_WAIT`: Timeout chờ sibling cán đích (mặc định 120s, cấu hình qua env). Trong unit test bắt buộc set `BATCH_ALERT_MAX_WAIT=0` để test chạy <1s.
3. **Format gộp (`format_multi_cluster_alert_message`)**:
   - Header: `🚨 [BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【TOÀN FARM】`
   - Khối `🏢 【FARM KIBE - MÁY 1-80】`: Chi tiết lỗi cụm Kibe.
   - Khối `🏢 【FARM ADMIN - MÁY 201-280】`: Chi tiết lỗi cụm Admin.
   - Khối Canary Test đại diện cho từng cụm.
4. **Deduplication Marker (`.sent`)**:
   - Ghi marker `D:/Taadaa/runtime/cron-state/batch-alerts/<session_key>.sent`.
   - Cụm về sau kiểm tra thấy marker sẽ Silent Skip, triệt tiêu 100% việc bắn tin thứ 2.

## 4. Pitfalls & Anti-Patterns (Bài học xương máu)
- **CẤM suy diễn lý thuyết suông (Hallucinated Overload)**: Không được vội vàng kết luận "160 máy quá tải USB/socket nên phải delay 15–20 phút" khi chưa kiểm chứng hiện trường. Thực tế 2 cụm ở 2 tỉnh khác nhau, IP khác nhau và đã có stagger sẵn.
- **CẤM đổi giọng lươn lẹo, nịnh bợ (Sycophancy)**: Khi user chỉ ra sự thật ("1 cụm Thái Bình 1 cụm Đà Nẵng"), trả lời thẳng thắn vào trọng tâm kỹ thuật, CẤM quay ngoắt 180 độ rồi dùng văn mẫu xin lỗi lòng vòng.
- **User hỏi dấu `?` hoặc `.`**: Nghĩa là câu trả lời trước đó quá dài dòng, không trả lời thẳng vào câu hỏi chính hoặc có mâu thuẫn. Phải trả lời trực diện CÓ/KHÔNG trong 1–2 câu đầu tiên, không giải thích tràng giang đại hải.

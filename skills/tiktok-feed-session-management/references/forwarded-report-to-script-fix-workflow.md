# Quy Trình Giải Mã Báo Cáo Forward & Sửa Code O(1) (Forward Report = Lệnh Fix Code)

## 1. Nguyên Tắc Cốt Lõi (Invariants)
- **Mệnh lệnh hành động dứt điểm:** Khi User forward bất kỳ tin nhắn báo cáo nào từ bot watchdog (phiên nuôi, follow, upload) vào chat, Coordinator **CẤM TUYỆT ĐỐI** hỏi lại:
  * Không hỏi: *"Bạn có muốn tôi sửa không?"*
  * Không hỏi: *"Tôi thấy có 20 máy lỗi mở app, tôi nên làm gì?"*
- **Tự động kích hoạt luồng sửa gốc:** Đọc tin nhắn forward -> trích xuất thông số O(1) -> đọc log 1 máy đại diện -> định vị script -> sửa code O(1) <= 30 dòng -> kiểm thử pytest -> canary máy thật -> báo cáo kết quả kèm ảnh nghiệm thu.

## 2. Quy Tắc Giải Mã Báo Cáo O(1)
Từ nội dung tin nhắn forward, bóc tách ngay 4 trường thông tin:

1. **Repo nguồn:**
   - `[TIKTOK NUÔI ACC]` -> `D:/Taadaa/tiktok-luot nuoi acc`
   - `[TIKTOK FOLLOW]` -> `D:/Taadaa/tiktok-follow`
   - `[TIKTOK VIDEO]` -> `D:/Taadaa/tiktok-luot nuoi acc` (khâu upload) hoặc `D:/Taadaa/orders`
2. **Thư mục Log O(1):**
   - Từ cụm (`【Cụm Kibe Local】` hoặc `【Farm Admin】`), `(Row X)` (hoặc `Pool {..}`), và `(Run: YYYYMMDD-HHMMSS)`:
   - Đường dẫn: `D:/Taadaa/runtime/{cluster}/live/{YYYY-MM-DD}/row-{row}-*/{run_id}/`
   - Nếu có dòng `📁 Trace: <path>` ở chân báo cáo, dùng trực tiếp đường dẫn tuyệt đối đó.
3. **Map nhóm lỗi sang file code:**
   - `Lỗi mở/focus App TikTok` -> `python_runner/flows/device_prepare.py` (`prepare_tiktok_app_for_automation`, `recover_systemui_occlusion`).
   - `Lỗi thao tác vuốt (Swipe)` -> `python_runner/flows/feed_session.py`.
   - `Lệch Profile/Nick TikTok` / `Kẹt Account Switcher` -> `python_runner/flows/account_switcher.py`.
   - `Chưa gán Proxy` / `Nghẽn đường truyền Proxy / 4G` -> `farm_network_gate.py` hoặc adapter network.
4. **Trích xuất log máy đại diện:**
   - Chọn ngay 1 máy trong danh sách lỗi `+ Fail (N)` hoặc `+ Lỗi mở app (N): M1, M2... M69`.
   - Đọc trực tiếp: `.../machines/machine_{M}/{run_id}/log.jsonl` hoặc `summary.txt`.
   - Tra cứu trạng thái màn hình hiện tại: `python D:/Taadaa/tools/inspect_machine.py <M>`.

## 3. Phân Định Rõ Ràng: Báo Cáo Phiên Nuôi vs Farm Alert
- **Không tùy tiện đổi tiêu đề phiên nuôi:** Tiêu đề phiên nuôi phải giữ nguyên định dạng chuẩn `📊 [TIKTOK NUÔI ACC] Ca X hoàn tất ({Pool/Row})` gửi đúng nhóm Nuôi (`-5377611430`).
- **Phạm vi của `🚨 [FARM ALERT]`:** Chỉ kích hoạt khi sập nguồn/cháy proxy diện rộng hoặc lỗi script Follow/Upload hàng loạt (`>= 8 máy` ~ 10% farm). Không gán ép `[FARM ALERT]` lên phiên nuôi feed để tránh báo động giả, làm hoảng loạn người trực.
- **Tính nhất quán (Chống flip-flopping):** Không được trả lời lúc khuyên revert, lúc khuyên giữ nguyên gây khó chịu cho người dùng. Bám chặt kỷ luật: giữ vững format báo cáo sạch sẽ, xử lý lỗi dứt điểm ở tầng code.

## 4. Kỷ Luật Thẩm Định Đóng Phiên (Closeout Gate)
- Khi người dùng phát lệnh đóng phiên ("xong phiên", "chốt phiên", "done"):
  * Chạy `python D:/Taadaa/tools/closeout_gate.py --repo <repo> --base HEAD~1 --json-output`.
  * Yêu cầu đạt `Overall Score >= 85/100` (hoặc Grace Band 80-84 có test verified) mới được phép kết thúc.
- Nếu trượt (< 85 điểm):
  * **Strike 1 & 2:** Kích hoạt Sol Repair (`sol_repair.py`).
  * **Fallback Worker:** Nếu `sol_repair.py` exit != 0, timeout hoặc valid=False, được phép fallback sang Worker (`dispatch_worker.py`) hoặc Coordinator L2 (ngân sách O(1) <= 30 dòng).
  * **Đồng bộ hóa Code & Test:** Mọi thay đổi logic output/format trong code bắt buộc phải cập nhật đồng bộ trong test assertion tương ứng trước khi chạy closeout gate để tránh reviewer từ chối do thiếu bằng chứng nhất quán.

# Canary Evidence Selection Policy & Chống Cargo Cult Screencap (02/11/2026)

## 1. Căn Nguyên Sự Cố & Lỗi "Cargo Cult Screencap"
- **Sự cố thực tế:** Khi sửa code backend/scheduler/loader SQLite (`freeze_targets_from_sqlite()` trong `run_batch_live_2fa.py`), runner không chạm thiết bị hay UI TikTok.
- **Hành vi sai lầm (Cargo Cult):** Agent bị ám ảnh bởi Gate 6 đòi hỏi ảnh máy thật, tự gửi lệnh ADB `input keyevent 224` bật màn hình và mở app TikTok để chụp đại một tấm ảnh feed video (không liên quan gì tới code vừa vá), tự khen ảnh nét để pass gate.
- **Bản chất kiến trúc:** Lệch pha giữa Intent (ý định thay đổi mã nguồn) và Verification Vector (véc-tơ kiểm chứng). Tầng lập kế hoạch (`canary_plan.py`) đã có LLM suy luận, nhưng tầng thực thi (`canary_runner.py`) lại áp dụng cào bằng: bắt buộc 100% repo farm phải nộp ảnh màn hình điện thoại.

## 2. Nguyên Tắc Phân Loại Evidence Type (Tự Tính Từ Diff, Cấm Nghe Agent Khai)
Theo kết luận của Hội đồng Cố vấn (Sol, Gemini, Claude):
- **Thuộc tính của bề mặt mã nguồn bị sửa:** Evidence Type do Gate tự tính từ cumulative diff kể từ canary base, không được dựa vào lời khai hay task prompt của Agent.
- **Quy tắc Max-Severity:**
  1. **Backend / Data / Scheduler / SSOT thuần:** Chỉ sửa query SQLite, thuật toán sort, parser json, lock server, data loader:
     - Evidence bắt buộc: `assert log_assertions + receipt + exit code 0`.
     - CẤM đè máy ra chụp ảnh giả mạo.
  2. **UI Automation / Flow / Click / Tap:** Sửa selector, tọa độ, flow chạm màn hình, XML layout, gesture:
     - Evidence bắt buộc: `screencap do Harness tự chụp + OCR khớp predicate + Vision xác thực`.
  3. **Hỗn hợp (Hybrid):** Sửa cả hai $\rightarrow$ BẮT BUỘC CẢ HAI (Log assertions đạt VÀ Screencap đạt). Không loại nào được thay thế loại nào.
  4. **Path lạ hoặc chưa phân loại được:** Mặc định Fail-Closed coi là UI.

## 3. Rào Chắn Chống Trốn Chụp Ảnh (Anti-Evasion Rules)
- **Harness độc quyền chụp ảnh:** Cấm tuyệt đối Agent tự nộp ảnh `MEDIA:` từ bên ngoài vào runner.
- **Cryptographic Binding:** Receipt bind chặt `diff_hash + device_serial + sha256(ảnh) + timestamp`. Timestamp bắt buộc lớn hơn `mtime` của lần sửa file UI cuối để chặn nộp lại ảnh cũ.
- **Predicate khai trước:** Task UI bắt buộc có predicate OCR / từ khóa kỳ vọng. Chụp màn hình ra mà OCR không khớp predicate thì `FAIL`, cấm chụp đại feed video lướt lướt cho xong.
- **Tách rãnh lỗi:** Hạ tầng bận lock hoặc ADB offline thì đánh dấu `BLOCKED`, tuyệt đối không được tự ý downgrade thành Backend để cấp PASS.

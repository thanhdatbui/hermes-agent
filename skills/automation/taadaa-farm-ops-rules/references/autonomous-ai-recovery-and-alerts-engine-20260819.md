# Autonomous AI Recovery Engine & Quy Trình 5 Bước Khép Kín (2026-08-19)

## 1. Bản Chất & Mục Tiêu
Cơ chế **Autonomous AI Recovery** cho Farm 80 máy Android:
- Khi máy gặp lỗi trong ca nuôi TikTok (popup lạ, thẻ gợi ý bạn bè, livestream, khảo sát quảng cáo, sai lệch profile...):
- **Tuyệt đối CẤM:**
  1. Cấm dùng if/else string cứng nhắc hay template rập khuôn.
  2. Cấm bắn lệnh ADB thô bằng tay trực tiếp lên máy rồi mới viết code (làm mất hiện trường lỗi, không kiểm chứng được code).
  3. Cấm ép máy về Feed một cách máy móc (kẹt ở bước nào: Login, OTP, Captcha, DOB, Profile, Popup... thì gỡ đúng bước đó).
  4. Cấm chạy lại script từ đầu (`--resume` / rerun from start) làm mất state.

---

## 2. Quy Trình 5 Bước Khép Kín Chuẩn Xác

```
[MÁY XX BỊ DỪNG PHIÊN TRONG CA NUÔI]
               │
               ▼
[BƯỚC 1: SCRIPT BẮN ALERT VÀO FARM ALERTS (0 TOKEN)]
• Script chạy trên máy chụp ảnh lỗi, vẽ Banner Đỏ [MAY XX] - HH:MM DD/MM.
• Gửi Tin nhắn 1 (Photo + Caption chi tiết) vào nhóm Telegram Farm Alerts (-5373649734).
• BẮT BUỘC GIỮ NGUYÊN HIỆN TRƯỜNG trên máy (CẤM tắt app, CẤM bấm Home).
               │
               ▼
[BƯỚC 2: AI RECOVERY AGENT ĐỌC ẢNH & VÁ CODE VÀO REPO TRƯỚC]
• AI Agent đọc ảnh lỗi và cây UI XML tại hiện trường.
• Phân tích bản chất blocker (thẻ bạn bè, dialog quảng cáo, khảo sát...).
  - Thẻ 'Người bạn có thể biết' / 'Follow lại' ➔ Bấm nút 'Follow lại' màu đỏ.
  - Popup thông tin / 'Tìm hiểu thêm' ➔ Bấm nút 'Đóng' / 'X'.
• VIẾT CODE TRƯỚC: Mở file runner (feed_swipe_smoke.py / benign_popup.py) bổ sung rule/selector/handler vào repo.
               │
               ▼
[BƯỚC 3: CHẠY CHÍNH HÀM VỪA VÁ TRỰC TIẾP LÊN MÁY ĐANG KẸT]
• Kích hoạt hàm vừa viết chạy thử trực tiếp trên máy đang lỗi tại hiện trường.
• Kiểm chứng thực tế: Đoạn code mới có tự động phát hiện và vượt qua lỗi hay không.
• Nếu test fail ➔ Rollback code ngay (git checkout -- <file>), giữ nguyên hiện trường.
               │
               ▼
[BƯỚC 4: PLAN-REVIEW AUDIT & COMMIT ĐỒNG BỘ TOÀN FARM]
• Xuất git diff gọi Model Plan-Review audit độc lập (Claude CLI --effort max / 9Router plan-review).
• BẮT BUỘC nhận VERDICT: APPROVED.
• Chạy test suite pytest (test_feed_swipe_smoke.py, test_ai_recovery.py) xác nhận 100% PASS (Regression Check).
• Commit & Push Git origin master để toàn bộ 80 máy nhận bản vá.
               │
               ▼
[BƯỚC 5: GỬI BÁO CÁO RECOVERY VÀO NHÓM FARM ALERTS]
• Gửi Tin nhắn 2 Reply trực tiếp dưới ảnh alert theo mẫu chuẩn:
  🛠️ [AI AUTO-RECOVERY - MÁY XX]
  • Hướng sửa: <Giải thích lỗi kỹ thuật & logic đã vá vào script>
  • Kết quả: <Kết quả test thực tế máy đã vượt qua bước kẹt và tiếp tục luồng>
  • (Nếu đúng ý bạn im lặng bỏ qua, cần sửa cách khác hãy nhắn lại)
```

---

## 3. Cấu Trúc Module AI Recovery Trong Repo `tiktok-luot nuoi acc`
Module `python_runner/ai_recovery/`:
- `agent.py`: Nhạc trưởng điều phối 5 bước recovery.
- `vision_client.py`: Trích xuất ảnh + XML và gọi Vision LLM phân tích blocker.
- `code_patcher.py`: Tự động vá rule vào `GEMPHONEFARM_BLIND_POPUP_RULES`, hỗ trợ Auto-Rollback 15 phút nếu có $\ge 3$ alert lỗi tương tự.
- `plan_reviewer.py`: Gọi Model Plan-Review audit git diff.
- `screen_verifier.py`: Thuật toán so khớp dHash Hamming distance + package/activity live pre-check.
- `recovery_lock.py`: Quản lý khóa Per-Device Lock (TTL 5 phút, atomic claim).
- `tests/test_ai_recovery.py`: Bộ 35 unit/integration tests bao phủ 100%.

---

## 4. Cấu Hình Telegram Gateway & Bot Self-Message Gotcha
- **Vấn đề Telegram Self-Message:** Telegram Bot API không bao giờ gửi `getUpdates` cho tin nhắn do chính Bot Token đó gửi ra.
- **Cấu hình Gateway:**
  - File `.env`: Bổ sung `TELEGRAM_ALLOW_BOTS=all` để cho phép bot nhận tin từ hệ thống.
  - File `config.yaml`: Gắn `channel_overrides` cho `-5373649734` (Farm Alerts) với `require_mention: false` và `observe_unmentioned_group_messages: true`.
- **Producer:** `automation_core/alerts.py` giữ vai trò pure 0-token producer (chỉ chụp ảnh Banner Đỏ + gửi Telegram 1).

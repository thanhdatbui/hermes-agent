Niche: video là Ground Truth. Dữ liệu toàn farm bắt buộc chuẩn hoá SQLite SSOT (farm_master.db); Excel chỉ là mirror một chiều cho người xem, cấm dùng trong runtime.
§
User yêu cầu gom Hermes codebase về một mối duy nhất tại D:\Taadaa\Hermes; tuyệt đối không để desync hay xóa nhầm thư viện/cấu hình riêng ở ổ C khi chưa đối soát an toàn.
§
User ép ảnh Telegram trực tiếp qua Multimodal Native của Gemini (image_input_mode: native); CẤM dùng browser_vision mở file local đối phó rồi đoán mò/hallucinate mô tả ảnh; kiểm chứng text/UI bắt buộc WinRT OCR thật. Khi phát ngôn cam kết hành động bắt buộc emit tool call ngay trong turn, cấm hứa hẹn suông.
§
User yêu cầu chuẩn hóa dữ liệu toàn farm trên SQLite SSOT (farm_master.db), tuyệt đối không để rò rỉ hay phụ thuộc runtime vào file Excel. Cấm Coordinator hứa hẹn suông ('em sẽ...') trong câu trả lời; phải lập tức gọi tool hoặc báo cáo bằng chứng thực tế.
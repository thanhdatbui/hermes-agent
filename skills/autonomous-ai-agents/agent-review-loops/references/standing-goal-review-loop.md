# Standing-goal review loop

Khi user yêu cầu làm đến khi xong hoặc dùng `/goal`, loop phải kín với user:

1. Chuẩn hóa một context/spec duy nhất và absolute workdir.
2. Dispatch đúng một worker sửa working tree.
3. Xác minh diff/file thực tế; không tin self-report nếu patch validation fail.
4. Dispatch reviewer read-only trên diff mới.
5. Nếu reviewer còn finding, gửi trực tiếp finding đó cho worker; không hỏi user và không trình intermediate report.
6. Lặp đến `APPROVED`; `MINOR_FIXES` chưa đủ nếu finding ảnh hưởng live path.
7. Nếu child cũ chạy theo clarification lỗi thời, ignore kết quả và không để nhiều worker cùng sửa một tree.
8. Chỉ báo user khi APPROVED, FINAL_BLOCKED hoặc MAX_ROUNDS. Evidence cuối phải gồm reviewer verdict và test output thực tế.
9. Nếu user tự hỏi "làm tới đâu rồi" giữa loop, tóm tắt ngắn gọn trạng thái mà không giải thích quy trình loop hay biện minh; không xin lỗi.

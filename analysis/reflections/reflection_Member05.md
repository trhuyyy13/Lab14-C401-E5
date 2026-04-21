# Reflection - Member05

## 1) Vai trò & Phạm vi đóng góp
- Vai trò trong team: DevOps/Validation.
- Module phụ trách: kiểm tra artifact, chuẩn hóa quy trình chạy.

## 2) Đóng góp kỹ thuật chính
- Xây dựng flow chạy ổn định: generate dataset -> benchmark -> check_lab.
- Đảm bảo report sinh ra đúng định dạng chấm tự động.

## 3) Kết quả đo được
- Pipeline có thể chạy end-to-end và pass checker.

## 4) Vấn đề gặp phải & cách xử lý
- Vấn đề: lỗi shell/heredoc làm hỏng lệnh thống kê.
- Xử lý: chuyển sang command an toàn và tách bước kiểm tra rõ ràng.

## 5) Bài học rút ra
- Tính reproducible của pipeline quan trọng không kém metric chất lượng.

## 6) Kế hoạch cải tiến cá nhân
- Tự động hóa bằng script task để giảm lỗi thao tác thủ công.

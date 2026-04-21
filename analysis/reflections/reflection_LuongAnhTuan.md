# Reflection - Lương Anh Tuấn

## 1. Phân công và đóng góp kỹ thuật
- Tham gia refactor các module quan trọng để code gọn hơn và dễ mở rộng: tách helper cho benchmark summary, fallback payload khi test case lỗi, và helper cho judge heuristic.  
- Đồng bộ luồng dữ liệu theo codebase mới: chuyển tất cả điểm fallback về `data.txt`, loại bỏ biến `raw_repo_path` không còn phù hợp.  
- Cập nhật script hỗ trợ dataset/chunk (`data/print_chunks.py`, `data/synthetic_gen.py`) để tránh mismatch signature và lỗi runtime.  
- Hỗ trợ kiểm tra ổn định sau thay đổi bằng cách chạy check lỗi và rà soát lại các file tham chiếu tên dữ liệu cũ.  

## 2. Kiến thức kỹ thuật rút ra
- Refactor hiệu quả là refactor giảm lặp và tăng độ rõ ràng, không thay đổi output nghiệp vụ.  
- Khi đổi tên file dữ liệu, cần scan toàn repo để đảm bảo loader, metadata, helper script và thông báo lỗi đều cập nhật đồng bộ.  
- Trong pipeline đánh giá, có fallback rõ ràng sẽ giúp benchmark tiếp tục tạo report dù gặp ngoại lệ, thay vì vỡ toàn bộ luồng.  
- Tách logic tính metric vào một hàm riêng giúp dễ test, dễ review và dễ sửa công thức mà không ảnh hưởng nhiều nơi.  

## 3. Vấn đề gặp phải và cách xử lý
- **Vấn đề 1:** Code vẫn còn tham chiếu file dữ liệu cũ sau khi đổi tên.  
  - *Xử lý:* Dùng tìm kiếm toàn workspace và cập nhật lại đường dẫn tại Agent, SDG và metadata source.  

- **Vấn đề 2:** Sau khi đổi signature hàm load chunk, call site cũ bị sai số tham số.  
  - *Xử lý:* Chuẩn hóa hàm `load_and_chunk_real_data` và cập nhật tất cả nơi gọi để chỉ nhận một `source_file`.  

- **Vấn đề 3:** Reflection cần phản ánh đúng hiện trạng codebase sau refactor, không dùng nội dung cũ.  
  - *Xử lý:* Viết lại reflection theo thay đổi mới, nêu rõ bài học kỹ thuật và bước nâng cấp tiếp theo.  

## 4. Kế hoạch cải tiến tiếp theo
- Bổ sung test nhỏ cho các helper mới (`_compute_summary`, fallback payload, helper thống kê) để giảm rủi ro regression.  
- Tách cấu hình tên file dữ liệu và các ngưỡng release gate thành constant/env để tránh hard-code phân tán.  
- Nâng cấp retrieval từ lexical overlap lên hybrid retrieval (BM25 + embedding) để ổn định hơn với edge/adversarial cases.  
- Chuẩn hóa thêm logging thống nhất để dễ đối chiếu giữa benchmark result và failure analysis.  
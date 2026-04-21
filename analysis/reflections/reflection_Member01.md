# Reflection - Member01

## 1) Vai trò & Phạm vi đóng góp
- Vai trò trong team: Data/Chunking.
- Module phụ trách: `data/legal_chunker.py`, `data/synthetic_gen.py`.
- File/chức năng đã chỉnh sửa: Hybrid chunking (article + clause), tạo `golden_set` bằng LLM.

## 2) Đóng góp kỹ thuật chính
- Thiết kế lại chunking từ fixed-size sang hybrid theo cấu trúc pháp lý.
- Sửa parser để bỏ phần mở đầu Nghị định, bắt đầu đúng từ Điều lệ.
- Chuẩn hóa metadata `expected_retrieval_ids` để đo Hit Rate/MRR.

## 3) Kết quả đo được
- Hệ thống tạo được 60 test cases ổn định.
- Có thể đo retrieval metrics xuyên suốt pipeline benchmark.

## 4) Vấn đề gặp phải & cách xử lý
- Vấn đề: parse sai 4 điều đầu vì văn bản có phần Nghị định trước Điều lệ.
- Xử lý: thêm logic nhận diện điểm bắt đầu Điều lệ và dựng Điều 1 hợp lý.

## 5) Bài học rút ra
- Dữ liệu pháp lý cần parsing theo cấu trúc văn bản, không thể split ký tự đơn thuần.

## 6) Kế hoạch cải tiến cá nhân
- Bổ sung bộ test parser tự động cho nhiều định dạng văn bản pháp luật.

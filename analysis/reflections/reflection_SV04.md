# Reflection - SV04

## Module phụ trách
- [x] Retrieval evaluation
- [ ] Multi-judge
- [ ] Benchmark runner async
- [ ] Failure analysis

## Đóng góp kỹ thuật
- Mô tả commit/chức năng đã làm: Thiết kế lại `data/synthetic_gen.py` để đọc 2 văn bản luật, tách theo Điều, tạo 80 cases gồm `fact-check`, `summary`, `responsibility`, cùng hard cases `adversarial`, `edge-case`, `multi-turn`, `technical`, và gắn `expected_retrieval_ids`.
- Khó khăn gặp phải: Văn bản pháp lý dài, nhiều ký tự đặc biệt và xuống dòng làm tách đoạn không ổn định.
- Cách xử lý: Chuẩn hóa text bằng regex, giới hạn context theo độ dài hợp lý, định danh `source_id` thống nhất `file#dieu_n`.

## Bài học rút ra
- Trade-off giữa chất lượng và chi phí: Dataset lớn và đa dạng giúp đánh giá tốt hơn nhưng tăng thời gian chạy benchmark.
- Điều sẽ làm tốt hơn ở vòng sau: Thêm nhóm `conflicting info` và `out-of-context` để stress test logic từ chối trả lời.

## Minh chứng
- PR/commit link: cập nhật `data/synthetic_gen.py`, `data/golden_set.jsonl`.
- Ảnh/chụp log benchmark: Total cases = 80, có đầy đủ trường `expected_retrieval_ids` và hard-case metadata.

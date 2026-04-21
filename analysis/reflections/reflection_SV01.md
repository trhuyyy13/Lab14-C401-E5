# Reflection - SV01

## Module phụ trách
- [x] Retrieval evaluation
- [ ] Multi-judge
- [ ] Benchmark runner async
- [ ] Failure analysis

## Đóng góp kỹ thuật
- Mô tả commit/chức năng đã làm: Hoàn thiện `RetrievalEvaluator` gồm `calculate_hit_rate`, `calculate_mrr`, `evaluate_case`, `evaluate_batch`; chuẩn hóa cách tính top-k và trả về `per_case` để debug.
- Khó khăn gặp phải: Ban đầu metric retrieval không phản ánh đúng vì dữ liệu chưa có ground-truth id nhất quán.
- Cách xử lý: Thống nhất schema `expected_retrieval_ids` trong golden set và nối pipeline để đánh giá retrieval trực tiếp từ kết quả agent.

## Bài học rút ra
- Trade-off giữa chất lượng và chi phí: Tính thêm metric chi tiết giúp chẩn đoán nhanh nhưng tăng kích thước log và thời gian phân tích.
- Điều sẽ làm tốt hơn ở vòng sau: Bổ sung metric Recall@k và NDCG để đánh giá sâu hơn khi mở rộng dữ liệu.

## Minh chứng
- PR/commit link: cập nhật các file `engine/retrieval_eval.py`, `main.py`.
- Ảnh/chụp log benchmark: Hit Rate = 97.5%, MRR = 0.975, Total cases = 80.

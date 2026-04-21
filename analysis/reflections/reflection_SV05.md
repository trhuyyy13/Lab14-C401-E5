# Reflection - SV05

## Module phụ trách
- [ ] Retrieval evaluation
- [x] Multi-judge
- [ ] Benchmark runner async
- [ ] Failure analysis

## Đóng góp kỹ thuật
- Mô tả commit/chức năng đã làm: Tích hợp toàn bộ engine vào `main.py`, tạo summary metrics đầy đủ và logic regression gate (score/hit_rate/latency/cost) để quyết định approve hoặc block release.
- Khó khăn gặp phải: Gate ban đầu nhạy với jitter latency, có lúc block dù chất lượng không giảm.
- Cách xử lý: Làm mượt tỷ lệ latency bằng `latency_floor` và điều chỉnh ngưỡng để giảm false block.

## Bài học rút ra
- Trade-off giữa chất lượng và chi phí: Gate chặt giúp an toàn phát hành nhưng nếu quá nhạy sẽ cản trở vòng lặp cải tiến nhanh.
- Điều sẽ làm tốt hơn ở vòng sau: Bổ sung confidence interval cho latency và so sánh trên nhiều lượt chạy.

## Minh chứng
- PR/commit link: cập nhật `main.py` và cấu trúc `reports/summary.json`.
- Ảnh/chụp log benchmark: Regression = APPROVE, score delta = -0.0051, latency ratio = 1.24, cost ratio = 1.00.

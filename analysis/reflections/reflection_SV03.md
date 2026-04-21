# Reflection - SV03

## Module phụ trách
- [ ] Retrieval evaluation
- [ ] Multi-judge
- [x] Benchmark runner async
- [ ] Failure analysis

## Đóng góp kỹ thuật
- Mô tả commit/chức năng đã làm: Nâng cấp `BenchmarkRunner` để thu thập `latency`, `token_usage`, `estimated_cost_usd`, và giữ chạy batch async bằng `asyncio.gather`.
- Khó khăn gặp phải: Khi thêm nhiều metric dễ làm vỡ cấu trúc report cũ.
- Cách xử lý: Chuẩn hóa output schema ở `runner.py` và cập nhật phần tổng hợp trong `main.py` đồng bộ.

## Bài học rút ra
- Trade-off giữa chất lượng và chi phí: Thu nhiều telemetry giúp tối ưu nhanh nhưng cần quản lý format chặt để tránh lỗi chấm tự động.
- Điều sẽ làm tốt hơn ở vòng sau: Bổ sung profiling theo từng bước retrieval/generation/judge thay vì chỉ tổng latency.

## Minh chứng
- PR/commit link: cập nhật `engine/runner.py`, `main.py`.
- Ảnh/chụp log benchmark: Avg latency = 0.074s/case, Total tokens = 15,051, Cost/eval = 0.0001129 USD.

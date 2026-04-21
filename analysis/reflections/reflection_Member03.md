# Reflection - Member03

## 1) Vai trò & Phạm vi đóng góp
- Vai trò trong team: Benchmark pipeline.
- Module phụ trách: `main.py`, `engine/runner.py`.

## 2) Đóng góp kỹ thuật chính
- Chuẩn hóa pipeline benchmark async và format output report.
- Bổ sung metrics tổng hợp: latency, cost, final answer accuracy, hallucination rate.

## 3) Kết quả đo được
- `reports/summary.json` có đầy đủ metrics theo yêu cầu lab.

## 4) Vấn đề gặp phải & cách xử lý
- Vấn đề: so sánh regression không phản ánh đúng khi chỉ nhìn `avg_score`.
- Xử lý: bổ sung quality index và delta theo hit rate/mrr/retrieval accuracy.

## 5) Bài học rút ra
- Cần chọn đúng KPI để ra quyết định release/rollback.

## 6) Kế hoạch cải tiến cá nhân
- Viết script compare-runs để theo dõi xu hướng chất lượng theo thời gian.

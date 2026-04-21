# Reflection - SV02

## Module phụ trách
- [ ] Retrieval evaluation
- [x] Multi-judge
- [ ] Benchmark runner async
- [ ] Failure analysis

## Đóng góp kỹ thuật
- Mô tả commit/chức năng đã làm: Thiết kế `LLMJudge` với 2 judge (`gpt-4o`, `gpt-4o-mini`) chạy qua OpenAI API, rubric 3 tiêu chí (accuracy/professionalism/safety), công thức agreement và conflict resolution.
- Khó khăn gặp phải: Nếu chấm điểm quá cứng thì dễ lệch giữa các case summary và adversarial.
- Cách xử lý: Thêm calibration offset nhẹ giữa judge, giữ rule arbitration bảo thủ khi chênh lệch lớn.

## Bài học rút ra
- Trade-off giữa chất lượng và chi phí: Multi-judge tăng độ tin cậy nhưng làm pipeline dài hơn và tốn tài nguyên đánh giá.
- Điều sẽ làm tốt hơn ở vòng sau: Áp dụng trigger chỉ chạy judge thứ 2 cho case có độ tự tin thấp để tiết kiệm chi phí.

## Minh chứng
- PR/commit link: cập nhật `engine/llm_judge.py` và phần tổng hợp metric trong `main.py`.
- Ảnh/chụp log benchmark: Agreement Rate = 93.1%, Avg Score = 4.08/5.0, using_openai = true.

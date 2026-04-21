# Reflection - SV06

## Module phụ trách
- [ ] Retrieval evaluation
- [ ] Multi-judge
- [x] Benchmark runner async
- [x] Failure analysis

## Đóng góp kỹ thuật
- Mô tả commit/chức năng đã làm: Tổng hợp log benchmark, thực hiện failure clustering, viết báo cáo 5 Whys cho các case relevancy thấp và đề xuất action plan theo mức ưu tiên.
- Khó khăn gặp phải: Sau tối ưu retrieval, không còn fail case nên khó trình bày "thất bại" theo cách cũ.
- Cách xử lý: Chuyển hướng phân tích từ fail tuyệt đối sang near-miss (relevancy thấp/faithfulness thấp) để vẫn chỉ ra điểm cần cải tiến thật.

## Bài học rút ra
- Trade-off giữa chất lượng và chi phí: Tối ưu retrieval tăng mạnh chất lượng nhưng vẫn cần cải thiện generation để tăng độ phù hợp nội dung.
- Điều sẽ làm tốt hơn ở vòng sau: Viết prompt riêng cho từng loại câu hỏi (`summary`, `adversarial`) và đánh giá A/B trước khi chốt.

## Minh chứng
- PR/commit link: cập nhật `analysis/failure_analysis.md` và hỗ trợ validation bằng `python main.py`, `python check_lab.py`.
- Ảnh/chụp log benchmark: Pass rate = 97.5% (78/80), Avg score = 4.08, Hit Rate = 97.5%, Agreement = 93.1%.

# Reflection - Member02

## 1) Vai trò & Phạm vi đóng góp
- Vai trò trong team: Retrieval/Eval.
- Module phụ trách: `agent/main_agent.py`, `engine/retrieval_eval.py`.

## 2) Đóng góp kỹ thuật chính
- Triển khai retrieval lexical với boost theo `Điều`/`khoản`.
- Bổ sung chỉ số `top1_accuracy` ngoài Hit Rate/MRR.

## 3) Kết quả đo được
- Retrieval metrics có thể theo dõi theo từng case.
- Cải thiện khả năng truy hồi đúng theo anchor pháp lý.

## 4) Vấn đề gặp phải & cách xử lý
- Vấn đề: query yes/no mơ hồ dễ miss.
- Xử lý: thêm tín hiệu boost, điều chỉnh chiến lược rank top-k.

## 5) Bài học rút ra
- Retrieval đúng context quyết định trực tiếp chất lượng answer.

## 6) Kế hoạch cải tiến cá nhân
- Thêm query rewrite + reranking để giảm miss ở câu hỏi mơ hồ.

# Reflection - Member06

## 1) Vai trò & Phạm vi đóng góp
- Vai trò trong team: Product/QA.
- Module phụ trách: rà chất lượng câu hỏi, kiểm tra tính hợp lệ output.

## 2) Đóng góp kỹ thuật chính
- Rà soát chất lượng `golden_set` (đa dạng dạng câu hỏi, mapping ID).
- Đánh giá khả năng giải thích kết quả trước/sau tối ưu.

## 3) Kết quả đo được
- Dataset đạt 60 cases, có metadata phục vụ retrieval eval.

## 4) Vấn đề gặp phải & cách xử lý
- Vấn đề: so sánh trước/sau dễ sai nếu thay đổi dataset.
- Xử lý: đề xuất freeze dataset để regression công bằng.

## 5) Bài học rút ra
- Đo lường phải nhất quán thì mới kết luận được hiệu quả tối ưu.

## 6) Kế hoạch cải tiến cá nhân
- Thêm bộ câu hỏi hard-case cố định để regression lâu dài.

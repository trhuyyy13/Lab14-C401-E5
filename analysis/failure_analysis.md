# Báo cáo Phân tích Thất bại (Failure Analysis Report)

## 1. Tổng quan Benchmark mới (đã cập nhật)
- Tổng số cases: 99
- Pass/Fail: 94/5 (Pass rate: 94.95%)
- Điểm trung bình (LLM Judge): 4.8182 / 5.0
- Faithfulness: 0.9784
- Relevancy: 0.3651
- Retrieval Hit Rate: 0.9596
- Retrieval MRR: 0.9040
- Agreement Rate (2 judges): 0.9823
- Hiệu năng: 0.0265 giây/case, 154.06 tokens/case, chi phí ước tính 0.004576 USD

## 2. Kết quả Regression
- V1 Score: 2.2323
- V2 Score: 4.8182
- Delta: +2.59
- Quyết định Release Gate: APPROVE

Nhận định: hệ thống đã cải thiện rõ rệt và đạt trạng thái sẵn sàng nộp/chấm.

## 3. Failure clustering (5 case còn fail)
| Nhóm lỗi | Số lượng | Tỉ lệ trên toàn bộ tập | Mô tả ngắn |
|---|---:|---:|---|
| Standard | 3 | 3.03% | Trả lời dựa vào đoạn liên quan nhưng không phải đoạn kỳ vọng top-1 |
| Adversarial | 2 | 2.02% | Có từ chối đúng format nhưng vẫn trích sai căn cứ tài liệu |
| Edge | 0 | 0.00% | Không còn lỗi đáng kể |

Các fail đều có mẫu giống nhau:
- Hit Rate = 1.0 (đúng tài liệu có nằm trong top-k)
- MRR = 0.5 (tài liệu đúng đứng hạng 2 thay vì hạng 1)
- Điểm judge giảm do căn cứ trả lời không khớp expected evidence.

## 4. 5 Whys cho lỗi còn lại (root cause hiện tại)
1. Symptom: còn 5 fail, tập trung ở cặp tài liệu gần nghĩa (ví dụ `doc_0007` vs `doc_0021`, `doc_0023` vs `doc_0024`, `doc_0011` vs `doc_0036`).
2. Why 1: Bộ truy hồi đưa đúng tài liệu vào top-k nhưng xếp sai top-1.
3. Why 2: Scoring retrieval hiện chưa đủ phân biệt câu hỏi có pattern "đoạn bắt đầu bằng..." với đoạn văn bản tương tự chủ đề.
4. Why 3: Sau retrieval, generator ưu tiên tài liệu đứng đầu thay vì re-rank theo ràng buộc câu hỏi (anchor phrase/điều luật cụ thể).
5. Why 4: Thiếu bước kiểm tra hậu truy hồi (post-retrieval validation) để đảm bảo đoạn trả lời khớp anchor trong câu hỏi.
6. Root cause: lỗi chính nằm ở độ chính xác xếp hạng top-1 (ranking precision), không còn là lỗi từ chối intent hay lỗi mất context như bản cũ.

## 5. Danh sách case fail còn lại
- idx 28: standard, expected `doc_0021`, retrieved `doc_0007, doc_0021`, score 1.5
- idx 30: adversarial, expected `doc_0021`, retrieved `doc_0007, doc_0021`, score 1.5
- idx 34: standard, expected `doc_0024`, retrieved `doc_0023, doc_0024`, score 2.5
- idx 61: standard, expected `doc_0036`, retrieved `doc_0011, doc_0036`, score 1.5
- idx 63: adversarial, expected `doc_0036`, retrieved `doc_0011, doc_0036`, score 2.0

## 6. Kế hoạch cải tiến vòng tiếp theo
1. Thêm bước re-rank theo anchor phrase: ưu tiên chunk có prefix/trích dẫn khớp cụm "đoạn bắt đầu bằng...".
2. Bổ sung post-check trước khi trả lời: nếu top-1 không chứa anchor nhưng top-2 có, tự động đổi nguồn sinh câu trả lời.
3. Tinh chỉnh metric nội bộ: theo dõi thêm Top-1 Accuracy bên cạnh Hit Rate để phát hiện sớm lỗi MRR=0.5.
4. Duy trì regression gate hiện tại vì đã hiệu quả (điểm tăng mạnh, agreement cao, latency thấp).
